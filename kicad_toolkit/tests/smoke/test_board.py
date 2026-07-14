"""
test_board.py — smoke-тест модуля core_api.board.
"""
from runner.registry import register


@register("smoke_board_commit", suite="smoke", needs_kicad=True)
def run_test(logger, kicad, board, **params) -> bool:
    from core_api import board as board_api

    ok = board_api.commit_with_retry(board, "smoke_board_commit: пустая транзакция", lambda: None)
    logger.info(f"commit_with_retry на пустом действии: {ok}")
    return ok
