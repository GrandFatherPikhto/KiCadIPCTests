"""
test_zones.py — smoke-тест модуля core_api.zones.
Требует параметр zone (имя зоны/Rule Area).
"""
from runner.registry import register


@register("smoke_zones", suite="smoke", needs_kicad=True)
def run_test(logger, kicad, board, zone: str = None, **params) -> bool:
    from core_api import zones

    if not zone:
        logger.warning("Параметр zone не передан — раздел пропущен по факту, не ошибка")
        return True

    z = zones.get_by_name(board, zone)
    if z is None:
        logger.error(f"Зона {zone!r} не найдена")
        return False

    pts = zones.get_boundary_points(z)
    logger.info(f"Зона {zone!r}: точек контура {len(pts)}")
    if len(pts) < 3:
        logger.error(f"Меньше 3 точек контура — не похоже на валидный полигон ({len(pts)})")
        return False

    return True
