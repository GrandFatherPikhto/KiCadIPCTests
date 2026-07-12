#!/usr/bin/env python3
"""
Тест получения информации о плате.
"""
from ipc_tests.core import get_kicad_board
from ipc_tests.board_utils import get_board_info

def run_test(logger):
    logger.info("=== ТЕСТ: ИНФОРМАЦИЯ О ПЛАТЕ ===")
    board = get_kicad_board(logger=logger)
    if board is None:
        return False
    info = get_board_info(board, logger=logger)
    logger.info(f"Информация о плате: {info}")
    return True
