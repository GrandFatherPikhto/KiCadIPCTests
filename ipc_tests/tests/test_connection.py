#!/usr/bin/env python3
"""
Тест подключения к IPC.
"""
from ipc_tests.core import get_kicad_board

def run_test(logger):
    logger.info("=== ТЕСТ: ПОДКЛЮЧЕНИЕ К IPC ===")
    board = get_kicad_board(logger=logger)
    if board is None:
        logger.error("Не удалось получить объект Board.")
        return False
    logger.info("Объект Board получен успешно.")
    return True