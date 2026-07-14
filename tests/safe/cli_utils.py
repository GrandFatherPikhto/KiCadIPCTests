"""
cli_utils.py — утилиты для вызова kicad-cli (НЕ IPC/kipy, отдельный
subprocess-механизм). Намеренно НЕ в core_api — core_api про IPC, это
про кое-что честно другое.
"""
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

_CANDIDATE_PATHS = [
    r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
    r"C:\Program Files (x86)\KiCad\10.0\bin\kicad-cli.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\10.0\kicad-cli.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\10.0\bin\kicad-cli.exe"),
]


def find_kicad_cli(logger=None):
    """Ищет kicad-cli: сначала KICAD_CLI_PATH, затем типичные пути установки, затем PATH."""
    env_path = os.environ.get("KICAD_CLI_PATH")
    if env_path:
        if os.path.exists(env_path):
            return env_path
        if logger:
            logger.warning(f"KICAD_CLI_PATH={env_path!r} указан, но файл не найден — ищу дальше")

    for path in _CANDIDATE_PATHS:
        if os.path.exists(path):
            if logger:
                logger.debug(f"kicad-cli найден по стандартному пути: {path}")
            return path

    which_path = shutil.which("kicad-cli") or shutil.which("kicad-cli.exe")
    if which_path:
        if logger:
            logger.debug(f"kicad-cli найден через PATH: {which_path}")
        return which_path

    if logger:
        tried = ([env_path] if env_path else []) + _CANDIDATE_PATHS
        logger.error("kicad-cli не найден. Проверены пути:\n  " + "\n  ".join(tried) +
                     "\nЛибо выставьте KICAD_CLI_PATH, либо добавьте путь в _CANDIDATE_PATHS.")
    return None


def export_netlist(schematic_path, output_path, kicad_cli_path=None, logger=None):
    """
    Экспортирует netlist схемы в XML через kicad-cli. Возвращает True при успехе.

    Верные значения (проверено, не по документации на глаз):
    subcommand "sch" (не "schematic"), --format "kicadxml" (не "xml").
    """
    if kicad_cli_path is None:
        kicad_cli_path = find_kicad_cli(logger=logger)
    if not kicad_cli_path or not os.path.exists(kicad_cli_path):
        return False
    if not os.path.exists(schematic_path):
        if logger:
            logger.error(f"Файл схемы не найден: {schematic_path}")
        return False

    cmd = [kicad_cli_path, "sch", "export", "netlist",
           "--format", "kicadxml", "--output", output_path, schematic_path]
    if logger:
        logger.debug(f"Запуск: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        if logger and result.stdout.strip():
            logger.debug(f"kicad-cli stdout: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        if logger:
            logger.error(f"kicad-cli завершился с кодом {e.returncode}.\n"
                        f"  stdout: {e.stdout.strip() if e.stdout else '(пусто)'}\n"
                        f"  stderr: {e.stderr.strip() if e.stderr else '(пусто)'}")
        return False
    except Exception as e:
        if logger:
            logger.error(f"Не удалось запустить kicad-cli: {type(e).__name__}: {e}")
        return False


def parse_netlist_xml(xml_path, logger=None):
    """Парсит XML-нетлист (формат kicadxml), возвращает список {"name", "nodes"}."""
    if not os.path.exists(xml_path):
        if logger:
            logger.error(f"Файл нетлиста не найден: {xml_path}")
        return None
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        nets_node = root.find("nets")
        if nets_node is None:
            if logger:
                logger.error("В XML нет узла <nets> — формат экспорта не тот, что ожидался")
            return None
        nets = []
        for net_elem in nets_node.findall("net"):
            net_name = net_elem.get("name", "")
            nodes = [f"{n.get('ref', '')}.{n.get('pin', '')}" for n in net_elem.findall("node")]
            nets.append({"name": net_name, "nodes": nodes})
        return nets
    except Exception as e:
        if logger:
            logger.error(f"Не удалось распарсить {xml_path}: {type(e).__name__}: {e}")
        return None
