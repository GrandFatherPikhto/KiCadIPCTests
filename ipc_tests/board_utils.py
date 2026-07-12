#!/usr/bin/env python3
"""
Утилиты для работы с платой (Board).
"""
from kipy import KiCad

def get_footprints(board):
    """Возвращает список всех компонентов (Footprint)."""
    try:
        return list(board.get_footprints())
    except Exception as e:
        return []

def get_nets(board):
    """Возвращает список всех цепей (Net)."""
    try:
        return list(board.get_nets())
    except Exception as e:
        return []

def get_footprint_by_reference(board, ref):
    """Ищет компонент по ссылочному обозначению (регистрозависимо)."""
    for fp in get_footprints(board):
        ref_field = getattr(fp, 'reference_field', None)
        if ref_field and hasattr(ref_field, 'text'):
            if ref_field.text.value == ref:
                return fp
        # fallback
        if hasattr(fp, 'reference') and fp.reference == ref:
            return fp
    return None

def get_board_info(board):
    """Возвращает словарь с базовой информацией о плате."""
    info = {}
    try:
        info['footprints_count'] = len(get_footprints(board))
    except:
        info['footprints_count'] = None
    try:
        info['nets_count'] = len(get_nets(board))
    except:
        info['nets_count'] = None
    # Попробуем получить размеры
    try:
        info['board_size'] = board.get_size()
    except:
        info['board_size'] = None
    # Количество слоёв
    try:
        info['copper_layer_count'] = board.get_copper_layer_count()
    except:
        info['copper_layer_count'] = None
    return info