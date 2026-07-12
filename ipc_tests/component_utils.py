#!/usr/bin/env python3
"""
Утилиты для работы с компонентами (Footprint) и их площадками (Pad).
"""
def get_reference(footprint):
    """Получает ссылочное обозначение компонента."""
    ref_field = getattr(footprint, 'reference_field', None)
    if ref_field and hasattr(ref_field, 'text'):
        return ref_field.text.value
    # fallback
    return getattr(footprint, 'reference', '?')

def get_value(footprint):
    """Получает номинал компонента."""
    val_field = getattr(footprint, 'value_field', None)
    if val_field and hasattr(val_field, 'text'):
        return val_field.text.value
    return getattr(footprint, 'value', '?')

def get_pads(footprint):
    """Возвращает список площадок (Pad) компонента."""
    # Пробуем через definition
    if hasattr(footprint, 'definition') and footprint.definition:
        return list(footprint.definition.pads)
    # fallback
    return list(getattr(footprint, 'pads', []))

def get_pad_net(pad):
    """Возвращает объект Net для площадки или None."""
    if hasattr(pad, 'net'):
        return pad.net
    return None

def get_pad_net_code(pad):
    """
    Пытается извлечь числовой код цепи для площадки.
    Возвращает int или None.
    """
    net = get_pad_net(pad)
    if net is not None:
        # Сначала пробуем атрибут code
        if hasattr(net, 'code'):
            return int(net.code)
        # Если нет, смотрим в _proto
        if hasattr(net, '_proto') and net._proto:
            proto = net._proto
            if hasattr(proto, 'code') and hasattr(proto.code, 'value'):
                return int(proto.code.value)
    # Если у самого pad есть _proto с полем net.code
    if hasattr(pad, '_proto') and pad._proto:
        proto = pad._proto
        if hasattr(proto, 'net') and proto.net:
            if hasattr(proto.net, 'code') and hasattr(proto.net.code, 'value'):
                return int(proto.net.code.value)
    return None

def get_pad_net_name(pad):
    """Возвращает имя цепи для площадки или None."""
    net = get_pad_net(pad)
    if net is not None:
        if hasattr(net, 'name'):
            return net.name
        # может быть в _proto
        if hasattr(net, '_proto') and net._proto:
            if hasattr(net._proto, 'name') and hasattr(net._proto.name, 'value'):
                return net._proto.name.value
    return None