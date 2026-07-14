"""
test_refill_zones_busy_repro.py — прямая проверка ГЛАВНОЙ неподтверждённой
гипотезы из истории проекта: вызов board.refill_zones(block=False,
max_poll_seconds=1) оставляет незавершённый асинхронный джоб, который
"заклинивает" плату (постоянный busy для get_footprints и т.п.) на весь
остаток сессии KiCad.

Шаги: baseline (get_footprints/get_tracks работают) -> вызов
refill_zones(block=False, ...) ТОЧНО как в оригинальном инциденте ->
проверка сразу после -> несколько попыток с паузами (до 30с).

САМЫЙ ОПАСНЫЙ ТЕСТ В НАБОРЕ: если гипотеза подтвердится, тест оставит
плату в том же "битом" состоянии, что и оригинальный инцидент —
единственный подтверждённый выход из него — полный перезапуск KiCad (не
скрипта). Запускайте осознанно, не на середине важной сессии редактирования.
"""
import time

from runner.registry import register
from runner.step_helper import call_step


def _probe_content_calls(board, logger, label):
    results = {}
    for name, fn in [
        ("get_footprints", lambda: list(board.get_footprints())),
        ("get_tracks", lambda: list(board.get_tracks())),
        ("get_nets (метаданные, контроль)", lambda: list(board.get_nets())),
    ]:
        _, ok = call_step(logger, f"{label}: {name}", fn)
        results[name] = ok
    return results


@register("mutating_refill_zones_busy_repro", suite="mutating", dangerous=True, needs_kicad=True)
def run_test(logger, kicad, board, **params) -> bool:
    logger.info("--- Шаг 1: baseline ДО refill_zones ---")
    before = _probe_content_calls(board, logger, "ДО")
    if not all(before.values()):
        logger.warning("Плата уже в busy ДО начала теста — результат неинформативен. "
                       "Перезапустите KiCad и повторите с чистого состояния.")
        return False
    logger.info("Baseline чист: все content-вызовы отработали")

    zones, ok = call_step(logger, "get_zones", lambda: list(board.get_zones()))
    if not ok or not zones:
        logger.warning("На плате нет зон — refill_zones нечего заливать, тест неприменим "
                       "на этой плате (нужна плата хотя бы с одной зоной)")
        return False
    logger.info(f"Найдено зон: {len(zones)}. Запускаю refill_zones(block=False, max_poll_seconds=1)...")

    t0 = time.perf_counter()
    _, ok = call_step(
        logger, "refill_zones(block=False, max_poll_seconds=1) — КАК В ОРИГИНАЛЬНОМ ИНЦИДЕНТЕ",
        board.refill_zones, block=False, max_poll_seconds=1
    )
    logger.info(f"Вызов refill_zones вернулся за {round((time.perf_counter()-t0)*1000, 1)} мс (ok={ok})")

    logger.info("--- Шаг 2: проверка СРАЗУ после refill_zones ---")
    immediately_after = _probe_content_calls(board, logger, "СРАЗУ ПОСЛЕ")

    if all(immediately_after.values()):
        logger.info("Сразу после refill_zones(block=False) всё работает — немедленного эффекта нет. "
                    "Проверяю отложенный эффект ниже.")
    else:
        logger.warning("Content-вызовы сломались СРАЗУ после refill_zones(block=False) — "
                       "сильное подтверждение гипотезы. Проверяю, отпускает ли само.")

    logger.info("--- Шаг 3: повторные попытки с паузами (до 30с) ---")
    attempts = 6
    delay_s = 5.0
    recovered = False
    for i in range(1, attempts + 1):
        time.sleep(delay_s)
        probe = _probe_content_calls(board, logger, f"попытка {i}/{attempts} (+{i*delay_s:.0f}с)")
        if all(probe.values()):
            logger.info(f"Восстановилось само через ~{i*delay_s:.0f}с")
            recovered = True
            break

    if not recovered:
        logger.error("busy НЕ отпустил сам за 30 секунд после refill_zones(block=False). "
                     "Гипотеза ПОДТВЕРЖДЕНА: единственный известный выход — полный "
                     "перезапуск самого приложения KiCad (не скрипта).")
    else:
        logger.info("busy было временным и прошло само. Гипотеза про постоянный busy "
                    "НЕ подтверждена в этом прогоне — возможно, причина инцидента была другой.")

    return recovered
