#!/usr/bin/env python3
"""
Полный тест всех основных классов и методов IPC API KiCad 10.
Проверяет доступность и базовую работоспособность:
- Board: получение всех элементов (footprints, nets, tracks, vias, zones, pads, text, shapes, dimensions, groups)
- Поисковые методы: get_items, get_items_by_id, get_items_by_net, get_items_by_netclass, get_connected_items
- Проект и штамп
- Слои и активный слой
- Выделение (selection)
- Транзакции (commit/rollback)
- Сохранение (без изменений)

ИСПРАВЛЕНО (2026-07-12), два реальных бага:

1. UnboundLocalError: `footprints = list(board.get_footprints())` внутри try
   — если исключение вылетало ДО завершения присваивания, имя `footprints`
   вообще не создавалось в локальной области видимости, и следующий
   `if footprints:` падал `UnboundLocalError`, маскируя настоящую причину
   (в логе это выглядело как "тест упал с исключением", хотя реальная
   ошибка — в get_footprints выше). Теперь footprints/nets/pads/zones
   инициализируются пустыми списками ДО вызовов.

2. `board.get_items(types=0xFFFFFFFF)` — неверное использование API.
   Судя по исходнику kipy.board.Board.get_items(), параметр types — это
   ЗНАЧЕНИЕ(-я) enum KiCadObjectType (KOT_PCB_FOOTPRINT, KOT_PCB_PAD, ...),
   а не битовая маска "все типы". 0xFFFFFFFF (4294967295) не влезает в
   диапазон protobuf-enum и либо не биндится (в одной версии окружения —
   "missing 1 required positional argument", в другой — "Value out of
   range: 4294967295"), а не запрашивает "всё". Чтобы получить всё —
   надо явно перечислить нужные типы.

Также все повторяющиеся try/except-блоки заменены на core.call_ipc(),
которая добавляет тайминг каждого вызова — это ключевое для диагностики
"KiCad is busy": видно, падает вызов мгновенно или висит до таймаута.
"""
import tempfile

from ipc_tests.core import get_kicad_board, call_ipc
from kipy.proto.common.types import KiCadObjectType

# Типы объектов платы, которые запрашиваем через get_items() как
# "практически всё, что нас интересует на PCB". Полный список типов
# смотрите в kipy.proto.common.types.KiCadObjectType — здесь взяты
# основные PCB-типы (KOT_PCB_*), без схемных (KOT_SCH_*), т.к. IPC в
# KiCad 9/10 не поддерживает схемный редактор.
ALL_PCB_TYPES = [
    KiCadObjectType.KOT_PCB_FOOTPRINT,
    KiCadObjectType.KOT_PCB_PAD,
    KiCadObjectType.KOT_PCB_SHAPE,
    KiCadObjectType.KOT_PCB_TEXT,
    KiCadObjectType.KOT_PCB_TEXTBOX,
    KiCadObjectType.KOT_PCB_TRACE,
    KiCadObjectType.KOT_PCB_VIA,
    KiCadObjectType.KOT_PCB_ARC,
    KiCadObjectType.KOT_PCB_ZONE,
    KiCadObjectType.KOT_PCB_GROUP,
    KiCadObjectType.KOT_PCB_DIMENSION,
]


def run_test(logger):
    logger.info("=== ПОЛНЫЙ ТЕСТ ВСЕХ КЛАССОВ И МЕТОДОВ IPC ===")
    board = get_kicad_board(logger=logger)
    if board is None:
        return False

    success = True

    # 1. Проверка получения базовых списков
    logger.info("1. Получение списков объектов...")
    footprints, ok = call_ipc(logger, "get_footprints", lambda: list(board.get_footprints()))
    footprints = footprints or []
    success &= ok

    nets, ok = call_ipc(logger, "get_nets", lambda: list(board.get_nets()))
    nets = nets or []
    success &= ok

    tracks, ok = call_ipc(logger, "get_tracks", lambda: list(board.get_tracks()))
    success &= ok

    vias, ok = call_ipc(logger, "get_vias", lambda: list(board.get_vias()))
    success &= ok

    zones, ok = call_ipc(logger, "get_zones", lambda: list(board.get_zones()))
    zones = zones or []
    success &= ok

    pads, ok = call_ipc(logger, "get_pads", lambda: list(board.get_pads()))
    pads = pads or []
    success &= ok

    _, ok = call_ipc(logger, "get_text", lambda: list(board.get_text()))
    success &= ok

    _, ok = call_ipc(logger, "get_shapes", lambda: list(board.get_shapes()))
    success &= ok

    _, ok = call_ipc(logger, "get_dimensions", lambda: list(board.get_dimensions()))
    success &= ok

    _, ok = call_ipc(logger, "get_groups", lambda: list(board.get_groups()))
    success &= ok

    # 2. Поисковые методы
    logger.info("2. Проверка поисковых методов...")
    items, ok = call_ipc(logger, "get_items(ALL_PCB_TYPES)", board.get_items, ALL_PCB_TYPES)
    success &= ok

    if footprints:
        first_fp = footprints[0]
        if hasattr(first_fp, 'id'):
            _, ok = call_ipc(logger, "get_items_by_id", board.get_items_by_id, [first_fp.id])
            success &= ok

    if nets:
        _, ok = call_ipc(logger, "get_items_by_net", board.get_items_by_net, nets[0])
        success &= ok

    if nets:
        net = nets[0]
        if hasattr(net, 'netclass') and net.netclass:
            _, ok = call_ipc(logger, "get_items_by_netclass", board.get_items_by_netclass, net.netclass)
            success &= ok

    if pads:
        _, ok = call_ipc(logger, "get_connected_items", board.get_connected_items, pads[0])
        success &= ok

    # 3. Проект и штамп
    logger.info("3. Проект и штамп...")
    project, ok = call_ipc(logger, "get_project", board.get_project)
    success &= ok
    if project:
        logger.info(f"   Проект: {getattr(project, 'path', '?')}")

    title_block, ok = call_ipc(logger, "get_title_block_info", board.get_title_block_info)
    success &= ok
    if title_block:
        logger.info(f"   Title: {getattr(title_block, 'title', '?')}")

    # 4. Слои
    logger.info("4. Слои...")
    copper_layers, ok = call_ipc(logger, "get_copper_layer_count", board.get_copper_layer_count)
    success &= ok
    if copper_layers is not None:
        logger.info(f"   Медных слоёв: {copper_layers}")

    enabled_layers, ok = call_ipc(logger, "get_enabled_layers", board.get_enabled_layers)
    success &= ok

    active_layer, ok = call_ipc(logger, "get_active_layer", board.get_active_layer)
    success &= ok
    if active_layer is not None:
        logger.info(f"   Активный слой: {active_layer}")

    # 5. Выделение (selection)
    logger.info("5. Выделение...")
    selection, ok = call_ipc(logger, "get_selection", board.get_selection)
    success &= ok

    if footprints:
        _, ok = call_ipc(logger, "add_to_selection", board.add_to_selection, [footprints[0]])
        success &= ok
        new_sel, ok = call_ipc(logger, "get_selection (после добавления)", board.get_selection)
        success &= ok
        _, ok = call_ipc(logger, "remove_from_selection", board.remove_from_selection, [footprints[0]])
        success &= ok
        _, ok = call_ipc(logger, "clear_selection", board.clear_selection)
        success &= ok

    # 6. Транзакции (с правильным завершением)
    logger.info("6. Транзакции...")
    commit, ok = call_ipc(logger, "begin_commit", board.begin_commit)
    success &= ok
    if commit is not None:
        _, ok = call_ipc(logger, "drop_commit", board.drop_commit, commit)
        success &= ok

    # 7. Сохранение (только если нет активной транзакции)
    logger.info("7. Сохранение...")
    _, ok = call_ipc(logger, "save", board.save)
    success &= ok

    # 8. Заливка зон (если есть зоны)
    if zones:
        logger.info("8. Заливка зон...")
        # ВАЖНО: раньше здесь был block=False без ожидания завершения.
        # Подозрение (не доказано, но по времени сходится): именно
        # незавершённый асинхронный refill_zones мог оставить плату в
        # состоянии "занято" для всех операций с содержимым на весь остаток
        # долгоживущей сессии KiCad. Теперь ждём завершения синхронно —
        # это медленнее, но не оставляет фоновых джобов висеть.
        _, ok = call_ipc(
            logger, "refill_zones (blocking)",
            board.refill_zones, block=True, max_poll_seconds=10
        )
        success &= ok

    logger.info("=== ПОЛНЫЙ ТЕСТ ЗАВЕРШЁН ===")
    return bool(success)
