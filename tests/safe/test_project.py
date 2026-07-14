"""
test_project.py — путь проекта и схемы.
Использует core_api.project (новый модуль, добавлен при переносе этого
теста — core_api раньше не имел этой функциональности вовсе).
"""
import os

from runner.registry import register


@register("safe_project", suite="safe", needs_kicad=True)
def run_test(logger, kicad, board, **params) -> bool:
    from core_api import project

    proj_dir = project.get_project_path(board)
    proj_name = project.get_project_name(board)
    sch_path = project.get_schematic_path(board)

    logger.info(f"Папка проекта: {proj_dir}")
    logger.info(f"Имя проекта: {proj_name}")
    logger.info(f"Путь к схеме: {sch_path}")

    if sch_path and os.path.exists(sch_path):
        logger.info("Файл схемы существует")
    else:
        logger.warning("Файл схемы не найден по вычисленному пути")

    return proj_dir is not None and proj_name is not None
