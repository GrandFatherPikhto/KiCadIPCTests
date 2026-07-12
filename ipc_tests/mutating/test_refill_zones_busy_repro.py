#!/usr/bin/env python3
"""
test_refill_zones_busy_repro.py — прямая проверка ГЛАВНОЙ неподтверждённой
гипотезы из CHANGES.md/README этого репозитория.

Контекст: между 13:47:21 и 13:49:10 (см. logs/test.log) плата перешла в
постоянное 'busy' для всех операций с содержимым (get_footprints и т.п.),
хотя метаданные (get_nets/get_project) продолжали отвечать. Рабочая
гипотеза — вызов board.refill_zones(block=False, max_poll_seconds=1) где-то
в непатченом первом прогоне оставил асинхронный джоб незавершённым, и это
"заклинило" плату на весь остаток сессии KiCad. Гипотеза НЕ была проверена
прямым воспроизведением — только по совпадению во времени и логике.

Этот тест воспроизводит это НАМЕРЕННО, по шагам, с проверкой busy ДО и
ПОСЛЕ:
    1. Подтверждаем, что get_footprints() сейчас работает (baseline).
    2. Вызываем refill_zones(block=False, max_poll_seconds=1) — ТОЧНО как
       предположительно произошло в оригинальном инциденте.
    3. Сразу пробуем get_footprints()/get_tracks() — если сломалось сразу,
       это сильное подтверждение.
    4. Ждём и пробуем снова несколько раз — если само не отпускает за
       ~30 секунд, гипотеза подтверждена практически полностью.

ВАЖНО: если гипотеза подтвердится, тест оставит плату в том же "битом"
состоянии, что и оригинальный инцидент — единственный подтверждённый выход
из него в прошлый раз был полный перезапуск KiCad (не скрипта). Запускайте
это осознанно, не на середине важной сессии редактирования.

Запуск:
    python -m ipc_tests.mutating.test_refill_zones_busy_repro
"""
import time

from ipc_tests.core import get_kicad_board, call_ipc, setup_logging


def _probe_content_calls(board, logger, label):
    """Пробует несколько лёгких по смыслу вызовов, трогающих содержимое платы."""
    results = {}
    for name, fn in [
        ("get_footprints", lambda: list(board.get_footprints())),
        ("get_tracks", lambda: list(board.get_tracks())),
        ("get_nets (метаданные, контроль)", lambda: list(board.get_nets())),
    ]:
        result, ok = call_ipc(logger, f"{label}: {name}", fn)
        results[name] = ok
    return results


def main():
    logger = setup_logging(log_file="logs/refill_zones_repro.log")
    logger.info("=" * 78)
    logger.info("РЕПРОДУКЦИЯ ГИПОТЕЗЫ: refill_zones(block=False) => постоянный busy")
    logger.info("=" * 78)

    board = get_kicad_board(logger=logger, force_reconnect=True)
    if board is None:
        logger.error("Нет соединения с KiCad — тест невозможен.")
        return False

    logger.info("\n--- Шаг 1: baseline ДО refill_zones ---")
    before = _probe_content_calls(board, logger, "ДО")
    if not all(before.values()):
        logger.warning(
            "Плата уже в busy ДО начала теста — результат будет неинформативен. "
            "Перезапустите KiCad и повторите с чистого состояния."
        )
        return False
    logger.info("Baseline чист: все content-вызовы отработали.")

    zones, ok = call_ipc(logger, "get_zones", lambda: list(board.get_zones()))
    if not ok or not zones:
        logger.warning(
            "На плате нет зон (get_zones пуст/упал) — refill_zones нечего заливать, "
            "тест неприменим на этой плате. Нужна плата хотя бы с одной зоной."
        )
        return False
    logger.info(f"Найдено зон: {len(zones)}. Запускаю refill_zones(block=False, max_poll_seconds=1)...")

    t0 = time.perf_counter()
    _, ok = call_ipc(
        logger, "refill_zones(block=False, max_poll_seconds=1) — КАК В ОРИГИНАЛЬНОМ ИНЦИДЕНТЕ",
        board.refill_zones, block=False, max_poll_seconds=1
    )
    logger.info(f"Вызов refill_zones вернулся за {round((time.perf_counter()-t0)*1000,1)} мс (ok={ok})")

    logger.info("\n--- Шаг 2: проверка СРАЗУ после refill_zones ---")
    immediately_after = _probe_content_calls(board, logger, "СРАЗУ ПОСЛЕ")

    if all(immediately_after.values()):
        logger.info(
            "[РЕЗУЛЬТАТ] Сразу после refill_zones(block=False) всё работает — "
            "немедленного эффекта нет. Гипотеза НЕ подтверждена этим шагом, "
            "проверяем отложенный эффект ниже."
        )
    else:
        logger.warning(
            "[РЕЗУЛЬТАТ] Content-вызовы сломались СРАЗУ после refill_zones(block=False) — "
            "сильное подтверждение гипотезы. Проверяю, отпускает ли само по себе."
        )

    logger.info("\n--- Шаг 3: повторные попытки с паузами (до 30 с) ---")
    attempts = 6
    delay_s = 5.0
    recovered = False
    for i in range(1, attempts + 1):
        time.sleep(delay_s)
        probe = _probe_content_calls(board, logger, f"попытка {i}/{attempts} (+{i*delay_s:.0f} с)")
        if all(probe.values()):
            logger.info(f"[РЕЗУЛЬТАТ] Восстановилось само через ~{i*delay_s:.0f} с.")
            recovered = True
            break

    if not recovered:
        logger.error(
            "[ИТОГ] busy НЕ отпустил сам за 30 секунд после refill_zones(block=False). "
            "Гипотеза ПОДТВЕРЖДЕНА практически: единственный известный выход — "
            "полный перезапуск самого приложения KiCad (не скрипта), затем повторный "
            "прогон run_static_tests.py/test_all.py первым делом."
        )
    else:
        logger.info(
            "[ИТОГ] busy было временным и прошло само. Гипотеза про 'refill_zones "
            "оставляет плату в постоянном busy' НЕ подтверждена в этом прогоне — "
            "возможно, реальная причина инцидента была другой (открытый диалог, "
            "активный инструмент — см. test_footprints_probe.py)."
        )

    return recovered


if __name__ == "__main__":
    main()
