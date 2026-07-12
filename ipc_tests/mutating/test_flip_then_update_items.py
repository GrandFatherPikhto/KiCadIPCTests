#!/usr/bin/env python3
"""
test_flip_then_update_items.py — регрессионный тест на баг, найденный и
исправленный СЕГОДНЯ (2026-07-12) в KiCadDecapPlacer/placement/executor.py:

    "флип — отдельный GUI-action, не update_items. Перечитываем футпринты
    заново, иначе следующий шаг (простановка position/orientation через
    update_items) молча откатит флип устаревшими данными."

Смысл бага: run_action("pcbnew.InteractiveEdit.flip") меняет плату НЕ через
update_items(), а как отдельное GUI-действие на стороне KiCad. Если после
этого использовать ЗАКЭШИРОВАННЫЙ локальный объект footprint (полученный
ДО флипа) и вызвать board.update_items([тот_же_объект]) для чего-то
другого (например, простановки position) — этот update_items() отправит
на сервер СТАРОЕ состояние layer (то, что было до флипа), и сервер, судя
по всему, тихо откатывает layer обратно. Baг был найден именно из-за
такого сценария, не из простого чтения документации.

Этот тест воспроизводит ОБА варианта на одном компоненте, по очереди:
    A. "Неправильный" путь: флип -> update_items() с footprint-объектом,
       закэшированным ДО флипа (без повторного get_footprints()).
    B. "Правильный" путь (текущий фикс DecapPlacer): флип -> повторный
       get_footprints() -> update_items() со СВЕЖИМ объектом.
И сравнивает: остался ли layer=B.Cu после варианта A (баг, если откатился
на F.Cu) и после варианта B (должен остаться B.Cu).

ВАЖНО: мутирует реальный компонент (флип на другую сторону + небольшой
сдвиг позиции, чтобы был повод вызвать update_items). Используйте
некритичный тестовый refdes, не боевую плату. Восстанавливает исходную
сторону и позицию в конце теста автоматически (если не упадёт раньше).

Запуск:
    python -m ipc_tests.mutating.test_flip_then_update_items C401
"""
import argparse
import sys
import time

from kipy.board_types import BoardLayer
from kipy.geometry import Vector2

from ipc_tests.core import get_kicad_board, call_ipc, setup_logging
from ipc_tests.board_utils import get_footprints
from ipc_tests.component_utils import get_reference


MM = 1_000_000


def _find(footprints, ref):
    return next((fp for fp in footprints if get_reference(fp) == ref), None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", help="refdes тестового компонента, например C401")
    args = ap.parse_args()

    logger = setup_logging(log_file="logs/flip_staleness_regression.log")
    logger.info("=" * 78)
    logger.info(f"РЕГРЕССИЯ: флип + update_items() со 'стухшим' vs свежим объектом ({args.ref})")
    logger.info("=" * 78)

    # run_action живёт на объекте KiCad (kicad.run_action), а не Board — нам
    # нужен сам клиент. core.get_kicad_board кэширует именно board, поэтому
    # здесь подключаемся напрямую, отдельно от общего кэша, чтобы иметь
    # доступ к kicad.run_action(). force_reconnect=False просто переиспользует
    # существующее соединение модуля core, если оно уже поднято.
    import ipc_tests.core as core_mod
    board = get_kicad_board(logger=logger)
    if board is None:
        logger.error("Нет соединения с KiCad.")
        return False
    kicad = core_mod._cached_kicad
    if kicad is None:
        logger.error("Внутренняя ошибка: _cached_kicad пуст после успешного get_kicad_board().")
        return False

    footprints = get_footprints(board, logger=logger)
    target = _find(footprints, args.ref)
    if target is None:
        logger.error(f"{args.ref} не найден на плате.")
        return False

    original_layer = target.layer
    original_position = target.position
    logger.info(f"Исходное состояние {args.ref}: layer={original_layer}, "
                f"pos=({original_position.x/MM:.3f}, {original_position.y/MM:.3f}) мм")

    # --- Вариант A: "неправильный" путь (стухший объект) ---
    logger.info("\n--- Вариант A: флип, затем update_items() СО СТАРЫМ объектом ---")
    call_ipc(logger, "clear_selection", board.clear_selection)
    call_ipc(logger, "add_to_selection([target])", board.add_to_selection, [target])
    _, ok = call_ipc(logger, "run_action('pcbnew.InteractiveEdit.flip')",
                      kicad.run_action, "pcbnew.InteractiveEdit.flip")
    call_ipc(logger, "clear_selection", board.clear_selection)
    if not ok:
        logger.error("Флип не выполнился — прерываю тест.")
        return False
    time.sleep(0.5)

    # Намеренно НЕ перечитываем footprints — используем 'target', полученный
    # ДО флипа, ровно как это делал старый (уже пофикшенный) код DecapPlacer.
    commit, ok = call_ipc(logger, "begin_commit (вариант A)", board.begin_commit)
    if ok and commit is not None:
        target.position = Vector2.from_xy(original_position.x + int(0.5 * MM), original_position.y)
        _, ok2 = call_ipc(logger, "update_items([стухший target]) (вариант A)",
                           board.update_items, [target])
        if ok2:
            call_ipc(logger, "push_commit (вариант A)", board.push_commit, commit,
                      "test_flip_then_update_items: вариант A")
        else:
            call_ipc(logger, "drop_commit (вариант A)", board.drop_commit, commit)

    footprints_after_a = get_footprints(board, logger=logger)
    after_a = _find(footprints_after_a, args.ref)
    layer_after_a = after_a.layer if after_a else None
    logger.info(f"После варианта A: layer={layer_after_a} "
                f"(ожидание бага: откатился на {original_layer}, а не остался перевёрнутым)")

    bug_reproduced = (layer_after_a == original_layer)

    # --- Вариант B: "правильный" путь (свежий объект, текущий фикс) ---
    logger.info("\n--- Вариант B: флип, затем ПЕРЕЧИТЫВАЕМ footprints, потом update_items() ---")
    if after_a is None:
        logger.error(f"{args.ref} не найден после варианта A — не могу продолжить вариант B.")
        return bug_reproduced

    call_ipc(logger, "clear_selection", board.clear_selection)
    call_ipc(logger, "add_to_selection([after_a])", board.add_to_selection, [after_a])
    _, ok = call_ipc(logger, "run_action('pcbnew.InteractiveEdit.flip') (2)",
                      kicad.run_action, "pcbnew.InteractiveEdit.flip")
    call_ipc(logger, "clear_selection", board.clear_selection)
    time.sleep(0.5)

    # ПРАВИЛЬНО: перечитываем footprints заново перед update_items.
    footprints_fresh = get_footprints(board, logger=logger)
    fresh_target = _find(footprints_fresh, args.ref)
    if fresh_target is None:
        logger.error(f"{args.ref} не найден после второго флипа.")
        return bug_reproduced

    commit, ok = call_ipc(logger, "begin_commit (вариант B)", board.begin_commit)
    if ok and commit is not None:
        fresh_target.position = original_position  # заодно возвращаем позицию
        _, ok2 = call_ipc(logger, "update_items([свежий fresh_target]) (вариант B)",
                           board.update_items, [fresh_target])
        if ok2:
            call_ipc(logger, "push_commit (вариант B)", board.push_commit, commit,
                      "test_flip_then_update_items: вариант B (restore)")
        else:
            call_ipc(logger, "drop_commit (вариант B)", board.drop_commit, commit)

    footprints_after_b = get_footprints(board, logger=logger)
    after_b = _find(footprints_after_b, args.ref)
    layer_after_b = after_b.layer if after_b else None
    logger.info(f"После варианта B: layer={layer_after_b} "
                f"(ожидание фикса: {original_layer} — второй флип вернул на исходную сторону)")

    fix_confirmed = (layer_after_b == original_layer)

    logger.info("\n" + "=" * 78)
    if bug_reproduced:
        logger.warning(
            "[ПОДТВЕРЖДЕНО] Вариант A воспроизвёл баг: update_items() со стухшим "
            "объектом ПОСЛЕ флипа откатил layer обратно. Фикс в DecapPlacer от "
            "2026-07-12 (перечитывать footprints после флипа) обоснован и необходим."
        )
    else:
        logger.info(
            "[НЕ ВОСПРОИЗВЕДЕНО] Вариант A не откатил layer в этом прогоне — либо баг "
            "специфичен для другой версии KiCad/kipy, либо для другого сценария "
            "(например, батч из нескольких футпринтов, а не одного)."
        )
    logger.info(f"Итог по слою: исходный={original_layer}, после A={layer_after_a}, "
                f"после B={layer_after_b} (должен = исходному, т.к. второй флип — возврат).")
    logger.info("=" * 78)

    return fix_confirmed


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
