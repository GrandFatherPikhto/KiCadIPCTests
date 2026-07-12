#!/usr/bin/env python3
"""
Утилиты для работы с платой (Board).
"""
from kipy.board_types import BoardLayer
from kipy.proto.common.types import KiCadObjectType


def get_footprints(board, logger=None):
    """Возвращает список всех компонентов (FootprintInstance).

    В отличие от старой версии, ошибка НЕ проглатывается молча — она
    логируется (если передан logger), т.к. раньше именно это скрывало
    настоящую причину "Нет компонентов" (на деле — 'KiCad is busy').
    """
    try:
        return list(board.get_footprints())
    except Exception as e:
        if logger:
            logger.error(f"get_footprints упал: {type(e).__name__}: {e}")
        return []


def get_nets(board, logger=None):
    """Возвращает список всех цепей (Net)."""
    try:
        return list(board.get_nets())
    except Exception as e:
        if logger:
            logger.error(f"get_nets упал: {type(e).__name__}: {e}")
        return []


def get_footprint_by_reference(board, ref, logger=None):
    """Ищет компонент по ссылочному обозначению (регистрозависимо)."""
    for fp in get_footprints(board, logger=logger):
        ref_field = getattr(fp, 'reference_field', None)
        if ref_field and hasattr(ref_field, 'text'):
            if ref_field.text.value == ref:
                return fp
    return None


def get_board_edge_bounding_box(board, logger=None):
    """
    Возвращает bounding box контура платы (слой Edge.Cuts) в виде Box2,
    либо None, если контур не найден/не удалось получить.

    ВАЖНО: в kicad-python 0.7.1 у Board НЕТ метода get_size() — его вызов
    просто кидает AttributeError. Размер платы нужно считать самому: взять
    графику на Edge.Cuts через get_items([KOT_PCB_SHAPE]) и посчитать общий
    bounding box через get_item_bounding_box().
    """
    try:
        shapes = board.get_items([KiCadObjectType.KOT_PCB_SHAPE])
        edge_shapes = [s for s in shapes if getattr(s, "layer", None) == BoardLayer.BL_Edge_Cuts]
        if not edge_shapes:
            if logger:
                logger.warning("На слое Edge.Cuts не найдено ни одной фигуры контура платы")
            return None
        # Для списка элементов get_item_bounding_box возвращает список
        # боксов (по одному на элемент), а не один общий — сводим сами.
        boxes = board.get_item_bounding_box(edge_shapes)
        boxes = [b for b in boxes if b is not None]
        if not boxes:
            return None
        total = boxes[0]
        for b in boxes[1:]:
            total.merge(b)
        return total
    except Exception as e:
        if logger:
            logger.error(f"get_board_edge_bounding_box упал: {type(e).__name__}: {e}")
        return None


def get_board_info(board, logger=None):
    """Возвращает словарь с базовой информацией о плате.

    Все под-вызовы логируют собственные ошибки через передаваемый logger,
    вместо того чтобы тихо превращаться в None/{} как раньше.
    """
    info = {}

    footprints = get_footprints(board, logger=logger)
    info['footprints_count'] = len(footprints)

    nets = get_nets(board, logger=logger)
    info['nets_count'] = len(nets)

    bbox = get_board_edge_bounding_box(board, logger=logger)
    if bbox is not None:
        info['board_size_mm'] = (
            round(bbox.size.x / 1_000_000, 3),
            round(bbox.size.y / 1_000_000, 3),
        )
    else:
        info['board_size_mm'] = None

    try:
        info['copper_layer_count'] = board.get_copper_layer_count()
    except Exception as e:
        if logger:
            logger.error(f"get_copper_layer_count упал: {type(e).__name__}: {e}")
        info['copper_layer_count'] = None

    return info
