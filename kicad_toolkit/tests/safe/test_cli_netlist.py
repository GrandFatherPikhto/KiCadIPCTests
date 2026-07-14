"""
test_cli_netlist.py — экспорт netlist через kicad-cli.

ОТДЕЛЬНАЯ КАТЕГОРИЯ: kicad-cli — это subprocess, не kipy/IPC. cli_utils.py
намеренно лежит рядом с этим тестом, а не в core_api (core_api — про IPC).
Единственная точка соприкосновения с core_api — получение пути к схеме
через core_api.project, дальше всё идёт через отдельный, честно другой
механизм.

Занимает заметно больше времени, чем остальные safe-тесты (~19с по
реальному прогону) — экспорт схемы через внешний процесс kicad-cli, не
через IPC.
"""
import os
import tempfile

from runner.registry import register
from tests.safe.cli_utils import export_netlist, parse_netlist_xml


@register("safe_cli_netlist", suite="safe", needs_kicad=True)
def run_test(logger, kicad, board, **params) -> bool:
    from core_api import project

    sch_path = project.get_schematic_path(board)
    if not sch_path or not os.path.exists(sch_path):
        logger.error(f"Файл схемы не найден: {sch_path}")
        return False

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        success = export_netlist(sch_path, tmp_path, logger=logger)
        if not success:
            logger.error("Экспорт netlist не удался (детали см. строками ERROR выше)")
            return False
        logger.info("Netlist экспортирован успешно")

        nets = parse_netlist_xml(tmp_path, logger=logger)
        if nets is None:
            logger.warning("Не удалось распарсить XML")
            return False

        logger.info(f"Найдено цепей в netlist: {len(nets)}")
        for net in nets[:5]:
            logger.info(f"  Цепь {net['name']!r}: узлы {net['nodes'][:3]}...")
        return True
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
