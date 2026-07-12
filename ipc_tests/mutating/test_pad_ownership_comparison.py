#!/usr/bin/env python3
"""
test_pad_ownership_comparison.py — permanent-регрессионный тест находки:
"нужен ли геометрический маппинг пэд->футпринт, или можно обойтись без него".

Контекст: README KiCadTemplateCloner обосновывает геометрический маппинг
(ближайший футпринт по евклидову расстоянию) тем, что "у компонентов нет
прямого доступа к своим падам в некоторых версиях kipy". Статический тест
test_static/test_pad_has_no_footprint_backreference подтвердил ПОЛОВИНУ
этого: объекты Pad из board.get_pads() (плоский список ВСЕХ пэдов платы)
действительно не несут обратной ссылки на владеющий футпринт.

Но ipc_tests/component_utils.py уже использует ДРУГОЙ путь — не
board.get_pads(), а footprint.definition.items (для уже известного,
конкретного footprint) — и живой прогон 2026-07-12 13:32:26 показал
реальные имена цепей на пэдах ('+3V3', '+3V3_OSCILL'), не пустые.

Этот тест формализует то однократное наблюдение в постоянно повторяемую
проверку: сравнивает оба пути на РЕАЛЬНОЙ плате и явно проверяет, что
via footprint.definition.items можно получить net БЕЗ геометрии.

Запуск (безопасно, только чтение, не мутирует плату):
    python -m ipc_tests.mutating.test_pad_ownership_comparison
"""
from ipc_tests.core import get_kicad_board, call_ipc, setup_logging
from ipc_tests.board_utils import get_footprints
from ipc_tests.component_utils import get_reference, get_pads, get_pad_net_name


def main():
    logger = setup_logging(log_file="logs/pad_ownership_comparison.log")
    logger.info("=" * 78)
    logger.info("СРАВНЕНИЕ: board.get_pads() (плоский) vs footprint.definition.items")
    logger.info("=" * 78)

    board = get_kicad_board(logger=logger)
    if board is None:
        logger.error("Нет соединения с KiCad.")
        return False

    # --- Путь А: board.get_pads() — плоский список, без владельца ---
    flat_pads, ok = call_ipc(logger, "board.get_pads()", lambda: list(board.get_pads()))
    if not ok:
        logger.error("board.get_pads() недоступен сейчас — возможно, busy (см. test_footprints_probe).")
        return False

    flat_attrs = [a for a in dir(flat_pads[0]) if not a.startswith("_")] if flat_pads else []
    has_owner_ref = any(name in flat_attrs for name in
                         ("footprint", "parent", "reference", "footprint_reference"))
    logger.info(f"Путь А (board.get_pads()): {len(flat_pads)} пэдов всего, "
                f"атрибуты одного пэда: {flat_attrs}")
    logger.info(f"  => есть обратная ссылка на футпринт: {has_owner_ref} "
                f"(ожидание: False — геометрия была бы нужна ИМЕННО для этого пути)")

    # --- Путь Б: footprint.definition.items, по конкретному fp ---
    footprints = get_footprints(board, logger=logger)
    if not footprints:
        logger.error("Нет компонентов на плате.")
        return False

    logger.info(f"\nПуть Б (footprint.definition.items): проверяю первые "
                f"{min(5, len(footprints))} футпринтов из {len(footprints)}")

    resolved_without_geometry = 0
    checked = 0
    for fp in footprints[:5]:
        ref = get_reference(fp)
        pads = get_pads(fp, logger=logger)
        checked += len(pads)
        for pad in pads:
            net_name = get_pad_net_name(pad)
            pad_num = getattr(pad, "number", "?")
            if net_name:
                resolved_without_geometry += 1
            logger.info(f"  {ref}.{pad_num}: net={net_name!r} — получено БЕЗ геометрии, "
                        f"владелец известен по конструкции запроса (мы сами вызвали fp)")

    logger.info(f"\n[ИТОГ] Путь Б дал {resolved_without_geometry}/{checked} пэдов с "
                f"известной цепью, БЕЗ единого geometry-based сопоставления (euclidean "
                f"distance / nearest-footprint), которое использует TemplateCloner.")

    success = checked > 0 and resolved_without_geometry == checked
    if success:
        logger.info(
            "[ВЫВОД] Геометрический маппинг в TemplateCloner не нужен ДЛЯ ТЕХ СЛУЧАЕВ, "
            "когда владеющий footprint уже известен (что верно для extract/place — там "
            "все интересующие футпринты уже выбраны через selection). Достаточно "
            "footprint.definition.items вместо board.get_pads() + nearest-neighbor."
        )
    else:
        logger.warning(
            "[ВЫВОД] Не все пэды дали net через definition.items — возможно, есть "
            "случаи (например, незапаянные пэды или другая версия kipy), где "
            "геометрический маппинг всё же нужен как fallback. Смотрите лог выше "
            "на предмет того, какие именно пэды не разрешились."
        )
    return success


if __name__ == "__main__":
    main()
