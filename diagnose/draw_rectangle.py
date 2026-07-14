import sys
from kipy import KiCad
from kipy.board_types import BoardLayer, BoardShape, ShapeType
from kipy.geometry import Vector2
from kipy.util import from_mm

def draw_rectangle_kipy():
    try:
        # 1. Подключаемся к запущенной сессии KiCad
        kicad = KiCad()
        board = kicad.get_board()
        
        # 2. Переводим миллиметры в нанометры (внутренние единицы IPC API)
        start_x = from_mm(10.0)
        start_y = from_mm(10.0)
        end_x = from_mm(50.0)
        end_y = from_mm(30.0)

        # 3. Открываем транзакцию (Commit) для безопасного изменения платы
        with board.begin_commit() as commit:
            
            # Создаем пустой графический объект для платы
            rect_shape = BoardShape()
            
            # Назначаем тип фигуры — Прямоугольник
            rect_shape.shape = ShapeType.RECTANGLE
            
            # Привязываем к нужному слою (в API слои имеют префикс BL_)
            rect_shape.layer = BoardLayer.BL_User_Drawings
            
            # Задаем толщину линии (например, 0.15 мм)
            rect_shape.stroke.width = from_mm(0.15)
            
            # Задаем координаты углов прямоугольника (в kipy это векторы типа Vector2)
            rect_shape.start = Vector2(start_x, start_y)
            rect_shape.end = Vector2(end_x, end_y)
            
            # Добавляем объект на плату через коммит
            commit.add(rect_shape)
            
        print("Прямоугольник успешно отрисован через kipy на User.Drawings!")

    except Exception as e:
        print(f"Ошибка выполнения скрипта: {e}")

if __name__ == "__main__":
    draw_rectangle_kipy()
