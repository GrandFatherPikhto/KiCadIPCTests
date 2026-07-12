#!/usr/bin/env python3
"""
Запуск всех тестов.
"""
import sys
import os

from ipc_tests.tests import (
    test_board, 
    test_components, 
    test_connection, 
    test_nets, 
    test_pads, 
    test_project, 
    test_full_api
    )

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ipc_tests.core import setup_logging
from ipc_tests.tests import test_cli_netlist

def run_all_tests():
    logger = setup_logging()
    logger.info("="*80)
    logger.info("ЗАПУСК ВСЕХ ТЕСТОВ IPC KiCad 10")
    logger.info("="*80)
    
    tests = [
        ("Подключение", test_connection.run_test),
        ("Информация о плате", test_board.run_test),
        ("Цепи и коды", test_nets.run_test),
        ("Площадки и цепи", test_pads.run_test),
        ("Инспекция компонентов", test_components.run_test),
        ("Путь проекта", test_project.run_test),
        ("Экспорт netlist через CLI", test_cli_netlist.run_test),
        ("Полный API-тест", test_full_api.run_test),
    ]
    
    results = {}
    for name, func in tests:
        logger.info(f"\n--- Запуск теста: {name} ---")
        try:
            ok = func(logger)
            results[name] = ok
            if ok:
                # logger.info(f"✅ Тест '{name}' пройден успешно.")
                logger.info(f"[PASS] Тест '{name}' пройден успешно.")
            else:
                # logger.error(f"❌ Тест '{name}' завершился с ошибкой.")
                logger.error(f"[FAIL] Тест '{name}' завершился с ошибкой.")
        except Exception as e:
            logger.exception(f"[FAIL] Тест '{name}' упал с исключением: {e}")
            results[name] = False
    
    logger.info("\n" + "="*80)
    logger.info("ИТОГИ ТЕСТИРОВАНИЯ:")
    for name, ok in results.items():
        status = "[SUCCESS] УСПЕШНО" if ok else "[FAIL] НЕУДАЧА"
        logger.info(f"  {name}: {status}")
    logger.info("="*80)

if __name__ == "__main__":
    run_all_tests()