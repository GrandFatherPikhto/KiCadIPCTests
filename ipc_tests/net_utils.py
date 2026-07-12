#!/usr/bin/env python3
"""
Утилиты для работы с цепями (Net).
"""
def get_net_name(net):
    """Возвращает имя цепи."""
    if hasattr(net, 'name'):
        return net.name
    if hasattr(net, '_proto') and net._proto:
        if hasattr(net._proto, 'name') and hasattr(net._proto.name, 'value'):
            return net._proto.name.value
    return None

def get_net_code(net):
    """Возвращает числовой код цепи."""
    if hasattr(net, 'code'):
        return int(net.code)
    if hasattr(net, '_proto') and net._proto:
        if hasattr(net._proto, 'code') and hasattr(net._proto.code, 'value'):
            return int(net._proto.code.value)
    return None

def find_net_by_name(nets, name):
    """Ищет цепь по имени (регистрозависимо)."""
    for net in nets:
        if get_net_name(net) == name:
            return net
    return None

def build_net_map(board):
    """
    Строит словарь {код: имя} для всех цепей платы.
    Использует board.get_nets().
    """
    net_map = {}
    for net in board.get_nets():
        code = get_net_code(net)
        name = get_net_name(net)
        if code is not None and name is not None:
            net_map[code] = name
    return net_map