"""
test_pads.py — smoke-тест модуля core_api.pads.
Требует параметры ref (refdes) и pad (номер площадки).
"""
from runner.registry import register


@register("smoke_pads", suite="smoke", needs_kicad=True)
def run_test(logger, kicad, board, ref: str = None, pad: str = "1", **params) -> bool:
    from core_api import footprints, pads

    if not ref:
        logger.error("Нужен параметр ref (refdes компонента)")
        return False

    fp = footprints.get_by_ref(board, ref)
    if fp is None:
        logger.error(f"Компонент {ref!r} не найден")
        return False

    all_pads = pads.get_all(fp)
    logger.info(f"Пад у {ref}: {len(all_pads)}")
    if not all_pads:
        logger.error(f"У {ref} нет ни одного пада")
        return False

    target_pad = pads.get_by_number(fp, pad)
    if target_pad is None:
        logger.warning(f"Пада с номером {pad!r} нет — беру первый попавшийся ({all_pads[0].number})")
        target_pad = all_pads[0]

    x, y = pads.get_position_mm(target_pad)
    net = pads.get_net_name(target_pad)
    size = pads.get_size_mm(target_pad)
    angle = pads.get_angle_deg(target_pad)
    logger.info(f"pad {target_pad.number}: pos=({x:.3f},{y:.3f})мм net={net!r} size={size} angle={angle}°")

    return True
