"""
vias.py — создание/удаление переходных отверстий (Via).
"""
from typing import Tuple
from kipy.board_types import Via, ViaType, Net
from kipy.proto.common.types import base_types_pb2 as common_types_pb2
from .geometry import MM, vec_mm


def make(position_mm: Tuple[float, float], net: Net,
         drill_mm: float = 0.3, diameter_mm: float = 0.6) -> Via:
    """
    Строит объект Via (ещё НЕ на плате). Чтобы реально создать её —
    board.create_items([via]) внутри транзакции (см. board.py).
    """
    via = Via()
    via.type = ViaType.VT_THROUGH
    via.position = vec_mm(*position_mm)
    via.net = net
    via.drill_diameter = int(drill_mm * MM)
    via.diameter = int(diameter_mm * MM)
    return via


def remove_by_id(board, uuid_str: str):
    """
    Удаляет объект (виа или любой другой BoardItem) по его id — строка uuid.
    ВАЖНО: remove_items_by_id() в реальном API ждёт объект KIID, а НЕ
    голую строку с uuid — если передать строку напрямую, вызов либо упадёт,
    либо (что хуже) молча не удалит ничего без единой ошибки.
    """
    kiid = common_types_pb2.KIID()
    kiid.value = uuid_str
    board.remove_items_by_id([kiid])
