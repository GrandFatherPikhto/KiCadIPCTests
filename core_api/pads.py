"""
pads.py — площадки (Pad) компонентов: поиск, координаты, размер, цепь.
"""
from typing import List, Optional, Tuple
from kipy.board_types import FootprintInstance, Pad
from .geometry import MM


def get_all(fp: FootprintInstance) -> List[Pad]:
    """
    Пады футпринта — напрямую из definition.items, БЕЗ похода в API:
    данные уже загружены вместе с футпринтом. Не пытайтесь искать пады
    геометрическим угадыванием "ближайшего компонента" по координатам —
    это ломается, если два компонента стоят вплотную друг к другу (у нас
    после раздвижки конденсаторы иногда всего в 2мм друг от друга).
    """
    return [item for item in fp.definition.items if isinstance(item, Pad)]


def get_by_number(fp: FootprintInstance, number: str) -> Optional[Pad]:
    """Находит конкретную площадку по номеру (например, '1', '145')."""
    for pad in get_all(fp):
        if pad.number == number:
            return pad
    return None


def get_position_mm(pad: Pad) -> Tuple[float, float]:
    """
    (x_mm, y_mm) — АБСОЛЮТНАЯ позиция пада на плате (kipy сам учитывает
    позицию/поворот родительского футпринта, руками пересчитывать не нужно).
    """
    return pad.position.x / MM, pad.position.y / MM


def get_net_name(pad: Pad) -> str:
    """Имя подключённой цепи, или '' если не подключена (N/C)."""
    return pad.net.name if pad.net else ""


def get_size_mm(pad: Pad) -> Optional[Tuple[float, float]]:
    """
    (width_mm, height_mm) — размер первого медного слоя падстека. Для
    обычных однослойных SMD-пад он один; для более сложных падстеков
    (например, THT) может быть несколько слоёв — здесь всегда берётся
    первый. None, если медных слоёв нет вовсе (не должно случаться для
    нормального пада, но лучше не падать, а вернуть None).
    """
    layers = pad.padstack.copper_layers
    if not layers:
        return None
    return layers[0].size.x / MM, layers[0].size.y / MM


def get_angle_deg(pad: Pad) -> float:
    """
    Собственный угол падстека в градусах. kipy держит его синхронизированным
    с поворотом родительского футпринта — отдельно пересчитывать не нужно.
    """
    return pad.padstack.angle.degrees
