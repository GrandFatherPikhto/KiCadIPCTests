#!/usr/bin/env python3
"""
Скрипт для автоматического создания переходных отверстий (via) возле GND-падов.
Поддерживает три режима offset_from:
  - "center"   – отступ от центра пада
  - "edge"     – отступ от края пада
  - "courtyard" – отступ от края Courtyard (слой F.Courtyard / B.Courtyard)
Если угол не задан, он вычисляется автоматически как направление к центру прямоугольника Courtyard.
"""
import sys
from pathlib import Path
# Добавляем родительскую папку (где лежит core_api) в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import math
import yaml

from core_api import kicad_client, board as board_api, footprints, pads, vias, nets
from core_api.geometry import MM
from kipy.board_types import BoardLayer


def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def find_gnd_pad(fp, gnd_net_name):
    for pad in pads.get_all(fp):
        if pads.get_net_name(pad) == gnd_net_name:
            return pad
    return None


def get_courtyard_bounding_box(board, fp):
    courtyard_layers = (BoardLayer.BL_F_CrtYd, BoardLayer.BL_B_CrtYd)
    shapes = [item for item in fp.definition.items
              if hasattr(item, 'layer') and item.layer in courtyard_layers]
    if not shapes:
        return None
    bboxes = board.get_item_bounding_box(shapes)
    if not isinstance(bboxes, list):
        bboxes = [bboxes]
    valid_boxes = [b for b in bboxes if b is not None]
    if not valid_boxes:
        return None
    total = valid_boxes[0]
    for b in valid_boxes[1:]:
        total.merge(b)
    return total


def distance_to_edge(pad_size_mm, angle_deg):
    w, h = pad_size_mm
    if w <= 0 or h <= 0:
        return 0.0
    angle_rad = math.radians(angle_deg)
    cos_a = abs(math.cos(angle_rad))
    sin_a = abs(math.sin(angle_rad))
    dist_x = (w / 2.0) / cos_a if cos_a > 1e-9 else float('inf')
    dist_y = (h / 2.0) / sin_a if sin_a > 1e-9 else float('inf')
    return min(dist_x, dist_y)


def compute_via_position(board, fp, gnd_pad, offset_mm, angle_deg=None, offset_from='edge'):
    pad_pos = pads.get_position_mm(gnd_pad)
    cx, cy = pad_pos

    if offset_from == 'center':
        if angle_deg is None:
            angle_deg = 0.0
        rad = math.radians(angle_deg)
        total_offset = offset_mm

    elif offset_from == 'edge':
        if angle_deg is None:
            angle_deg = 0.0
        pad_size = pads.get_size_mm(gnd_pad)
        if pad_size is None:
            total_offset = offset_mm
        else:
            total_offset = distance_to_edge(pad_size, angle_deg) + offset_mm
        rad = math.radians(angle_deg)

    elif offset_from == 'courtyard':
        courtyard_bbox = get_courtyard_bounding_box(board, fp)
        if courtyard_bbox is None:
            print(f"  [!] Courtyard не найден, использую отступ от края пада")
            if angle_deg is None:
                angle_deg = 0.0
            pad_size = pads.get_size_mm(gnd_pad)
            if pad_size is None:
                total_offset = offset_mm
            else:
                total_offset = distance_to_edge(pad_size, angle_deg) + offset_mm
            rad = math.radians(angle_deg)
        else:
            if angle_deg is None:
                center_x = (courtyard_bbox.pos.x + courtyard_bbox.size.x / 2) / MM
                center_y = (courtyard_bbox.pos.y + courtyard_bbox.size.y / 2) / MM
                dx = center_x - cx
                dy = center_y - cy
                if abs(dx) < 1e-9 and abs(dy) < 1e-9:
                    angle_deg = 0.0
                else:
                    angle_deg = math.degrees(math.atan2(dy, dx))
                print(f"  [auto] угол к центру Courtyard: {angle_deg:.1f}°")

            rad = math.radians(angle_deg)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)

            left = courtyard_bbox.pos.x / MM
            right = (courtyard_bbox.pos.x + courtyard_bbox.size.x) / MM
            bottom = courtyard_bbox.pos.y / MM
            top = (courtyard_bbox.pos.y + courtyard_bbox.size.y) / MM

            t_values = []
            if abs(cos_a) > 1e-9:
                t_left = (left - cx) / cos_a
                t_right = (right - cx) / cos_a
                if t_left >= 0:
                    y_left = cy + t_left * sin_a
                    if bottom <= y_left <= top:
                        t_values.append(t_left)
                if t_right >= 0:
                    y_right = cy + t_right * sin_a
                    if bottom <= y_right <= top:
                        t_values.append(t_right)
            if abs(sin_a) > 1e-9:
                t_bottom = (bottom - cy) / sin_a
                t_top = (top - cy) / sin_a
                if t_bottom >= 0:
                    x_bottom = cx + t_bottom * cos_a
                    if left <= x_bottom <= right:
                        t_values.append(t_bottom)
                if t_top >= 0:
                    x_top = cx + t_top * cos_a
                    if left <= x_top <= right:
                        t_values.append(t_top)

            if not t_values:
                print(f"  [!] Луч не пересекает Courtyard, использую отступ от края пада")
                pad_size = pads.get_size_mm(gnd_pad)
                if pad_size is None:
                    total_offset = offset_mm
                else:
                    total_offset = distance_to_edge(pad_size, angle_deg) + offset_mm
            else:
                t_min = min(t_values)
                total_offset = t_min + offset_mm

    dx = total_offset * math.cos(rad)
    dy = total_offset * math.sin(rad)
    return (pad_pos[0] + dx, pad_pos[1] + dy)


def main():
    parser = argparse.ArgumentParser(
        description="Создание via возле GND-падов с отступом от края Courtyard (или пада)."
    )
    parser.add_argument("config", help="Путь к YAML-файлу")
    args = parser.parse_args()

    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Ошибка загрузки конфига: {e}")
        sys.exit(1)

    comp_list = config.get('components', [])
    gnd_net_name = config.get('gnd_net_name', 'GND')
    via_cfg = config.get('via', {})
    offset_from = via_cfg.get('offset_from', 'edge').lower()
    if offset_from not in ('center', 'edge', 'courtyard'):
        print(f"Ошибка: offset_from должен быть 'center', 'edge' или 'courtyard', получено '{offset_from}'")
        sys.exit(1)

    global_offset_mm = via_cfg.get('offset_mm', 1.0)
    global_angle_deg = via_cfg.get('angle_deg', None)
    drill_mm = via_cfg.get('drill_mm', 0.3)
    diameter_mm = via_cfg.get('diameter_mm', 0.6)

    if not comp_list:
        print("Ошибка: в конфиге не указан список 'components'.")
        sys.exit(1)

    print("Подключение к KiCad...")
    kicad = kicad_client.connect()
    board = kicad_client.get_board(kicad)
    if board is None:
        print("Не удалось получить плату.")
        sys.exit(1)

    gnd_net = nets.get_by_name(board, gnd_net_name)
    if gnd_net is None:
        print(f"Цепь '{gnd_net_name}' не найдена.")
        sys.exit(1)
    print(f"Найдена цепь: {gnd_net_name}")
    print(f"Режим отсчёта: {offset_from}, отступ = {global_offset_mm} мм")
    if global_angle_deg is not None:
        print(f"Угол (глобальный): {global_angle_deg}°")
    else:
        print("Угол: будет вычислен автоматически для каждого компонента (в режиме courtyard)")

    vias_to_create = []
    errors = []

    for item in comp_list:
        ref = item.get('ref')
        if not ref:
            continue

        comp_offset = item.get('offset_mm', global_offset_mm)
        comp_angle = item.get('angle_deg', global_angle_deg)

        fp = footprints.get_by_ref(board, ref)
        if fp is None:
            errors.append(f"Компонент {ref} не найден.")
            continue

        gnd_pad = find_gnd_pad(fp, gnd_net_name)
        if gnd_pad is None:
            errors.append(f"У {ref} нет пада с цепью '{gnd_net_name}'.")
            continue

        via_pos = compute_via_position(board, fp, gnd_pad, comp_offset, comp_angle, offset_from)
        via = vias.make(via_pos, gnd_net, drill_mm, diameter_mm)
        vias_to_create.append(via)
        print(f"  {ref}: пад {gnd_pad.number} -> via в ({via_pos[0]:.3f}, {via_pos[1]:.3f}) мм")

    if errors:
        print("\nПредупреждения:")
        for e in errors:
            print(f"  {e}")

    if not vias_to_create:
        print("Нет via для создания.")
        sys.exit(0)

    print(f"\nСоздаю {len(vias_to_create)} via...")
    try:
        commit = board.begin_commit()
        created = board.create_items(vias_to_create)
        board.push_commit(commit, f"Добавлено {len(created)} via (режим {offset_from})")
        print(f"Успешно создано {len(created)} via.")
    except Exception as e:
        print(f"Ошибка: {e}")
        if 'commit' in locals() and commit is not None:
            board.drop_commit(commit)
        sys.exit(1)

    print("Готово.")


if __name__ == "__main__":
    main()