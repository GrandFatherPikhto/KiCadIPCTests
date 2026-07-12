#!/usr/bin/env python3
"""
Тест инспекции компонентов (референс, номинал, количество площадок).
"""
from ipc_tests.core import get_kicad_board
from ipc_tests.board_utils import get_footprints
from ipc_tests.component_utils import get_reference, get_value, get_pads

def run_test(logger):
    logger.info("=== ТЕСТ: ИНСПЕКЦИЯ КОМПОНЕНТОВ ===")
    board = get_kicad_board(logger=logger)
    if board is None:
        return False
    footprints = get_footprints(board, logger=logger)
    if not footprints:
        logger.warning("Нет компонентов (см. лог выше — если это get_footprints "
                        "упал с ошибкой, а не реально пустой список, причина будет "
                        "явно записана строкой ERROR над этим сообщением).")
        return False
    logger.info(f"Всего компонентов: {len(footprints)}")
    for fp in footprints[:10]:
        ref = get_reference(fp)
        val = get_value(fp)
        pads_count = len(get_pads(fp, logger=logger))
        logger.info(f"  {ref} ({val}) – площадок: {pads_count}")
    return True
