"""
test_nets.py — smoke-тест модуля core_api.nets.
Требует параметр net (имя цепи, по умолчанию 'GND').
"""
from runner.registry import register


@register("smoke_nets", suite="smoke", needs_kicad=True)
def run_test(logger, kicad, board, net: str = "GND", **params) -> bool:
    from core_api import nets

    all_nets = nets.get_all(board)
    logger.info(f"Всего цепей на плате: {len(all_nets)}")
    if not all_nets:
        logger.error("На плате нет ни одной цепи")
        return False

    found = nets.get_by_name(board, net)
    if found is None:
        logger.error(f"Цепь {net!r} не найдена")
        return False

    logger.info(f"Найдена цепь: {found.name}")
    return True
