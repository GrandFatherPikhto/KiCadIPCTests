#!/usr/bin/env python3
"""
Тест инспекции площадок и их цепей.
"""
from ipc_tests.core import get_kicad_board
from ipc_tests.board_utils import get_footprints
from ipc_tests.component_utils import get_reference, get_pads, get_pad_net_name, get_pad_net_code

def run_test(logger):
    logger.info("=== ТЕСТ: ПЛОЩАДКИ И ЦЕПИ ===")
    board = get_kicad_board(logger=logger)
    if board is None:
        return False
    footprints = get_footprints(board, logger=logger)
    if not footprints:
        logger.warning("Нет компонентов.")
        return False
    fp = footprints[0]
    ref = get_reference(fp)
    logger.info(f"Анализируем компонент: {ref}")
    pads = get_pads(fp, logger=logger)
    if not pads:
        logger.warning(f"У компонента {ref} нет площадок.")
        return False
    for pad in pads[:5]:
        pad_num = getattr(pad, 'number', '?')
        net_name = get_pad_net_name(pad)
        net_code = get_pad_net_code(pad)
        logger.info(f"  Пин {pad_num}: цепь '{net_name}' (код {net_code})")
    return True
