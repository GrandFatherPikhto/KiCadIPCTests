#!/usr/bin/env python3
"""
Утилиты для работы с цепями (Net).
"""

def get_net_name(net):
    """Возвращает имя цепи."""
    return net.name if net is not None else None


def get_net_code(net):
    """
    Возвращает числовой код цепи.

    ПРИМЕЧАНИЕ: Net.code в kicad-python 0.7.1 официально помечен
    @deprecated ("This property will be removed in KiCad 10; API clients
    should not rely on net codes") — используйте net.name для сопоставления
    цепей, где это возможно. Оставлено здесь только для отладочного вывода.
    """
    if net is None:
        return None
    try:
        return int(net.code)
    except (TypeError, ValueError, AttributeError):
        return None


def find_net_by_name(nets, name):
    """Ищет цепь по имени (регистрозависимо)."""
    for net in nets:
        if get_net_name(net) == name:
            return net
    return None


def build_net_map(board):
    """Строит словарь {код: имя} для всех цепей платы через board.get_nets()."""
    net_map = {}
    for net in board.get_nets():
        code = get_net_code(net)
        name = get_net_name(net)
        if code is not None and name is not None:
            net_map[code] = name
    return net_map
