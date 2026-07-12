#!/usr/bin/env python3
"""
Утилиты для работы с компонентами (FootprintInstance) и их площадками (Pad).
"""
from kipy.board_types import Pad


def get_reference(footprint):
    """Получает ссылочное обозначение компонента."""
    ref_field = getattr(footprint, 'reference_field', None)
    if ref_field and hasattr(ref_field, 'text'):
        return ref_field.text.value
    return '?'


def get_value(footprint):
    """Получает номинал компонента."""
    val_field = getattr(footprint, 'value_field', None)
    if val_field and hasattr(val_field, 'text'):
        return val_field.text.value
    return '?'


def get_pads(footprint, logger=None):
    """Возвращает список площадок (Pad) компонента.

    ИСПРАВЛЕНО: в kicad-python 0.7.1 у Footprint (definition футпринта) НЕТ
    атрибута .pads — площадки лежат внутри definition.items вперемешку с
    Field/Zone/BoardShape/BoardText. Раньше код обращался к
    footprint.definition.pads, который просто не существует — это ловилось
    бы AttributeError, если бы вызывающий код не заворачивал всё в try/except
    и не терял ошибку молча.
    """
    try:
        if not hasattr(footprint, 'definition') or footprint.definition is None:
            return []
        return [item for item in footprint.definition.items if isinstance(item, Pad)]
    except Exception as e:
        if logger:
            logger.error(f"get_pads({get_reference(footprint)}) упал: {type(e).__name__}: {e}")
        return []


def get_pad_net(pad):
    """Возвращает объект Net для площадки или None."""
    return getattr(pad, 'net', None)


def get_pad_net_code(pad):
    """Возвращает числовой код цепи для площадки, либо None."""
    net = get_pad_net(pad)
    if net is not None and hasattr(net, 'code'):
        try:
            return int(net.code)
        except (TypeError, ValueError):
            return None
    return None


def get_pad_net_name(pad):
    """Возвращает имя цепи для площадки, либо None (в т.ч. для незапаянных)."""
    net = get_pad_net(pad)
    if net is not None and hasattr(net, 'name'):
        return net.name or None
    return None
