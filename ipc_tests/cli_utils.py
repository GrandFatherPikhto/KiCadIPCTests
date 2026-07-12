#!/usr/bin/env python3
"""
Утилиты для вызова kicad-cli (не IPC).
"""
import os
import subprocess
import xml.etree.ElementTree as ET

DEFAULT_KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

def export_netlist(schematic_path, output_path, kicad_cli_path=None):
    """
    Экспортирует netlist схемы в XML-формат с помощью kicad-cli.
    Возвращает True при успехе, иначе False.
    """
    if kicad_cli_path is None:
        kicad_cli_path = os.environ.get("KICAD_CLI_PATH", DEFAULT_KICAD_CLI)
    
    if not os.path.exists(kicad_cli_path):
        return False
    if not os.path.exists(schematic_path):
        return False

    cmd = [
        kicad_cli_path,
        "schematic", "export", "netlist",
        "--format", "xml",
        "-o", output_path,
        schematic_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def parse_netlist_xml(xml_path):
    """
    Парсит XML-нетлист и возвращает словарь с информацией о цепях.
    """
    if not os.path.exists(xml_path):
        return None
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        nets_node = root.find("nets")
        if nets_node is None:
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
    except Exception:
        return None