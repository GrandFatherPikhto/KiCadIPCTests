#!/usr/bin/env python3
"""
Тест экспорта netlist через kicad-cli.
"""
import os
import tempfile
from ipc_tests.core import get_kicad_board
from ipc_tests.project_utils import get_schematic_path
from ipc_tests.cli_utils import export_netlist, parse_netlist_xml

def run_test(logger):
    logger.info("=== ТЕСТ: ЭКСПОРТ NETLIST ЧЕРЕЗ CLI ===")
    board = get_kicad_board(logger=logger)
    if board is None:
        return False
    sch_path = get_schematic_path(board)
    if not sch_path or not os.path.exists(sch_path):
        logger.error("Файл схемы не найден.")
        return False
    # Создаём временный файл для netlist
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        success = export_netlist(sch_path, tmp_path)
        if not success:
            logger.error("Экспорт netlist не удался.")
            return False
        logger.info("Netlist экспортирован успешно.")
        nets = parse_netlist_xml(tmp_path)
        if nets is None:
            logger.warning("Не удалось распарсить XML.")
            return False
        logger.info(f"Найдено цепей в netlist: {len(nets)}")
        for net in nets[:5]:
            logger.info(f"  Цепь '{net['name']}': узлы {net['nodes'][:3]}...")
        return True
    finally:
        try:
            os.remove(tmp_path)
        except:
            pass