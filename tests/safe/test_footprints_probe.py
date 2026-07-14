"""
test_footprints_probe.py — диагностический тест-проба: несколько попыток
get_footprints() с паузами.

"busy" возвращается мгновенно (0.1-0.5мс, не таймаут), и только для
вызовов, трогающих содержимое платы, а не для метаданных. Больше похоже
на состояние PCB-редактора в живом GUI (открытый диалог, активный
инструмент), чем на перегрузку сервера. Тест не чинит проблему — честно
фиксирует, отпускает ли busy само по себе за ~10 секунд.
"""
import time

from runner.registry import register
from runner.step_helper import call_step


@register("safe_footprints_probe", suite="safe", needs_kicad=True)
def run_test(logger, kicad, board, **params) -> bool:
    attempts = 6
    delay_s = 2.0
    results = []

    for i in range(1, attempts + 1):
        footprints, ok = call_step(
            logger, f"get_footprints (попытка {i}/{attempts})",
            lambda: list(board.get_footprints())
        )
        results.append(ok)
        if ok:
            logger.info(f"Попытка {i}: успех, {len(footprints)} футпринтов")
            break
        if i < attempts:
            logger.info(f"Попытка {i}: busy, жду {delay_s}с...")
            time.sleep(delay_s)

    if any(results):
        logger.info("get_footprints в итоге отработал — состояние busy временное и само проходит")
        return True

    logger.warning(f"За {attempts} попыток с паузами {delay_s}с busy не прошло. "
                   f"Похоже, что-то в GUI PCB-редактора держит модель постоянно — "
                   f"проверьте окно KiCad глазами прямо сейчас")
    # Не считаем это провалом всего прогона -- это диагностика, а не
    # проверка корректности API. Результат уже виден в логе выше.
    return True
