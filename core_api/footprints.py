"""
footprints.py — поиск, чтение и изменение футпринтов (компонентов платы).
"""
from typing import List, Optional, Tuple
from kipy.board_types import FootprintInstance, BoardLayer
from .geometry import MM


# --- Поиск ---

def get_all(board) -> List[FootprintInstance]:
    """Все футпринты платы."""
    return list(board.get_footprints())


def get_by_ref(board, ref: str) -> Optional[FootprintInstance]:
    """Ищет футпринт по refdes (например, 'C5'). Регистрозависимо."""
    for fp in get_all(board):
        if fp.reference_field.text.value == ref:
            return fp
    return None


# --- Чтение ---

def get_reference(fp: FootprintInstance) -> str:
    """
    Refdes ('C5', 'IC1', ...).

    ИСПРАВЛЕНО (2026-07-14, аудит против component_utils.py): возвращён
    защитный getattr/hasattr с fallback '?' — на случай футпринта без
    reference_field (в реальной практике такого не встречалось, но
    старый код на это подстраховывался, и молчаливое исчезновение этой
    подстраховки при переносе не было осознанным решением).
    """
    ref_field = getattr(fp, "reference_field", None)
    if ref_field is not None and hasattr(ref_field, "text"):
        return ref_field.text.value
    return "?"


def get_value(fp: FootprintInstance) -> str:
    """Номинал/значение ('100nF', '10CL006YE144C8G', ...)."""
    val_field = getattr(fp, "value_field", None)
    if val_field is not None and hasattr(val_field, "text"):
        return val_field.text.value
    return "?"


def get_footprint_name(fp: FootprintInstance) -> str:
    """Имя библиотечного футпринта, например 'Capacitor_SMD:C_0402'."""
    return str(fp.definition.id)


def get_position_mm(fp: FootprintInstance) -> Tuple[float, float]:
    """(x_mm, y_mm) — абсолютная позиция футпринта."""
    return fp.position.x / MM, fp.position.y / MM


def get_angle_deg(fp: FootprintInstance) -> float:
    """Угол поворота в градусах."""
    return fp.orientation.degrees


def get_layer(fp: FootprintInstance) -> BoardLayer:
    """Слой футпринта (BoardLayer.BL_F_Cu / BL_B_Cu). Сравнивать через
    константы BoardLayer, не строками."""
    return fp.layer


def is_back(fp: FootprintInstance) -> bool:
    """True, если футпринт на обратной стороне (B.Cu)."""
    return fp.layer == BoardLayer.BL_B_Cu


def get_bounding_box_mm(board, fp: FootprintInstance) -> Optional[Tuple[float, float]]:
    """
    (width_mm, height_mm) физического контура футпринта (пады + графика,
    БЕЗ учёта надписей на шёлкографии — include_text=False по умолчанию у
    get_item_bounding_box). None, если bounding box недоступен.
    Для ОДНОГО элемента get_item_bounding_box() отдаёт Box2|None напрямую
    (не список) — в отличие от вызова со списком, см. get_bounding_boxes_mm.
    """
    bbox = board.get_item_bounding_box(fp)
    if bbox is None:
        return None
    return bbox.size.x / MM, bbox.size.y / MM


def get_bounding_boxes_mm(board, footprints: List[FootprintInstance]) -> List[Optional[Tuple[float, float]]]:
    """
    То же самое, но ОДНИМ батч-запросом на весь список — дешевле по
    сетевым вызовам, чем дёргать get_bounding_box_mm в цикле по одному.
    ВАЖНО: для СПИСКА элементов get_item_bounding_box() отдаёт
    List[Optional[Box2]] — то есть именно список, в отличие от вызова с
    одним элементом напрямую.
    """
    if not footprints:
        return []
    bboxes = board.get_item_bounding_box(list(footprints))
    if not isinstance(bboxes, list):
        bboxes = [bboxes]
    return [(b.size.x / MM, b.size.y / MM) if b is not None else None for b in bboxes]


# --- Изменение (нужен board.update_items([fp]) внутри коммита, чтобы применить) ---

def set_position(fp: FootprintInstance, x_mm: float, y_mm: float):
    """Меняет позицию ЛОКАЛЬНО на объекте. Само по себе на плату не влияет —
    нужен board.update_items([fp]) внутри транзакции (см. board.py)."""
    from kipy.geometry import Vector2
    fp.position = Vector2.from_xy(int(x_mm * MM), int(y_mm * MM))


def set_angle_deg(fp: FootprintInstance, angle_deg: float):
    """Меняет угол ЛОКАЛЬНО. Как и позиция — нужен update_items() внутри коммита."""
    from kipy.geometry import Angle
    fp.orientation = Angle.from_degrees(angle_deg)


def flip_selected(kicad, board, footprints: List[FootprintInstance]):
    """
    НАСТОЯЩИЙ переворот на обратную сторону — через GUI-action, а НЕ через
    footprint.layer = BL_B_Cu (это меняет только поле в данных и НЕ
    зеркалирует площадки/шёлкографию — визуально ничего не изменится).

    Побочный эффект (эмпирически подтверждено): угол поворота меняется на
    +180° от того, что было — для симметричных 2-контактных компонентов
    (конденсаторы/резисторы) это обычно не важно, если после флипа всё
    равно выставляется собственный целевой угол.

    КРИТИЧНО: после вызова локальные Python-объекты в footprints ещё
    хранят СТАРЫЙ layer/orientation — флип это отдельное GUI-действие, не
    update_items(). Обязательно board.get_footprints() заново (см.
    board.refresh) перед тем, как что-то ещё делать с этими объектами —
    иначе последующий update_items() с устаревшими данными молча откатит
    флип.
    """
    board.clear_selection()
    board.add_to_selection(footprints)
    kicad.run_action("pcbnew.InteractiveEdit.flip")
    board.clear_selection()
