"""
core_api — дистиллированный, проверенный на живом KiCad 10.0.4 набор
тонких обёрток над kicad-python (kipy 0.7.1). Каждый модуль — один
класс/область kipy:

    kicad_client — подключение, run_action, версия
    board        — refresh, begin/push/drop_commit, commit_with_retry
    footprints   — поиск/чтение/изменение футпринтов, флип
    pads         — площадки компонентов: координаты, размер, цепь
    vias         — создание/удаление переходных отверстий
    zones        — зоны/Rule Area, точки контура
    nets         — цепи платы
    selection    — работа с выделением (в т.ч. Group), сводка по компоненту
    geometry     — MM и мелкие хелперы поверх Vector2/Angle/Box2

Импортировать явно нужный модуль, например:
    from core_api import footprints, pads
    fp = footprints.get_by_ref(board, "C5")
    pad = pads.get_by_number(fp, "1")

Смотри test_api.py — там же живые примеры использования каждой функции.
"""
