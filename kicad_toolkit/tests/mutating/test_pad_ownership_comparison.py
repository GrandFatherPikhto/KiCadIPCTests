"""
test_pad_ownership_comparison.py — постоянный регрессионный тест находки:
"нужен ли геометрический маппинг пэд->футпринт, или можно обойтись без него".

README KiCadTemplateCloner обосновывает геометрический маппинг (ближайший
футпринт по евклидову расстоянию) тем, что "у компонентов нет прямого
доступа к своим падам в некоторых версиях kipy". Статический тест
static_pad_has_no_footprint_backreference подтвердил ПОЛОВИНУ этого:
board.get_pads() (плоский список ВСЕХ пад платы) действительно не несёт
обратной ссылки на футпринт.

Но core_api.pads уже использует ДРУГОЙ путь — footprint.definition.items
для уже известного, конкретного футпринта — этот тест сравнивает оба
пути на реальной плате.

НЕ ОПАСНЫЙ: только чтение, ничего не мутирует на плате.
"""
from runner.registry import register
from runner.step_helper import call_step


@register("mutating_pad_ownership_comparison", suite="mutating", dangerous=False, needs_kicad=True)
def run_test(logger, kicad, board, **params) -> bool:
    from core_api import footprints, pads

    # --- Путь А: board.get_pads() — плоский список, без владельца ---
    flat_pads, ok = call_step(logger, "board.get_pads()", lambda: list(board.get_pads()))
    if not ok:
        logger.error("board.get_pads() недоступен сейчас (возможно, busy)")
        return False

    flat_attrs = [a for a in dir(flat_pads[0]) if not a.startswith("_")] if flat_pads else []
    has_owner_ref = any(name in flat_attrs for name in
                         ("footprint", "parent", "reference", "footprint_reference"))
    logger.info(f"Путь А (board.get_pads()): {len(flat_pads)} пад всего")
    logger.info(f"  => есть обратная ссылка на футпринт: {has_owner_ref} "
                f"(ожидание: False — геометрия была бы нужна ИМЕННО для этого пути)")

    # --- Путь Б: footprint.definition.items, по конкретному fp ---
    all_fps = footprints.get_all(board)
    if not all_fps:
        logger.error("Нет компонентов на плате")
        return False

    sample = all_fps[:5]
    logger.info(f"Путь Б (footprint.definition.items): проверяю первые {len(sample)} из {len(all_fps)}")

    resolved_without_geometry = 0
    checked = 0
    for fp in sample:
        ref = footprints.get_reference(fp)
        pads_list = pads.get_all(fp)
        checked += len(pads_list)
        for pad in pads_list:
            net_name = pads.get_net_name(pad)
            if net_name:
                resolved_without_geometry += 1
            logger.info(f"  {ref}.{pad.number}: net={net_name!r} — получено БЕЗ геометрии, "
                        f"владелец известен по конструкции запроса")

    logger.info(f"Путь Б: {resolved_without_geometry}/{checked} пад с известной цепью, "
                f"БЕЗ geometry-based сопоставления")

    success = checked > 0 and resolved_without_geometry == checked
    if success:
        logger.info("Геометрический маппинг не нужен, когда владеющий footprint уже известен "
                    "(верно для extract/place — там футпринт уже выбран через selection)")
    else:
        logger.warning("Не все пады дали net через definition.items — возможен fallback-случай "
                       "(незапаянные пады, другая версия kipy) — см. лог выше")
    return success
