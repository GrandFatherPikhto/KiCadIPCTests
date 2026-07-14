"""
selection.py — работа с текущим выделением в PCB-редакторе.
"""
from typing import List, Set, Dict, Any
from kipy.board_types import Group, FootprintInstance
from . import footprints as fp_api
from . import pads as pad_api


def get_selected_uuids(board) -> Set[str]:
    """
    UUID выделенных элементов, с учётом Group.

    ВАЖНО: у Group свойство .items, полученное с сервера, ВСЕГДА ПУСТОЕ —
    это просто локальный кэш-атрибут обёртки kipy, не то, что реально
    пришло с платы. Настоящие участники группы лежат в .proto.items
    (список KIID) — если выделить группу футпринтов в KiCad, брать нужно
    оттуда, а не из .items.
    """
    uuids: Set[str] = set()
    for item in board.get_selection():
        if isinstance(item, Group):
            for kiid in item.proto.items:
                uuids.add(str(kiid.value))
        elif hasattr(item, "id") and hasattr(item.id, "value"):
            uuids.add(str(item.id.value))
    return uuids


def get_selected_footprints(board) -> List[FootprintInstance]:
    """
    Только футпринты (компоненты) из текущего выделения. Group
    разворачивается в участников; прочие типы выделенных элементов (пады,
    треки, отдельные виа и т.п.) отфильтровываются — эта функция только
    про компоненты целиком.
    """
    uuids = get_selected_uuids(board)
    return [fp for fp in fp_api.get_all(board) if str(fp.id.value) in uuids]


def describe_selected(board) -> List[Dict[str, Any]]:
    """
    Сводка по каждому выделенному компоненту: refdes, номинал, футпринт,
    позиция, угол, размер, подключённые цепи и пады (с их собственными
    координатами/размером/цепью). Собрано поверх footprints.py/pads.py —
    ничего нового не изобретает, просто удобная точка входа "дай мне всё
    сразу про то, что выделено".
    """
    selected = get_selected_footprints(board)
    if not selected:
        return []

    bboxes = fp_api.get_bounding_boxes_mm(board, selected)

    result = []
    for fp, size_mm in zip(selected, bboxes):
        pads_data = []
        for pad in pad_api.get_all(fp):
            x_mm, y_mm = pad_api.get_position_mm(pad)
            size = pad_api.get_size_mm(pad)
            pads_data.append({
                "number": pad.number,
                "net": pad_api.get_net_name(pad),
                "x_mm": x_mm,
                "y_mm": y_mm,
                "width_mm": size[0] if size else None,
                "height_mm": size[1] if size else None,
            })

        x_mm, y_mm = fp_api.get_position_mm(fp)
        nets = sorted({p["net"] for p in pads_data if p["net"]})

        result.append({
            "ref": fp_api.get_reference(fp),
            "value": fp_api.get_value(fp),
            "footprint": fp_api.get_footprint_name(fp),
            "x_mm": x_mm,
            "y_mm": y_mm,
            "angle_deg": fp_api.get_angle_deg(fp),
            "width_mm": size_mm[0] if size_mm else None,
            "height_mm": size_mm[1] if size_mm else None,
            "nets": nets,
            "pads": pads_data,
        })
    return result
