"""
test_kipy_contract.py — статические контрактные проверки установленной
библиотеки kicad-python (kipy), БЕЗ подключения к живому KiCad.

Перенесено из ipc_tests/mutating/test_kipy_contract.py (2026-07-12) с
исправлением пути (файл раньше физически лежал в mutating/, а
run_static_tests.py импортировал его из static/ — отсюда ModuleNotFoundError
при запуске задокументированной командой; см. историю аудита). Здесь этот
класс бага в принципе невозможен — раннер обнаруживает тесты через
единый пакет tests/, а не через ручной импорт по строковому пути.

Каждая проверка — конкретная строка кода из KiCadTemplateCloner или
KiCadDecapPlacer, воспроизведённая напрямую против установленной kipy —
не предположение, а факт, проверяемый одним импортом библиотеки.
"""
import inspect
import math

from runner.registry import register


@register("static_via_drill_attribute_name", suite="static")
def test_via_drill_attribute_name(logger, **params) -> bool:
    """
    Источник: KiCadTemplateCloner/template_cloner/extractor.py:99,
    applier.py:20 — оба обращаются к несуществующему via.drill.diameter.
    Верно (DecapPlacer): via.drill_diameter (плоский атрибут).
    """
    from kipy.board_types import Via
    v = Via()
    has_nested_drill = hasattr(v, "drill")
    has_flat_drill = hasattr(v, "drill_diameter")

    ok = has_flat_drill and not has_nested_drill
    logger.info(f"hasattr(v,'drill')={has_nested_drill}, hasattr(v,'drill_diameter')={has_flat_drill}")
    if has_flat_drill and not has_nested_drill:
        logger.info("КОНФИРМ: extractor.py/applier.py обращаются к несуществующему .drill "
                    "(extractor всегда падает на default 0.3, applier кидает AttributeError)")
    return ok


@register("static_footprint_orientation_property_name", suite="static")
def test_footprint_orientation_property_name(logger, **params) -> bool:
    """
    Источник: extractor.py:80 — hasattr(fp.orientation, 'as_degrees') всегда
    False, angle в каждом извлечённом компоненте молча теряется (=0.0).
    Верно: свойство .degrees, метода .as_degrees() не существует.
    """
    from kipy.geometry import Angle
    a = Angle.from_degrees(45.0)
    has_method = hasattr(a, "as_degrees")
    has_property = hasattr(a, "degrees") and a.degrees == 45.0

    ok = has_property and not has_method
    logger.info(f"hasattr(a,'as_degrees')={has_method}, a.degrees={a.degrees}")
    if not has_method:
        logger.info("КОНФИРМ: angle в каждом извлечённом компоненте = 0.0, поворот теряется молча")
    return ok


@register("static_footprint_get_layer_method", suite="static")
def test_footprint_get_layer_method(logger, **params) -> bool:
    """
    Источник: extractor.py:78 — hasattr(fp, 'get_layer') всегда False,
    слой в каждом компоненте хардкодится в 'F.Cu'.
    Верно: свойство .layer, метода .get_layer() не существует.
    """
    from kipy.board_types import FootprintInstance
    fp = FootprintInstance()
    has_method = hasattr(fp, "get_layer")
    has_property = hasattr(fp, "layer")

    ok = has_property and not has_method
    logger.info(f"hasattr(fp,'get_layer')={has_method}")
    if not has_method:
        logger.info("КОНФИРМ: layer в каждом извлечённом компоненте = 'F.Cu' (хардкод), сторона платы теряется")
    return ok


@register("static_getter_returns_copy_not_reference", suite="static")
def test_getter_returns_copy_not_reference(logger, **params) -> bool:
    """
    САМАЯ важная находка. Источник: applier.py:17-19, 73-74 —
    fp.position.x = ...  /  via.position.x = ...
    Геттеры вроде .position оборачивают proto через CopyFrom() — то есть
    возвращают НЕЗАВИСИМУЮ КОПИЮ, а не живую ссылку. Присваивание атрибуту
    полученной копии — тихий no-op, без исключения.
    Верно (DecapPlacer executor.py): fp.position = Vector2.from_xy(...) —
    переприсвоить объект ЦЕЛИКОМ.
    """
    from kipy.board_types import FootprintInstance
    from kipy.geometry import Vector2

    fp = FootprintInstance()
    fp.position = Vector2.from_xy(1_000_000, 2_000_000)

    before_x = fp.position.x
    fp.position.x = 99_000_000  # точно как в applier.py
    after_x = fp.position.x

    is_noop = (after_x == before_x) and (after_x != 99_000_000)
    logger.info(f"было {before_x}, после .x=99000000 читаем снова: {after_x}")
    if is_noop:
        logger.info("КОНФИРМ: applier.py's 'fp.position.x = ...' и 'via.position.x = ...' "
                    "не двигают компонент/via вообще никак — тихий no-op")
    return is_noop


@register("static_net_assignment_via_attribute_is_noop", suite="static")
def test_net_assignment_via_attribute_is_noop(logger, **params) -> bool:
    """
    Тот же класс бага, что и с position, но для Net. Источник:
    applier.py:23, 39 — via.net.name = ..., tr.net.name = ...
    Верно (DecapPlacer create_via): via.net = net_obj (объект целиком).
    """
    from kipy.board_types import Via, Net

    v = Via()
    net = Net(name="GND")
    v.net = net

    before_name = v.net.name
    v.net.name = "CHANGED_VIA_ATTRIBUTE_ASSIGNMENT"
    after_name = v.net.name

    is_noop = (after_name == before_name) and (after_name != "CHANGED_VIA_ATTRIBUTE_ASSIGNMENT")
    logger.info(f"было {before_name!r}, после .name=... читаем снова: {after_name!r}")
    if is_noop:
        logger.info("КОНФИРМ: applier.py's 'via.net.name = ...' / 'tr.net.name = ...' — тихий no-op")
    return is_noop


@register("static_orientation_setter_rejects_raw_float", suite="static")
def test_orientation_setter_rejects_raw_float(logger, **params) -> bool:
    """
    Источник: applier.py:78 — fp.orientation = math.radians(comp.angle).
    Setter .orientation ожидает объект Angle, а не сырое число.
    """
    from kipy.board_types import FootprintInstance

    fp = FootprintInstance()
    raised = False
    exc_info = ""
    try:
        fp.orientation = math.radians(45.0)  # точно как в applier.py
    except Exception as e:
        raised = True
        exc_info = f"{type(e).__name__}: {e}"

    logger.info(exc_info or "исключение не возникло")
    if raised:
        logger.info("КОНФИРМ: apply_template() падает на ПЕРВОМ компоненте, до create_via/push_commit. "
                    "Верно (DecapPlacer): fp.orientation = cmd.angle, где cmd.angle — kipy.geometry.Angle")
    return raised


@register("static_push_commit_requires_commit_argument", suite="static")
def test_push_commit_requires_commit_argument(logger, **params) -> bool:
    """
    Источник: applier.py:92 — board.push_commit() без аргументов, и
    begin_commit() нигде не вызывался. Сигнатура: push_commit(commit,
    message='') — commit обязателен и позиционен, вызов без него — TypeError.
    """
    from kipy.board import Board
    sig = inspect.signature(Board.push_commit)
    params_list = list(sig.parameters.values())
    commit_param = next((p for p in params_list if p.name == "commit"), None)
    commit_required = commit_param is not None and commit_param.default is inspect.Parameter.empty

    logger.info(str(sig))
    if commit_required:
        logger.info("КОНФИРМ: applier.py's 'board.push_commit()' кидает TypeError "
                    "(missing 1 required positional argument: 'commit')")
    return commit_required


@register("static_pad_has_no_footprint_backreference", suite="static")
def test_pad_has_no_footprint_backreference(logger, **params) -> bool:
    """
    Источник: README KiCadTemplateCloner — обоснование геометрического
    маппинга ("у пада нет обратной ссылки на футпринт"). Проверяем: у Pad
    из board.get_pads() (плоский список ВСЕХ пад платы) действительно нет
    обратной ссылки — но test_footprint_definition_items_contains_pads
    ниже показывает путь в обход этого ограничения.
    """
    from kipy.board_types import Pad
    p = Pad()
    attrs = [a for a in dir(p) if not a.startswith("_")]
    has_backref = any(name in attrs for name in
                       ("footprint", "parent", "reference", "footprint_reference", "owner"))

    ok = not has_backref
    logger.info(f"атрибуты Pad: {attrs}")
    if ok:
        logger.info("Обоснование геометрического маппинга технически верно ДЛЯ board.get_pads(), "
                    "но есть путь в обход (см. static_footprint_definition_items_contains_pads)")
    return ok


@register("static_footprint_definition_items_contains_pads", suite="static")
def test_footprint_definition_items_contains_pads(logger, **params) -> bool:
    """
    Источник: ipc_tests/component_utils.py: get_pads() — обходит
    board.get_pads() полностью, читая footprint.definition.items,
    отфильтрованный по isinstance(item, Pad). Пад уже привязан к known
    футпринту по конструкции запроса — геометрический маппинг не нужен.
    """
    from kipy.board_types import FootprintInstance
    fp = FootprintInstance()
    has_definition = hasattr(fp, "definition")
    has_items = has_definition and hasattr(fp.definition, "items")

    logger.info(f"hasattr(fp,'definition')={has_definition}, hasattr(fp.definition,'items')={has_items}")
    if has_items:
        logger.info("Пад привязан к known футпринту по конструкции запроса, "
                    "не ищется постфактум геометрическим маппингом по координатам")
    return has_items


@register("static_run_action_is_documented_unstable", suite="static")
def test_run_action_is_documented_unstable(logger, **params) -> bool:
    """
    Проверяем: сама библиотека kipy маркирует run_action как нестабильный
    API прямо в docstring — не наше предположение, а официальное
    предупреждение разработчиков KiCad.
    """
    from kipy import KiCad
    doc = inspect.getdoc(KiCad.run_action) or ""
    warns_unstable = "unstable" in doc.lower()

    logger.info(doc.replace("\n", " ")[:160] + "...")
    if warns_unstable:
        logger.info("Флип через run_action('pcbnew.InteractiveEdit.flip') — единственный способ "
                    "реально отзеркалить пады/шёлкографию, но имена action не гарантированы стабильными")
    return warns_unstable


@register("static_refill_zones_default_is_blocking", suite="static")
def test_refill_zones_default_is_blocking(logger, **params) -> bool:
    """
    Проверяем реальный default в установленной библиотеке: block=True.
    Если так — исходный busy-баг был не "забыли указать block=True", а
    кто-то ЯВНО передал block=False в раннем прототипе.
    """
    from kipy.board import Board
    sig = inspect.signature(Board.refill_zones)
    block_param = sig.parameters.get("block")
    default_is_true = block_param is not None and block_param.default is True

    logger.info(str(sig))
    if default_is_true:
        logger.info("Значит исходный busy-баг был осознанным (ошибочным) выбором в раннем "
                    "прототипе, не default-поведением библиотеки")
    return default_is_true


@register("static_net_code_deprecated_but_present", suite="static")
def test_net_code_deprecated_but_present(logger, **params) -> bool:
    """
    Проверяем, что Net.code несёт явную deprecation-документацию в самой
    библиотеке, а не только в наших комментариях к коду.
    """
    from kipy.board_types import Net
    code_prop = Net.code
    doc = (code_prop.__doc__ or "") if hasattr(code_prop, "__doc__") else ""
    fget_doc = ""
    if hasattr(code_prop, "fget") and code_prop.fget is not None:
        fget_doc = inspect.getdoc(code_prop.fget) or ""

    combined = (doc + " " + fget_doc).lower()
    looks_deprecated = "deprecat" in combined

    logger.info((fget_doc or doc).replace("\n", " ")[:120])
    return looks_deprecated
