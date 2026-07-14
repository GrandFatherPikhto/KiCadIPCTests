"""
nets.py — цепи (Net) платы.
"""
from typing import List, Optional
from kipy.board_types import Net


def get_all(board) -> List[Net]:
    """Все цепи платы."""
    return list(board.get_nets())


def get_by_name(board, name: str) -> Optional[Net]:
    """Ищет цепь по имени (например, '+3V3_VCCIO', 'GND')."""
    for n in get_all(board):
        if n.name == name:
            return n
    return None
