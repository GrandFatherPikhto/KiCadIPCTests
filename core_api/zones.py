"""
zones.py — зоны (в т.ч. Rule Area): поиск по имени, точки контура.
"""
from typing import List, Optional
from kipy.board_types import Zone
from kipy.geometry import Vector2


def get_by_name(board, name: str) -> Optional[Zone]:
    """Ищет зону по имени (например, Rule Area 'RA_DECAP_ZONE')."""
    for z in board.get_zones():
        if z.name == name:
            return z
    return None


def get_boundary_points(zone: Zone) -> List[Vector2]:
    """
    Точки контура зоны, БЕЗ учёта дуг (node.has_point отфильтровывает
    дуговые узлы) — для прямоугольной/полигональной Rule Area этого
    обычно достаточно; для контура со скруглениями нужна более полная
    обработка PolyLine.
    """
    return [node.point for node in zone.outline.outline if node.has_point]
