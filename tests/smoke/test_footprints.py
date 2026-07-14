"""
test_footprints.py — smoke-тест модуля core_api.footprints.
Требует параметр ref (refdes существующего на плате компонента).
"""
from runner.registry import register


@register("smoke_footprints", suite="smoke", needs_kicad=True)
def run_test(logger, kicad, board, ref: str = None, **params) -> bool:
    from core_api import footprints

    all_fps = footprints.get_all(board)
    logger.info(f"Всего футпринтов на плате: {len(all_fps)}")
    if not all_fps:
        logger.error("На плате нет ни одного футпринта — нечего проверять")
        return False

    target_ref = ref or footprints.get_reference(all_fps[0])
    fp = footprints.get_by_ref(board, target_ref)
    if fp is None:
        logger.error(f"Компонент {target_ref!r} не найден")
        return False

    x, y = footprints.get_position_mm(fp)
    angle = footprints.get_angle_deg(fp)
    layer = footprints.get_layer(fp)
    logger.info(f"{target_ref}: value={footprints.get_value(fp)!r} "
                f"footprint={footprints.get_footprint_name(fp)!r} "
                f"pos=({x:.3f},{y:.3f})мм angle={angle}° layer={layer} is_back={footprints.is_back(fp)}")

    size = footprints.get_bounding_box_mm(board, fp)
    logger.info(f"Размер (одиночный запрос): {size}")

    sizes = footprints.get_bounding_boxes_mm(board, [fp])
    logger.info(f"Размер (батч-запрос): {sizes}")
    if size is not None and sizes and sizes[0] != size:
        logger.error(f"Одиночный и батч-запрос дали РАЗНЫЕ результаты: {size} vs {sizes[0]}")
        return False

    return True
