#!/usr/bin/env python3
"""
Утилиты для вызова kicad-cli (не IPC).
"""
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

# ИСПРАВЛЕНО (2026-07-12): раньше был один жёстко прописанный путь
# (C:\Program Files\KiCad\10.0\bin\kicad-cli.exe), который не совпал с
# реальной локальной установкой (у Дениса — под AppData\Local\Programs).
# Теперь пробуем несколько типичных мест по очереди + PATH.
_CANDIDATE_PATHS = [
    r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
    r"C:\Program Files (x86)\KiCad\10.0\bin\kicad-cli.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\10.0\kicad-cli.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\10.0\bin\kicad-cli.exe"),
]


def find_kicad_cli(logger=None):
    """
    Ищет kicad-cli.exe: сначала переменная окружения KICAD_CLI_PATH, затем
    несколько типичных путей установки на Windows, затем PATH (shutil.which).
    Возвращает найденный путь или None.
    """
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
        logger.error(
            "kicad-cli.exe не найден. Проверены пути:\n  " + "\n  ".join(tried) +
            "\nЛибо выставьте KICAD_CLI_PATH, либо добавьте свой путь в "
            "_CANDIDATE_PATHS в cli_utils.py."
        )
    return None


def export_netlist(schematic_path, output_path, kicad_cli_path=None, logger=None):
    """
    Экспортирует netlist схемы в XML-формат с помощью kicad-cli.
    Возвращает True при успехе, иначе False.

    ИСПРАВЛЕНО (2026-07-12), два реальных бага:
    1. Команда была "schematic export netlist" — такого subcommand у
       kicad-cli 10 нет. По документации (kicad-cli sch --help) верхний
       subcommand называется "sch", не "schematic":
           kicad-cli sch export netlist --output OUT --format FORMAT INPUT
    2. Формат был "xml" — тоже не существует. Реальные значения --format
       для sch export netlist (см. JOB_EXPORT_SCH_NETLIST в исходниках
       KiCad): kicadxml, kicadsexpr, orcadpcb2, cadstar, pads, spice,
       spicemodel, allegro. Нужен именно "kicadxml".
    Раньше `except subprocess.CalledProcessError: return False` без
    логирования result.stderr — это и маскировало обе ошибки как просто
    "Экспорт netlist не удался" без единой полезной детали.
    """
    if kicad_cli_path is None:
        kicad_cli_path = find_kicad_cli(logger=logger)

    if not kicad_cli_path or not os.path.exists(kicad_cli_path):
        return False
    if not os.path.exists(schematic_path):
        if logger:
            logger.error(f"Файл схемы не найден: {schematic_path}")
        return False

    cmd = [
        kicad_cli_path,
        "sch", "export", "netlist",
        "--format", "kicadxml",
        "--output", output_path,
        schematic_path
    ]
    if logger:
        logger.debug(f"Запуск: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        if logger and result.stdout.strip():
            logger.debug(f"kicad-cli stdout: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        if logger:
            logger.error(
                f"kicad-cli завершился с кодом {e.returncode}.\n"
                f"  stdout: {e.stdout.strip() if e.stdout else '(пусто)'}\n"
                f"  stderr: {e.stderr.strip() if e.stderr else '(пусто)'}"
            )
        return False
    except Exception as e:
        if logger:
            logger.error(f"Не удалось запустить kicad-cli: {type(e).__name__}: {e}")
        return False


def parse_netlist_xml(xml_path, logger=None):
    """
    Парсит XML-нетлист (формат kicadxml) и возвращает список словарей
    {"name": ..., "nodes": [...]}.
    """
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
            nodes = []
            for node in net_elem.findall("node"):
                ref = node.get("ref", "")
                pin = node.get("pin", "")
                nodes.append(f"{ref}.{pin}")
            nets.append({"name": net_name, "nodes": nodes})
        return nets
    except Exception as e:
        if logger:
            logger.error(f"Не удалось распарсить {xml_path}: {type(e).__name__}: {e}")
        return None
