#!/usr/bin/env python3
"""
Утилиты для определения пути проекта и схемы.
"""
import os

def get_project_path(board):
    """Возвращает путь к каталогу проекта или None."""
    try:
        project = board.get_project()
        if hasattr(project, 'path') and project.path:
            return str(project.path)
    except Exception:
        pass
    return None

def get_project_name(board):
    """Возвращает имя проекта или None."""
    try:
        project = board.get_project()
        if hasattr(project, 'name') and project.name:
            return str(project.name)
    except Exception:
        pass
    return None

def get_schematic_path(board):
    """
    Собирает путь к главной схеме (project.kicad_sch).
    Возвращает полный путь или None.
    """
    project_dir = get_project_path(board)
    if not project_dir:
        return None
    proj_name = get_project_name(board)
    if not proj_name:
        # пробуем взять имя каталога
        proj_name = os.path.basename(project_dir)
    return os.path.join(project_dir, f"{proj_name}.kicad_sch")