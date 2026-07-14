#!/usr/bin/env python3
"""
Диагностический скрипт: рисует прямоугольник Courtyard компонента на слое User.Drawings.
С принудительным обновлением и сохранением.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse

from core_api import kicad_client, board as board_api, footprints, pads
from core_api.geometry import MM
from kipy.board_types import BoardLayer, BoardRectangle, BoardText
from kipy.geometry import Vector2
from kipy.proto.common.types import KiCadObjectType

# --- Определяем слой User.Drawings ---
if hasattr(BoardLayer, 'BL_User_Drawing'):
    USER_DRAWINGS_LAYER = BoardLayer.BL_User_Drawing
elif hasattr(BoardLayer, 'BL_User_Comments'):
    USER_DRAWINGS_LAYER = BoardLayer.BL_User_Comments
else:
    USER_DRAWINGS_LAYER = 106
    print("Предупреждение: используется числовой код слоя 106 (User.Drawings)")


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


def draw_rectangle_on_user_drawings(board, bbox, ref, layer=USER_DRAWINGS_LAYER):
    x = bbox.pos.x
    y = bbox.pos.y
    w = bbox.size.x
    h = bbox.size.y

    items = []

    # Прямоугольник
    rect = BoardRectangle()
    rect.position = Vector2.from_xy(x, y)
    rect.size = Vector2.from_xy(w, h)
    rect.layer = layer
    rect.width = int(0.1 * MM)
    items.append(rect)

    # Текст
    text = BoardText()
    text.text = f"{ref}\n{bbox.size.x/MM:.2f}x{bbox.size.y/MM:.2f}mm"
    text.position = Vector2.from_xy(x + w//2, y + h//2)
    text.layer = layer
    text.size = Vector2.from_xy(int(1.0 * MM), int(1.0 * MM))
    text.thickness = int(0.15 * MM)
    text.h_justify = "center"
    text.v_justify = "center"
    items.append(text)

    return items


def draw_courtyard_for_component(kicad, board, ref, dry_run=False):
    fp = footprints.get_by_ref(board, ref)
    if fp is None:
        print(f"Компонент {ref} не найден.")
        return False

    bbox = get_courtyard_bounding_box(board, fp)
    if bbox is None:
        print(f"У компонента {ref} нет Courtyard.")
        return False

    if dry_run:
        print(f"[DRY RUN] Был бы нарисован прямоугольник:")
        print(f"  ref: {ref}")
        print(f"  позиция: ({bbox.pos.x/MM:.3f}, {bbox.pos.y/MM:.3f}) мм")
        print(f"  размер: {bbox.size.x/MM:.3f} x {bbox.size.y/MM:.3f} мм")
        return True

    print(f"Создаю объекты на слое {USER_DRAWINGS_LAYER}...")
    items = draw_rectangle_on_user_drawings(board, bbox, ref)

    try:
        commit = board.begin_commit()
        board.create_items(items)
        board.push_commit(commit, f"Диагностика: Courtyard компонента {ref}")
        print("Транзакция зафиксирована.")

        # Принудительно сохраняем плату, чтобы изменения точно попали в файл
        board.save()
        print("Плата сохранена.")

        # Обновляем объект board, чтобы получить свежие данные
        board = kicad.get_board()
        print("Объект board обновлён.")

        # Проверяем, что объекты действительно появились на слое User.Drawings
        all_shapes = board.get_items([KiCadObjectType.KOT_PCB_SHAPE, KiCadObjectType.KOT_PCB_TEXT])
        user_shapes = [s for s in all_shapes if hasattr(s, 'layer') and s.layer == USER_DRAWINGS_LAYER]
        if user_shapes:
            print(f"На слое User.Drawings теперь {len(user_shapes)} объектов.")
        else:
            print("Предупреждение: на слое User.Drawings не найдено объектов после коммита.")

        print(f"Прямоугольник Courtyard для {ref} нарисован на слое User.Drawings.")
        print("Включите слой User.Drawings (или User.Comments) в KiCad, чтобы увидеть его.")
        return True
    except Exception as e:
        print(f"Ошибка при рисовании: {e}")
        import traceback
        traceback.print_exc()
        if 'commit' in locals() and commit is not None:
            board.drop_commit(commit)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Рисует прямоугольник Courtyard компонента на слое User.Drawings."
    )
    parser.add_argument("ref", help="refdes компонента (например, C5)")
    parser.add_argument("--dry-run", action="store_true", help="только показать координаты, не рисовать")
    args = parser.parse_args()

    print("Подключение к KiCad...")
    kicad = kicad_client.connect()
    board = kicad_client.get_board(kicad)
    if board is None:
        print("Не удалось получить плату.")
        sys.exit(1)

    success = draw_courtyard_for_component(kicad, board, args.ref, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()