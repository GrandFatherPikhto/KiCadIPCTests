#!/usr/bin/env python3
"""
Запуск всех тестов.
"""
import sys
import os
import time

from ipc_tests.tests import (
    test_board,
    test_components,
    test_connection,
    test_connection_reuse,
    test_footprints_probe,
    test_nets,
    test_pads,
    test_project,
    test_full_api,
    test_cli_netlist,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ipc_tests.core import setup_logging


def run_all_tests():
    logger = setup_logging()
    logger.info("=" * 80)
    logger.info("ЗАПУСК ВСЕХ ТЕСТОВ IPC KiCad 10")
    logger.info("=" * 80)

    tests = [
        ("Подключение", test_connection.run_test),
        ("Переиспользование соединения", test_connection_reuse.run_test),
        ("Информация о плате", test_board.run_test),
        ("Цепи и коды", test_nets.run_test),
        ("Площадки и цепи", test_pads.run_test),
        ("Инспекция компонентов", test_components.run_test),
        ("Путь проекта", test_project.run_test),
        ("Экспорт netlist через CLI", test_cli_netlist.run_test),
        ("Полный API-тест", test_full_api.run_test),
        ("Проба get_footprints с повторами", test_footprints_probe.run_test),
    ]

    results = {}
    timings = {}
    run_started = time.perf_counter()

    for name, func in tests:
        logger.info(f"\n--- Запуск теста: {name} ---")
        t0 = time.perf_counter()
        try:
            ok = func(logger)
            results[name] = ok
        except Exception as e:
            logger.exception(f"[FAIL] Тест '{name}' упал с исключением: {e}")
            results[name] = False
        finally:
            timings[name] = round((time.perf_counter() - t0) * 1000, 1)

        if results[name]:
            logger.info(f"[PASS] Тест '{name}' пройден успешно ({timings[name]} мс).")
        else:
            logger.error(f"[FAIL] Тест '{name}' завершился с ошибкой ({timings[name]} мс).")

    total_ms = round((time.perf_counter() - run_started) * 1000, 1)

    logger.info("\n" + "=" * 80)
    logger.info("ИТОГИ ТЕСТИРОВАНИЯ:")
    for name, ok in results.items():
        status = "[SUCCESS] УСПЕШНО" if ok else "[FAIL] НЕУДАЧА"
        logger.info(f"  {name}: {status} — {timings[name]} мс")
    passed = sum(1 for ok in results.values() if ok)
    logger.info(f"Пройдено: {passed}/{len(results)}. Общее время прогона: {total_ms} мс.")
    logger.info("=" * 80)

    return results


if __name__ == "__main__":
    run_all_tests()
