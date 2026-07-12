#!/usr/bin/env python3
"""
Тест переиспользования IPC-соединения.

Это регрессионный тест на главный фикс от 2026-07-12: раньше каждый
get_kicad_board() создавал новое подключение, и к моменту "тяжёлых" тестов
(test_full_api) накапливалось несколько незакрытых сокетов, что совпадало
по времени с ошибками "KiCad is busy" на get_footprints/get_tracks/...

Тест НЕ доказывает causal-связь железно (это можно подтвердить только
прогоном на реальном KiCad до/после фикса), но фиксирует контракт:
повторные вызовы get_kicad_board() в рамках одного процесса должны
возвращать один и тот же объект Board, а не плодить новые подключения.
"""
import time

from ipc_tests.core import get_kicad_board


def run_test(logger):
    logger.info("=== ТЕСТ: ПЕРЕИСПОЛЬЗОВАНИЕ IPC-СОЕДИНЕНИЯ ===")

    board_1 = get_kicad_board(logger=logger)
    if board_1 is None:
        logger.error("Не удалось получить Board на первом вызове.")
        return False

    t0 = time.perf_counter()
    board_2 = get_kicad_board(logger=logger)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    if board_2 is None:
        logger.error("Не удалось получить Board на повторном вызове.")
        return False

    same_object = board_1 is board_2
    logger.info(f"Повторный get_kicad_board() занял {elapsed_ms} мс "
                f"(тот же объект: {same_object})")

    if not same_object:
        logger.error(
            "Повторный вызов создал НОВЫЙ объект Board вместо переиспользования "
            "кэша — проверьте логику can_reuse в core.get_kicad_board()."
        )
        return False

    # Дополнительно: несколько быстрых вызовов подряд не должны почти ничего
    # стоить по времени, если кэш реально работает (это просто board.get_project()
    # под капотом can_reuse-ветки).
    timings = []
    for _ in range(5):
        t0 = time.perf_counter()
        get_kicad_board(logger=logger)
        timings.append(round((time.perf_counter() - t0) * 1000, 1))
    logger.info(f"5 повторных вызовов подряд, мс: {timings}")

    return True
