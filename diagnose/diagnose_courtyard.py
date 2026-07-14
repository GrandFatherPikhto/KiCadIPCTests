#!/usr/bin/env python3
"""
Диагностика геометрии courtyard для компонента.
Показывает:
- позицию GND-пада
- bounding box courtyard (в мм)
- расстояния от центра пада до каждого края courtyard
- пересечение луча с углом angle_deg
"""
import argparse
import sys
import math

from pathlib import Path
# Добавляем родительскую папку (где лежит core_api) в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_api import kicad_client, board as board_api, footprints, pads, nets
from core_api.geometry import MM
from kipy.board_types import BoardLayer


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
    valid = [b for b in bboxes if b is not None]
    if not valid:
        return None
    total = valid[0]
    for b in valid[1:]:
        total.merge(b)
    return total


def main():
    parser = argparse.ArgumentParser(description="Диагностика courtyard")
    parser.add_argument("ref", help="refdes компонента, например C5")
    parser.add_argument("--angle-deg", type=float, default=0.0, help="угол для луча")
    parser.add_argument("--gnd-net", default="GND", help="имя GND-цепи")
    args = parser.parse_args()

    print("Подключение к KiCad...")
    kicad = kicad_client.connect()
    board = kicad_client.get_board(kicad)
    if board is None:
        print("Не удалось получить плату.")
        sys.exit(1)

    fp = footprints.get_by_ref(board, args.ref)
    if fp is None:
        print(f"Компонент {args.ref} не найден.")
        sys.exit(1)

    gnd_pad = find_gnd_pad(fp, args.gnd_net)
    if gnd_pad is None:
        print(f"У {args.ref} нет пада с цепью '{args.gnd_net}'.")
        sys.exit(1)

    pad_pos = pads.get_position_mm(gnd_pad)
    pad_size = pads.get_size_mm(gnd_pad)

    print(f"\n=== Компонент {args.ref} ===")
    print(f"GND-пад: номер {gnd_pad.number}")
    print(f"  центр: ({pad_pos[0]:.3f}, {pad_pos[1]:.3f}) мм")
    if pad_size:
        print(f"  размер: {pad_size[0]:.3f} x {pad_size[1]:.3f} мм")

    courtyard_bbox = get_courtyard_bounding_box(board, fp)
    if courtyard_bbox is None:
        print("  courtyard: НЕ НАЙДЕН")
        sys.exit(0)

    # Преобразуем в мм
    left = courtyard_bbox.pos.x / MM
    right = (courtyard_bbox.pos.x + courtyard_bbox.size.x) / MM
    bottom = courtyard_bbox.pos.y / MM
    top = (courtyard_bbox.pos.y + courtyard_bbox.size.y) / MM

    print("\n=== Courtyard (прямоугольник в мм) ===")
    print(f"  left:   {left:.3f}")
    print(f"  right:  {right:.3f}")
    print(f"  bottom: {bottom:.3f}")
    print(f"  top:    {top:.3f}")
    print(f"  ширина: {right - left:.3f}, высота: {top - bottom:.3f}")

    # Расстояния от центра пада до каждой стороны
    print("\n=== Расстояния от центра пада до границ courtyard ===")
    print(f"  до левой границы:   {pad_pos[0] - left:.3f} мм")
    print(f"  до правой границы:  {right - pad_pos[0]:.3f} мм")
    print(f"  до нижней границы:  {pad_pos[1] - bottom:.3f} мм")
    print(f"  до верхней границы: {top - pad_pos[1]:.3f} мм")

    # Проверка, находится ли пад внутри courtyard
    inside = (left <= pad_pos[0] <= right) and (bottom <= pad_pos[1] <= top)
    print(f"  пад внутри courtyard: {inside}")

    # Вычисление пересечения луча под заданным углом
    angle_rad = math.radians(args.angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    cx, cy = pad_pos

    t_values = []
    # Пересечение с вертикальными границами
    if abs(cos_a) > 1e-9:
        t_left = (left - cx) / cos_a
        t_right = (right - cx) / cos_a
        if t_left >= 0:
            y_left = cy + t_left * sin_a
            if bottom <= y_left <= top:
                t_values.append(("left", t_left))
        if t_right >= 0:
            y_right = cy + t_right * sin_a
            if bottom <= y_right <= top:
                t_values.append(("right", t_right))
    # Пересечение с горизонтальными границами
    if abs(sin_a) > 1e-9:
        t_bottom = (bottom - cy) / sin_a
        t_top = (top - cy) / sin_a
        if t_bottom >= 0:
            x_bottom = cx + t_bottom * cos_a
            if left <= x_bottom <= right:
                t_values.append(("bottom", t_bottom))
        if t_top >= 0:
            x_top = cx + t_top * cos_a
            if left <= x_top <= right:
                t_values.append(("top", t_top))

    print(f"\n=== Пересечение луча (угол {args.angle_deg}°) ===")
    if not t_values:
        print("  Луч НЕ пересекает прямоугольник courtyard!")
        print("  Возможные причины: пад вне courtyard и луч идёт наружу, или угол не попадает в границы.")
    else:
        # Сортируем по возрастанию t
        t_values.sort(key=lambda x: x[1])
        for side, t in t_values:
            x = cx + t * cos_a
            y = cy + t * sin_a
            print(f"  {side}: t = {t:.3f} мм -> точка ({x:.3f}, {y:.3f})")
        t_min = t_values[0][1]
        print(f"  Ближайшее пересечение: {t_values[0][0]} на расстоянии {t_min:.3f} мм")
        print(f"  После добавления offset_mm (например, 1.0) расстояние от центра пада до via будет {t_min + 1.0:.3f} мм")
        print(f"  Это соответствует via в точке ({cx + (t_min + 1.0)*cos_a:.3f}, {cy + (t_min + 1.0)*sin_a:.3f})")

    # Также проверим, совпадает ли полученное смещение с ожидаемым
    # Если пад внутри courtyard и угол 0°, то t_min = right - cx.
    print("\n=== Рекомендация ===")
    if args.angle_deg == 0 and inside:
        print(f"  При угле 0° и паде внутри courtyard, via должен быть на {offset_mm_placeholder} мм правее правой границы.")
        print(f"  Если вы хотите получить расстояние {offset_mm_placeholder} от края courtyard, установите offset_mm = {offset_mm_placeholder}")
    else:
        print("  Проверьте, что offset_mm задаёт нужное расстояние от края courtyard.")


if __name__ == "__main__":
    main()