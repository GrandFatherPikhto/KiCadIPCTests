#!/usr/bin/env python3
"""
test_kipy_contract.py — статические контракт-тесты против установленной
библиотеки `kicad-python` (kipy), БЕЗ подключения к живому KiCad.

Зачем этот файл существует отдельно от ipc_tests/tests/:
Все тесты в ipc_tests/tests/ требуют запущенного KiCad с открытой платой —
это тесты ПОВЕДЕНИЯ живого IPC-сервера (busy-состояния, реальные net'ы на
плате и т.п.), их нельзя выполнить без Windows-машины с KiCad.

Но часть находок в KiCadTemplateCloner/KiCadDecapPlacer — это не поведение
сервера, а факты о самой Python-библиотеке kipy: существует ли атрибут,
что возвращает getter (копию или ссылку), какой тип ожидает setter. Эти
факты можно проверить ОДНИМ импортом kipy, без KiCad вообще — и именно
так были найдены баги ниже. Каждый тест — это конкретная строка кода из
одного из репозиториев, проверенная напрямую.

Запуск:
    python run_static_tests.py
"""
import inspect
import math


def _report(label, ok, detail=""):
    status = "[OK]  " if ok else "[FAIL]"
    print(f"{status} {label}" + (f" — {detail}" if detail else ""))
    return ok


def test_via_drill_attribute_name():
    """
    Источник: KiCadTemplateCloner/template_cloner/extractor.py:99
        drill = via.drill.diameter if hasattr(via, 'drill') and ... else 0.3
    и applier.py:20
        via.drill.diameter = drill_nm

    Проверяем: существует ли у Via атрибут `.drill` (вложенный, с полем
    .diameter), или только плоский `.drill_diameter`, как использует
    KiCadDecapPlacer (adapter.py: via.drill_diameter = ...).
    """
    from kipy.board_types import Via
    v = Via()
    has_nested_drill = hasattr(v, "drill")
    has_flat_drill = hasattr(v, "drill_diameter")

    ok = _report(
        "Via: только drill_diameter (плоский), НЕТ .drill (вложенного)",
        has_flat_drill and not has_nested_drill,
        f"hasattr(v,'drill')={has_nested_drill}, hasattr(v,'drill_diameter')={has_flat_drill}"
    )
    if has_nested_drill and not has_flat_drill:
        print("      => extractor.py/applier.py используют ВЕРНОЕ имя, DecapPlacer — НЕТ (проверьте руками ещё раз)")
    elif has_flat_drill and not has_nested_drill:
        print("      => КОНФИРМ: extractor.py/applier.py обращаются к несуществующему .drill.")
        print("         extractor.py: hasattr(via,'drill') всегда False => drill всегда падает на default 0.3.")
        print("         applier.py: 'via.drill.diameter = drill_nm' кидает AttributeError на первом же via.")
    return ok


def test_footprint_orientation_property_name():
    """
    Источник: KiCadTemplateCloner/template_cloner/extractor.py:80
        angle = fp.orientation.as_degrees() if hasattr(fp.orientation, 'as_degrees') else 0.0

    Проверяем: у Angle есть свойство `.degrees`, но НЕТ метода `.as_degrees()`.
    """
    from kipy.geometry import Angle
    a = Angle.from_degrees(45.0)
    has_method = hasattr(a, "as_degrees")
    has_property = hasattr(a, "degrees") and a.degrees == 45.0

    ok = _report(
        "Angle: есть .degrees (свойство), НЕТ .as_degrees() (метода)",
        has_property and not has_method,
        f"hasattr(a,'as_degrees')={has_method}, a.degrees={a.degrees}"
    )
    if not has_method:
        print("      => КОНФИРМ: extractor.py's hasattr(fp.orientation,'as_degrees') всегда False.")
        print("         Значит angle в КАЖДОМ извлечённом компоненте = 0.0, реальный поворот теряется молча.")
    return ok


def test_footprint_get_layer_method():
    """
    Источник: KiCadTemplateCloner/template_cloner/extractor.py:78
        layer_obj = fp.get_layer() if hasattr(fp, 'get_layer') else None

    Проверяем: у FootprintInstance слой — это свойство `.layer`,
    метода `.get_layer()` не существует.
    """
    from kipy.board_types import FootprintInstance
    fp = FootprintInstance()
    has_method = hasattr(fp, "get_layer")
    has_property = hasattr(fp, "layer")

    ok = _report(
        "FootprintInstance: есть .layer (свойство), НЕТ .get_layer() (метода)",
        has_property and not has_method,
        f"hasattr(fp,'get_layer')={has_method}"
    )
    if not has_method:
        print("      => КОНФИРМ: extractor.py's hasattr(fp,'get_layer') всегда False.")
        print("         Значит layer в КАЖДОМ извлечённом компоненте = 'F.Cu' (хардкод), сторона платы теряется.")
    return ok


def test_getter_returns_copy_not_reference():
    """
    Источник: KiCadTemplateCloner/template_cloner/applier.py:17-19
        via.position.x = x_nm
        via.position.y = y_nm
    и applier.py:73-74 (apply_template):
        fp.position.x = int(new_x * 1_000_000)
        fp.position.y = int(new_y * 1_000_000)

    Это САМАЯ важная находка: getter'ы вроде .position у kipy-объектов
    оборачивают proto через CopyFrom() — т.е. возвращают НЕЗАВИСИМУЮ КОПИЮ,
    а не живую ссылку на внутренние данные объекта. Значит присваивание
    атрибуту ПОЛУЧЕННОЙ копии (.position.x = ...) — операция в пустоту:
    она меняет копию, которая тут же выбрасывается, и НИКАК не влияет на
    сам fp/via. Единственный рабочий путь — переприсвоить весь объект
    целиком через setter: fp.position = Vector2.from_xy(...).
    Это то, что реально делает KiCadDecapPlacer (executor.py: fp.position = cmd.position).
    """
    from kipy.board_types import FootprintInstance
    from kipy.geometry import Vector2

    fp = FootprintInstance()
    fp.position = Vector2.from_xy(1_000_000, 2_000_000)  # 1.0, 2.0 мм — через setter, для базы

    before_x = fp.position.x
    fp.position.x = 99_000_000  # ТОЧНО как в applier.py — мутируем то, что вернул getter
    after_x = fp.position.x

    is_noop = (after_x == before_x) and (after_x != 99_000_000)

    ok = _report(
        "fp.position.x = ... является no-op (getter возвращает копию)",
        is_noop,
        f"было {before_x}, после присваивания .x=99000000 читаем снова: {after_x}"
    )
    if is_noop:
        print("      => КОНФИРМ: applier.py's 'fp.position.x = ...' и 'via.position.x = ...'")
        print("         не двигают компонент/via вообще никак — это тихий no-op, без исключения.")
        print("         Верно (см. DecapPlacer executor.py): fp.position = Vector2.from_xy(new_x, new_y)")
    return ok


def test_net_assignment_via_attribute_is_noop():
    """
    Источник: applier.py:23 (create_via) и :39 (create_track):
        via.net.name = net_name
        tr.net.name = net_name

    Тот же класс бага, что и с position, но для Net: via.net — это getter,
    возвращающий новый Net(...) обёрнутый вокруг КОПИИ proto. Присваивание
    .name этой копии не долетает до реального via.net.
    Верно (см. DecapPlacer create_via): via.net = net_obj (весь объект целиком).
    """
    from kipy.board_types import Via, Net

    v = Via()
    net = Net(name="GND")
    v.net = net  # правильный путь — целиком, через setter

    before_name = v.net.name
    v.net.name = "CHANGED_VIA_ATTRIBUTE_ASSIGNMENT"  # ТОЧНО как в applier.py
    after_name = v.net.name

    is_noop = (after_name == before_name) and (after_name != "CHANGED_VIA_ATTRIBUTE_ASSIGNMENT")

    ok = _report(
        "via.net.name = ... является no-op (getter возвращает копию Net)",
        is_noop,
        f"было {before_name!r}, после присваивания .name читаем снова: {after_name!r}"
    )
    if is_noop:
        print("      => КОНФИРМ: applier.py's 'via.net.name = ...' / 'tr.net.name = ...' — тихий no-op.")
        print("         Верно (см. DecapPlacer create_via): via.net = net  (объект Net целиком)")
    return ok


def test_orientation_setter_rejects_raw_float():
    """
    Источник: KiCadTemplateCloner/template_cloner/applier.py:78 (apply_template):
        fp.orientation = math.radians(comp.angle)

    Setter .orientation ожидает объект Angle, а не сырое число (радианы).
    Проверяем, что присваивание float реально падает с исключением —
    это должно останавливать apply_template на первом же компоненте.
    """
    from kipy.board_types import FootprintInstance

    fp = FootprintInstance()
    raised = False
    exc_info = ""
    try:
        fp.orientation = math.radians(45.0)  # ТОЧНО как в applier.py
    except Exception as e:
        raised = True
        exc_info = f"{type(e).__name__}: {e}"

    ok = _report(
        "fp.orientation = <сырой float> кидает исключение (а не тихо игнорируется)",
        raised,
        exc_info
    )
    if raised:
        print("      => КОНФИРМ: apply_template() падает с этим исключением на ПЕРВОМ же")
        print("         компоненте шаблона — до создания via/track и до push_commit().")
        print("         Верно (см. DecapPlacer executor.py): fp.orientation = cmd.angle, где")
        print("         cmd.angle — это kipy.geometry.Angle, а не число.")
    return ok


def test_push_commit_requires_commit_argument():
    """
    Источник: KiCadTemplateCloner/template_cloner/applier.py:92 (apply_template):
        board.push_commit()   # без аргументов, и begin_commit() нигде не вызывался

    Проверяем сигнатуру: push_commit(self, commit, message='') — commit
    обязателен и позиционный, вызов без него — TypeError.
    """
    from kipy.board import Board
    sig = inspect.signature(Board.push_commit)
    params = list(sig.parameters.values())
    # params[0] = self? Нет, inspect.signature на классе (не bound method)
    # включает self первым параметром.
    commit_param = next((p for p in params if p.name == "commit"), None)
    commit_required = commit_param is not None and commit_param.default is inspect.Parameter.empty

    ok = _report(
        "Board.push_commit(commit, message='') — commit обязателен и позиционен",
        commit_required,
        str(sig)
    )
    if commit_required:
        print("      => КОНФИРМ: applier.py's 'board.push_commit()' кидает TypeError")
        print("         (missing 1 required positional argument: 'commit'), и begin_commit()")
        print("         нигде в apply_template() не вызывается — транзакции нет вообще.")
    return ok


def test_pad_has_no_footprint_backreference():
    """
    Источник: README KiCadTemplateCloner, раздел 'Извлечение цепей
    (геометрический маппинг)': обоснование геометрического маппинга —
    'у компонентов нет прямого доступа к своим падам в некоторых версиях kipy'.

    Проверяем ОБРАТНУЮ сторону: у объекта Pad, полученного через
    board.get_pads() (плоский список ВСЕХ пэдов платы), нет обратной ссылки
    на владеющий footprint (ни .footprint, ни .parent, ни .reference) —
    так что геометрический маппинг для board.get_pads() был бы оправдан.
    Но test_pad_owner_via_definition_items ниже показывает, что этого пути
    можно избежать целиком, обходя board.get_pads().
    """
    from kipy.board_types import Pad
    p = Pad()
    attrs = [a for a in dir(p) if not a.startswith("_")]
    has_backref = any(name in attrs for name in
                       ("footprint", "parent", "reference", "footprint_reference", "owner"))

    ok = _report(
        "Pad (из board.get_pads()) НЕ имеет обратной ссылки на footprint",
        not has_backref,
        f"атрибуты Pad: {attrs}"
    )
    if not has_backref:
        print("      => Обоснование геометрического маппинга в README TemplateCloner")
        print("         технически верно ДЛЯ board.get_pads(), но есть путь в обход (см. ниже).")
    return ok


def test_footprint_definition_items_contains_pads():
    """
    Источник: KiCadIPCTests/ipc_tests/component_utils.py:get_pads() —
    footprint.definition.items, отфильтрованный по isinstance(item, Pad).

    Проверяем, что у свежесозданного FootprintInstance.definition вообще
    есть атрибут .items (структурная проверка типа; сам список пуст для
    объекта "с нуля", реальные пэды появляются только у футпринта, реально
    прочитанного с платы — это уже подтверждено логом test.log живого
    прогона: 'Пин 1: цепь '+3V3' (код 0)').
    """
    from kipy.board_types import FootprintInstance
    fp = FootprintInstance()
    has_definition = hasattr(fp, "definition")
    has_items = has_definition and hasattr(fp.definition, "items")

    ok = _report(
        "FootprintInstance.definition.items существует (путь IPCTests в обход board.get_pads())",
        has_items,
        f"hasattr(fp,'definition')={has_definition}, hasattr(fp.definition,'items')={has_items}"
    )
    if has_items:
        print("      => Это НЕ требует геометрического маппинга: pad уже привязан к")
        print("         известному footprint по конструкции запроса (мы сами вызвали его")
        print("         у fp), а не ищется постфактум по координатам.")
        print("         Подтверждено живым логом (logs/test.log, 13:32:26): реальные")
        print("         net-имена на пэдах ('+3V3', '+3V3_OSCILL') — не пустые/library-only.")
    return ok


def test_run_action_is_documented_unstable():
    """
    Источник: DecapPlacer/TemplateCloner adapter.py: flip_selected() —
        self._kicad.run_action("pcbnew.InteractiveEdit.flip")

    Проверяем: сама библиотека kipy маркирует run_action как нестабильный
    API прямо в docstring — это не наше предположение, а официальное
    предупреждение разработчиков KiCad.
    """
    from kipy import KiCad
    doc = inspect.getdoc(KiCad.run_action) or ""
    warns_unstable = "unstable" in doc.lower()

    ok = _report(
        "KiCad.run_action() документирован как нестабильный/unstable API",
        warns_unstable,
        doc.replace("\n", " ")[:160] + "..."
    )
    if warns_unstable:
        print("      => Флип через run_action('pcbnew.InteractiveEdit.flip') — это")
        print("         единственный способ реально отзеркалить пэды/шёлкографию (см.")
        print("         test_flip_one_cap.py docstring), но сама библиотека прямо предупреждает,")
        print("         что имена action НЕ гарантированы стабильными между версиями KiCad.")
    return ok


def test_refill_zones_default_is_blocking():
    """
    Источник: KiCadIPCTests CHANGES.md/README — гипотеза про
    'refill_zones(block=False, max_poll_seconds=1)' как причину постоянного
    busy-состояния платы.

    Проверяем реальный default в установленной библиотеке: block=True.
    Если это так — значит кто-то (в более раннем, ещё не патченом коде)
    ЯВНО переопределил безопасный default на block=False, а не просто
    unknowingly использовал дефолтное поведение.
    """
    from kipy.board import Board
    sig = inspect.signature(Board.refill_zones)
    block_param = sig.parameters.get("block")
    default_is_true = block_param is not None and block_param.default is True

    ok = _report(
        "Board.refill_zones(block=True, ...) — блокирующий режим ПО УМОЛЧАНИЮ в библиотеке",
        default_is_true,
        str(sig)
    )
    if default_is_true:
        print("      => Значит исходный баг был не 'забыли указать block=True', а")
        print("         КТО-ТО ЯВНО передал block=False, max_poll_seconds=1 — осознанный")
        print("         (ошибочный) выбор в раннем прототипе, не default-поведение библиотеки.")
    return ok


def test_net_code_deprecated_but_present():
    """
    Источник: net_utils.py: 'Net.code в kicad-python 0.7.1 официально
    помечен @deprecated'. Проверяем это напрямую через сам декоратор/docstring,
    а не по комментарию в коде.
    """
    from kipy.board_types import Net
    code_prop = Net.code
    doc = (code_prop.__doc__ or "") if hasattr(code_prop, "__doc__") else ""
    fget_doc = ""
    if hasattr(code_prop, "fget") and code_prop.fget is not None:
        fget_doc = inspect.getdoc(code_prop.fget) or ""

    combined = (doc + " " + fget_doc).lower()
    looks_deprecated = "deprecat" in combined

    ok = _report(
        "Net.code несёт явную deprecation-документацию в самой библиотеке",
        looks_deprecated,
        (fget_doc or doc).replace("\n", " ")[:120]
    )
    return ok


ALL_TESTS = [
    test_via_drill_attribute_name,
    test_footprint_orientation_property_name,
    test_footprint_get_layer_method,
    test_getter_returns_copy_not_reference,
    test_net_assignment_via_attribute_is_noop,
    test_orientation_setter_rejects_raw_float,
    test_push_commit_requires_commit_argument,
    test_pad_has_no_footprint_backreference,
    test_footprint_definition_items_contains_pads,
    test_run_action_is_documented_unstable,
    test_refill_zones_default_is_blocking,
    test_net_code_deprecated_but_present,
]


def run_all():
    print("=" * 78)
    print("СТАТИЧЕСКИЕ КОНТРАКТ-ТЕСТЫ kicad-python (kipy) — без живого KiCad")
    print("=" * 78)
    results = {}
    for test_fn in ALL_TESTS:
        print(f"\n--- {test_fn.__name__} ---")
        print((test_fn.__doc__ or "").strip().split("\n")[0])
        try:
            results[test_fn.__name__] = bool(test_fn())
        except Exception as e:
            print(f"[ERR]  тест упал с исключением: {type(e).__name__}: {e}")
            results[test_fn.__name__] = False

    print("\n" + "=" * 78)
    passed = sum(1 for v in results.values() if v)
    for name, ok in results.items():
        print(f"  {'[OK]  ' if ok else '[FAIL]'} {name}")
    print(f"\nПройдено: {passed}/{len(results)}")
    print("=" * 78)
    return results


if __name__ == "__main__":
    run_all()
