#!/usr/bin/env python3
"""
Тест определения пути проекта и схемы.
"""
import os
from ipc_tests.core import get_kicad_board
from ipc_tests.project_utils import get_project_path, get_project_name, get_schematic_path

def run_test(logger):
    logger.info("=== ТЕСТ: ПУТЬ ПРОЕКТА ===")
    board = get_kicad_board(logger=logger)
    if board is None:
        return False
    proj_dir = get_project_path(board)
    proj_name = get_project_name(board)
    sch_path = get_schematic_path(board)
    logger.info(f"Папка проекта: {proj_dir}")
    logger.info(f"Имя проекта: {proj_name}")
    logger.info(f"Путь к схеме: {sch_path}")
    if sch_path and os.path.exists(sch_path):
        logger.info("Файл схемы существует.")
    else:
        logger.warning("Файл схемы не найден.")
    return True