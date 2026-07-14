#!/usr/bin/env python3
"""
Диагностика размещения via для компонента (с автоматическими повторными попытками при busy).
"""
import argparse
import sys
import time
import math

from pathlib import Path
# Добавляем родительскую папку (где лежит core_api) в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_api import kicad_client, board as board_api, footprints, pads, nets
from core_api.geometry import MM
from kipy.board_types import BoardLayer
from kipy.errors import ApiError


def get_footprint_with_retry(board, ref, logger=None, retries=5, delay=1.0):
    """Пытается получить футпринт с повторными попытками при busy."""
    for attempt in range(retries):
        try:
            return footprints.get_by_ref(board, ref)
        except ApiError as e:
            if "busy" in str(e).lower():
                print(f"  KiCad busy, попытка {attempt+1}/{retries}, жду {delay} с...")
                time.sleep(delay)
                continue
            raise
    return None


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


def diagnose_courtyard(board, fp, gnd_pad, offset_mm, angle_deg=None):
    pad_pos = pads.get_position_mm(gnd_pad)
    cx, cy = pad_pos
    pad_size = pads.get_size_mm(gnd_pad)

    print(f"\n=== GND-пад ===")
    print(f"  номер: {gnd_pad.number}")
    print(f"  центр: ({cx:.3f}, {cy:.3f}) мм")
    if pad_size:
        print(f"  размер: {pad_size[0]:.3f} x {pad_size[1]:.3f} мм")

    courtyard_bbox = get_courtyard_bounding_box(board, fp)
    if courtyard_bbox is None:
        print("  Courtyard: НЕ НАЙДЕН")
        return None

    left = courtyard_bbox.pos.x / MM
    right = (courtyard_bbox.pos.x + courtyard_bbox.size.x) / MM
    bottom = courtyard_bbox.pos.y / MM
    top = (courtyard_bbox.pos.y + courtyard_bbox.size.y) / MM

    print(f"\n=== Courtyard (прямоугольник) ===")
    print(f"  left:   {left:.3f}")
    print(f"  right:  {right:.3f}")
    print(f"  bottom: {bottom:.3f}")
    print(f"  top:    {top:.3f}")
    print(f"  ширина: {right-left:.3f}, высота: {top-bottom:.3f}")

    if angle_deg is None:
        center_x = (left + right) / 2
        center_y = (bottom + top) / 2
        dx = center_x - cx
        dy = center_y - cy
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            angle_deg = 0.0
        else:
            angle_deg = math.degrees(math.atan2(dy, dx))
        print(f"\n=== Направление (авто) ===")
        print(f"  угол к центру Courtyard: {angle_deg:.1f}°")

    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    t_values = []
    if abs(cos_a) > 1e-9:
        t_left = (left - cx) / cos_a
        t_right = (right - cx) / cos_a
        if t_left >= 0:
            y_left = cy + t_left * sin_a
            if bottom <= y_left <= top:
                t_values.append(("left", t_left, cx + t_left*cos_a, cy + t_left*sin_a))
        if t_right >= 0:
            y_right = cy + t_right * sin_a
            if bottom <= y_right <= top:
                t_values.append(("right", t_right, cx + t_right*cos_a, cy + t_right*sin_a))
    if abs(sin_a) > 1e-9:
        t_bottom = (bottom - cy) / sin_a
        t_top = (top - cy) / sin_a
        if t_bottom >= 0:
            x_bottom = cx + t_bottom * cos_a
            if left <= x_bottom <= right:
                t_values.append(("bottom", t_bottom, cx + t_bottom*cos_a, cy + t_bottom*sin_a))
        if t_top >= 0:
            x_top = cx + t_top * cos_a
            if left <= x_top <= right:
                t_values.append(("top", t_top, cx + t_top*cos_a, cy + t_top*sin_a))

    print(f"\n=== Пересечение луча (угол {angle_deg:.1f}°) ===")
    if not t_values:
        print("  Луч НЕ пересекает прямоугольник Courtyard!")
        print("  Будет использован fallback: отступ от края пада.")
        if pad_size:
            edge_dist = distance_to_edge(pad_size, angle_deg)
            total_offset = edge_dist + offset_mm
        else:
            total_offset = offset_mm
        via_x = cx + total_offset * cos_a
        via_y = cy + total_offset * sin_a
        print(f"  fallback: отступ от края пада = {total_offset:.3f} мм")
        print(f"  via будет в ({via_x:.3f}, {via_y:.3f})")
        return

    print("  Точки пересечения:")
    for side, t, x, y in t_values:
        print(f"    {side}: t={t:.3f} мм -> ({x:.3f}, {y:.3f})")
    t_min = min(t for _, t, _, _ in t_values)
    side_min = next(s for s, t, _, _ in t_values if t == t_min)
    print(f"  Ближайшее пересечение: {side_min} на расстоянии {t_min:.3f} мм от центра пада")

    total_offset = t_min + offset_mm
    via_x = cx + total_offset * cos_a
    via_y = cy + total_offset * sin_a

    print(f"\n=== Результат ===")
    print(f"  Расстояние от центра пада до края Courtyard (t_min) = {t_min:.3f} мм")
    print(f"  Заданный отступ от края Courtyard (offset_mm) = {offset_mm:.3f} мм")
    print(f"  Итоговое расстояние от центра пада до via = {total_offset:.3f} мм")
    print(f"  Позиция via: ({via_x:.3f}, {via_y:.3f}) мм")
    print(f"  Это соответствует отступу {offset_mm:.3f} мм от края Courtyard.")


def main():
    parser = argparse.ArgumentParser(description="Диагностика размещения via для компонента")
    parser.add_argument("ref", help="refdes компонента, например C5")
    parser.add_argument("--gnd-net", default="GND", help="имя GND-цепи")
    parser.add_argument("--offset-mm", type=float, default=1.0, help="отступ от края Courtyard (мм)")
    parser.add_argument("--angle-deg", type=float, default=None, help="угол в градусах (если не указан – авто-расчёт)")
    args = parser.parse_args()

    print("Подключение к KiCad...")
    kicad = kicad_client.connect()
    board = kicad_client.get_board(kicad)
    if board is None:
        print("Не удалось получить плату.")
        sys.exit(1)

    print(f"Поиск компонента {args.ref}...")
    fp = get_footprint_with_retry(board, args.ref, retries=5, delay=1.0)
    if fp is None:
        print(f"Компонент {args.ref} не найден после нескольких попыток.")
        sys.exit(1)

    gnd_pad = find_gnd_pad(fp, args.gnd_net)
    if gnd_pad is None:
        print(f"У {args.ref} нет пада с цепью '{args.gnd_net}'.")
        sys.exit(1)

    diagnose_courtyard(board, fp, gnd_pad, args.offset_mm, args.angle_deg)


if __name__ == "__main__":
    main()