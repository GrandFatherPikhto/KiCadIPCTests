"""
nets.py — цепи (Net) платы.
"""
from typing import List, Optional, Dict
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


def build_net_map(board) -> Dict[int, str]:
    """
    Строит словарь {код: имя} для всех цепей платы.

    ЧЕСТНОЕ ПРИМЕЧАНИЕ: Net.code в kicad-python 0.7.1 официально помечен
    deprecated ("будет удалён в KiCad 10, клиентам API не следует
    полагаться на net codes") — подтверждено нашим же контрактным тестом
    static_net_code_deprecated_but_present. Современной "замены" в смысле
    отдельной функции здесь НЕТ и, похоже, не нужна: везде, где мы реально
    работаем с цепями в этом проекте (пады, футпринты), API и так
    возвращает целиком объект Net с прямым .name — числовой код нигде не
    требуется как промежуточное звено. Эта функция оставлена только для
    отладочного вывода/обратной совместимости, не как рекомендуемый путь.
    """
    net_map: Dict[int, str] = {}
    for net in get_all(board):
        try:
            code = int(net.code)
        except (TypeError, ValueError, AttributeError):
            continue
        if net.name:
            net_map[code] = net.name
    return net_map
