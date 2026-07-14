"""
test_board_info.py — сводная информация о плате.
Использует core_api.board.get_info() (добавлено при переносе этого теста —
core_api раньше не имел этой функциональности вовсе).
"""
from runner.registry import register


@register("safe_board_info", suite="safe", needs_kicad=True)
def run_test(logger, kicad, board, **params) -> bool:
    from core_api import board as board_api

    info = board_api.get_info(board)
    logger.info(f"Информация о плате: {info}")

    if info["footprints_count"] == 0:
        logger.warning("На плате 0 футпринтов — возможно, плата пустая или что-то не так")
    if info["board_size_mm"] is None:
        logger.warning("Не удалось определить размер платы (контур Edge.Cuts не найден?)")
    if info["copper_layer_count"] is None:
        logger.warning("Не удалось определить число медных слоёв")

    return True
