#!/usr/bin/env python3
"""
Диагностический скрипт для изучения структуры Box2 в kipy.
"""
import sys
from pathlib import Path
# Добавляем родительскую папку (где лежит core_api) в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_api import kicad_client, footprints, board as board_api
from kipy.board_types import BoardLayer
from kipy.proto.common.types import KiCadObjectType

def main():
    print("Подключение к KiCad...")
    kicad = kicad_client.connect()
    board = kicad_client.get_board(kicad)
    if board is None:
        print("Не удалось получить плату.")
        return

    # Найдём любой футпринт с courtyard
    all_fps = footprints.get_all(board)
    if not all_fps:
        print("Нет компонентов.")
        return

    for fp in all_fps:
        courtyard_items = [item for item in fp.definition.items
                           if hasattr(item, 'layer') and item.layer in (BoardLayer.BL_F_CrtYd, BoardLayer.BL_B_CrtYd)]
        if courtyard_items:
            print(f"Найден компонент {footprints.get_reference(fp)} с {len(courtyard_items)} элементами courtyard.")
            bboxes = board.get_item_bounding_box(courtyard_items)
            if not isinstance(bboxes, list):
                bboxes = [bboxes]
            for idx, bbox in enumerate(bboxes):
                if bbox is None:
                    print("  bbox is None")
                    continue
                print(f"  bbox {idx}: type={type(bbox)}")
                print(f"    dir(bbox) = {[a for a in dir(bbox) if not a.startswith('_')]}")
                # Попробуем получить доступ к различным атрибутам
                for attr in ['min', 'max', 'position', 'pos', 'origin', 'size', 'width', 'height', 'x', 'y']:
                    if hasattr(bbox, attr):
                        try:
                            val = getattr(bbox, attr)
                            print(f"    has {attr}: {val}")
                        except Exception as e:
                            print(f"    has {attr} but error: {e}")
                # Также проверим, может быть это просто кортеж или что-то ещё
                print(f"    repr(bbox) = {repr(bbox)}")
            # нам достаточно первого, прервём
            break
    else:
        print("Не найден ни один компонент с courtyard.")

if __name__ == "__main__":
    main()