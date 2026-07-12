#!/usr/bin/env python3
"""
Тест получения цепей и их кодов.
"""
from ipc_tests.core import get_kicad_board
from ipc_tests.board_utils import get_nets
from ipc_tests.net_utils import get_net_name, get_net_code, build_net_map

def run_test(logger):
    logger.info("=== ТЕСТ: ЦЕПИ И ИХ КОДЫ ===")
    board = get_kicad_board(logger=logger)
    if board is None:
        return False
    nets = get_nets(board, logger=logger)
    if not nets:
        logger.warning("Цепи не найдены.")
        return False
    logger.info(f"Найдено цепей: {len(nets)}")
    net_map = build_net_map(board)
    logger.info(f"Построена карта цепей: {len(net_map)} записей")
    for code, name in list(net_map.items())[:10]:
        logger.debug(f"  {code}: {name}")
    return True
