#!/usr/bin/env python3
"""
Диагностический тест-проба: несколько попыток get_footprints() с паузами.

Контекст: в прогоне от 2026-07-12 14:06-14:07 выяснилось, что "busy"
возвращается МГНОВЕННО (0.1-0.5 мс, не таймаут), и только для вызовов,
трогающих содержимое платы (get_footprints/get_tracks/.../begin_commit),
а не для метаданных (get_nets/get_project/get_selection/...). Это больше
похоже на состояние PCB-редактора в живом GUI (открытый диалог, активный
инструмент, отсутствие фокуса), чем на перегрузку сервера.

Этот тест не чинит проблему — он просто честно фиксирует, отпускает ли
"busy" само по себе за ~10 секунд без вмешательства в GUI, или нет. Если
НЕ отпускает — почти наверняка что-то держит PCB-редактор (диалог/
инструмент), и это надо смотреть глазами прямо в момент прогона.
"""
import time

from ipc_tests.core import get_kicad_board, call_ipc


def run_test(logger):
    logger.info("=== ТЕСТ: ПРОБА get_footprints С ПОВТОРАМИ ===")
    board = get_kicad_board(logger=logger)
    if board is None:
        return False

    attempts = 6
    delay_s = 2.0
    results = []

    for i in range(1, attempts + 1):
        footprints, ok = call_ipc(
            logger, f"get_footprints (попытка {i}/{attempts})",
            lambda: list(board.get_footprints())
        )
        results.append(ok)
        if ok:
            logger.info(f"   Попытка {i}: УСПЕХ, {len(footprints)} футпринтов")
            break
        if i < attempts:
            logger.info(f"   Попытка {i}: busy, жду {delay_s} с...")
            time.sleep(delay_s)

    if any(results):
        logger.info("[PASS] get_footprints в итоге отработал — состояние "
                     "'busy' временное и само проходит.")
        return True
    else:
        logger.warning(
            f"За {attempts} попыток с паузами {delay_s} с 'busy' не прошло. "
            f"Похоже, что-то в GUI PCB-редактора держит модель постоянно "
            f"(открытый диалог, активный инструмент, редактор не в фокусе) — "
            f"проверьте окно KiCad глазами прямо сейчас."
        )
        # Не считаем это провалом всего прогона — это диагностика, а не
        # проверка корректности API. Возвращаем True, если сам вызов прошёл
        # без падения теста; результат уже виден в логе выше.
        return True
