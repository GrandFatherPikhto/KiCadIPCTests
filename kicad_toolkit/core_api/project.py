"""
project.py — определение пути проекта и схемы.
"""
import os
from typing import Optional


def get_project_path(board) -> Optional[str]:
    """Путь к каталогу проекта, или None."""
    project = board.get_project()
    return project.path or None


def get_project_name(board) -> Optional[str]:
    """Имя проекта, или None."""
    project = board.get_project()
    return project.name or None


def get_schematic_path(board) -> Optional[str]:
    """
    Путь к главной схеме (<имя_проекта>.kicad_sch). Собирается из пути и
    имени проекта — сам kipy прямого метода "путь к схеме" не даёт.
    """
    project_dir = get_project_path(board)
    if not project_dir:
        return None
    proj_name = get_project_name(board) or os.path.basename(project_dir)
    return os.path.join(project_dir, f"{proj_name}.kicad_sch")
