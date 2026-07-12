#!/usr/bin/env python3
"""
Утилиты для определения пути проекта и схемы.
"""
import os


def get_project_path(board, logger=None):
    """Возвращает путь к каталогу проекта или None."""
    try:
        project = board.get_project()
        return project.path or None
    except Exception as e:
        if logger:
            logger.error(f"get_project_path упал: {type(e).__name__}: {e}")
        return None


def get_project_name(board, logger=None):
    """Возвращает имя проекта или None."""
    try:
        project = board.get_project()
        return project.name or None
    except Exception as e:
        if logger:
            logger.error(f"get_project_name упал: {type(e).__name__}: {e}")
        return None


def get_schematic_path(board, logger=None):
    """
    Собирает путь к главной схеме (project.kicad_sch).
    Возвращает полный путь или None.
    """
    project_dir = get_project_path(board, logger=logger)
    if not project_dir:
        return None
    proj_name = get_project_name(board, logger=logger) or os.path.basename(project_dir)
    return os.path.join(project_dir, f"{proj_name}.kicad_sch")
