"""
test_kicad_client.py — smoke-тест модуля core_api.kicad_client.
"""
from runner.registry import register


@register("smoke_kicad_client", suite="smoke", needs_kicad=True)
def run_test(logger, kicad, board, **params) -> bool:
    from core_api import kicad_client

    version = kicad_client.get_version(kicad)
    logger.info(f"Версия KiCad: {version}")
    if not version:
        logger.error("get_version вернул пусто")
        return False

    board2 = kicad_client.get_board(kicad)
    if board2 is None:
        logger.error("get_board вернул None")
        return False

    return True
