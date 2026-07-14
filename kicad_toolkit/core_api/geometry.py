"""
geometry.py — общие константы и мелкие геометрические хелперы поверх
kipy.geometry (Vector2 / Angle / Box2).

Всё в проекте меряется в нанометрах внутри kipy — MM переводит мм<->нм.
"""

MM = 1_000_000  # внутренние единицы kipy (нанометры) на один миллиметр


def vec_mm(x_mm: float, y_mm: float):
    """Строит Vector2 из координат в мм (внутри — целые нанометры)."""
    from kipy.geometry import Vector2
    return Vector2.from_xy(int(x_mm * MM), int(y_mm * MM))


def to_mm(vector) -> tuple:
    """(x_mm, y_mm) из произвольного Vector2."""
    return vector.x / MM, vector.y / MM


def bbox_size_mm(bbox) -> tuple:
    """
    (width_mm, height_mm) из Box2.pos/Box2.size (НЕ .min/.max — это
    настоящие поля в kipy, легко перепутать по аналогии с другими библиотеками).
    Вызывающий код сам решает, что делать, если bbox is None — здесь
    только конвертация уже существующего объекта.
    """
    return bbox.size.x / MM, bbox.size.y / MM
