#!/usr/bin/env python3
"""
run.py — единая точка входа для всех тестов/скриптов инструментария.

Подключение к живому KiCad этот раннер НЕ делает сам — это осознанно
оставлено следующему шагу (когда будем переносить реальные тесты
ipc_tests/core_api-smoke, там и понадобится решить, как именно тест
получает kicad/board). На этом этапе проверяется только сама механика:
конфиг -> отбор тестов -> запуск -> логирование, на тестах-заглушках,
которым живой KiCad не нужен вовсе.

Запуск:
    python -m runner.run --config config/test_config.yaml --board 10CL006 --test dummy_ok
    python -m runner.run --config config/test_config.yaml --board 10CL006 --suite toy
    python -m runner.run --config config/test_config.yaml --board 10CL006   # все включённые суиты
"""
import argparse
import importlib
import pkgutil
import sys
from pathlib import Path
from typing import Optional, List, Tuple

from runner import registry
from runner.config_schema import load_config, resolve_params, RootConfig, TestEntry
from runner.logging_setup import setup_logging


class SharedConnection:
    """
    ОДНО соединение с KiCad на весь прогон, лениво устанавливаемое при
    первой необходимости и переиспользуемое дальше. НЕ создавайте новое
    соединение внутри отдельных тестов — см. registry.register().
    """
    def __init__(self, timeout_ms: int, logger):
        self._timeout_ms = timeout_ms
        self._logger = logger
        self._kicad = None
        self._board = None

    def get(self):
        if self._kicad is None:
            from core_api import kicad_client
            self._logger.debug(f"Устанавливаю соединение с KiCad (таймаут {self._timeout_ms} мс)...")
            self._kicad = kicad_client.connect(timeout_ms=self._timeout_ms)
            self._board = kicad_client.get_board(self._kicad)
        return self._kicad, self._board

    def refresh_board(self):
        """Перечитывает плату на существующем соединении (не открывает новое)."""
        from core_api import kicad_client
        self._board = kicad_client.get_board(self._kicad)
        return self._board


def discover_tests(package_name: str = "tests"):
    """
    Импортирует все модули внутри пакета tests (рекурсивно) — чтобы
    сработали декораторы @register в каждом из них. Импорт модуля, а не
    вызов какой-то отдельной функции регистрации — так модуль теста может
    быть одновременно и обычным Python-скриптом (запускаемым напрямую), и
    участником общего реестра.
    """
    package = importlib.import_module(package_name)
    for _, name, is_pkg in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}."):
        if not is_pkg:
            importlib.import_module(name)


def select_tests(cfg: RootConfig, suite_name: Optional[str], test_name: Optional[str]
                  ) -> List[Tuple[str, TestEntry]]:
    """
    Возвращает список (suite_name, TestEntry) для запуска, с учётом
    enabled/dangerous из конфига. Опасные тесты запускаются ТОЛЬКО если
    явно enabled: true в конфиге — отдельного CLI-флага поверх не нужно
    (так и договаривались).
    """
    selected: List[Tuple[str, TestEntry]] = []

    if test_name:
        # Запуск одного конкретного теста по имени — ищем, в какой суите
        # конфига он описан. ВАЖНО: даже при явном запросе по имени
        # enabled: false из конфига ДОЛЖЕН соблюдаться — иначе --test это
        # дыра в защите опасных тестов в обход суитного отбора (было
        # реально проверено и подтверждено как баг на этапе тестирования
        # каркаса, до переноса реальных тестов).
        for s_name, suite in cfg.suites.items():
            if test_name in suite.tests:
                entry = suite.tests[test_name]
                if not entry.enabled:
                    raise PermissionError(
                        f"Тест {test_name!r} выключен в конфиге (enabled: false) — "
                        f"поставьте enabled: true в suites.{s_name}.tests.{test_name}, "
                        f"чтобы запустить его явно. Это намеренная защита для опасных тестов."
                    )
                selected.append((s_name, entry))
                break
        else:
            # Тест не описан в конфиге вообще -- считаем enabled=True,
            # dangerous=False по умолчанию, раз пользователь просит явно
            # и ему просто негде было бы поставить enabled: false.
            selected.append((suite_name or "", TestEntry(name=test_name)))
        return selected

    suite_names = [suite_name] if suite_name else list(cfg.suites.keys())
    for s_name in suite_names:
        suite = cfg.suites.get(s_name)
        if suite is None or not suite.enabled:
            continue
        for t_name, entry in suite.tests.items():
            if not entry.enabled:
                continue
            if entry.dangerous and not entry.enabled:
                continue  # избыточно, но явно: опасные тесты никогда не проскакивают неявно
            selected.append((s_name, entry))
    return selected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="путь к YAML-конфигу")
    ap.add_argument("--board", default=None, help="имя борта-профиля из конфига")
    ap.add_argument("--suite", default=None, help="запустить только одну суиту")
    ap.add_argument("--test", default=None, help="запустить только один тест по имени")
    args = ap.parse_args()

    cfg = load_config(args.config)
    logger = setup_logging(
        console_level=cfg.logging.console_level,
        file_path=cfg.logging.file,
        file_level=cfg.logging.file_level,
        rotate_max_bytes=cfg.logging.rotate_max_bytes,
        rotate_backups=cfg.logging.rotate_backups,
    )

    discover_tests()

    board_profile = cfg.boards.get(args.board) if args.board else None
    if args.board and board_profile is None:
        logger.warning(f"Борт-профиль {args.board!r} не найден в конфиге — параметры ref/pad/zone/net "
                        f"не будут подставлены автоматически")

    try:
        to_run = select_tests(cfg, args.suite, args.test)
    except PermissionError as e:
        logger.error(str(e))
        sys.exit(2)
    if not to_run:
        logger.warning("Нечего запускать — проверьте --suite/--test и содержимое конфига")
        sys.exit(1)

    shared_conn = SharedConnection(timeout_ms=cfg.kicad.timeout_ms, logger=logger)

    results = []
    for suite_name, entry in to_run:
        try:
            reg = registry.get(entry.name)
        except KeyError as e:
            logger.error(str(e))
            results.append((entry.name, False))
            continue

        params = resolve_params(board_profile, entry)
        if reg.needs_kicad:
            try:
                kicad, board = shared_conn.get()
            except Exception as e:
                logger.error(f"Не удалось подключиться к KiCad для теста {entry.name}: {e}")
                results.append((entry.name, False))
                continue
            params["kicad"] = kicad
            params["board"] = board

        tag = " [ОПАСНЫЙ]" if reg.dangerous else ""
        logger.info(f"--- Запуск: {entry.name}{tag} (суита {reg.suite}) ---")
        try:
            ok = reg.func(logger, **params)
        except Exception as e:
            logger.exception(f"Тест {entry.name} упал с исключением: {e}")
            ok = False
        results.append((entry.name, ok))
        logger.info(f"[{'PASS' if ok else 'FAIL'}] {entry.name}")

    passed = sum(1 for _, ok in results if ok)
    logger.info("=" * 60)
    logger.info(f"ИТОГО: {passed}/{len(results)} пройдено")
    for name, ok in results:
        logger.info(f"  {'[PASS]' if ok else '[FAIL]'} {name}")

    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
