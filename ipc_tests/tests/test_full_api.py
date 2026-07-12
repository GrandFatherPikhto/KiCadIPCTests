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
"""
import os
import tempfile
from ipc_tests.core import get_kicad_board

def run_test(logger):
    logger.info("=== ПОЛНЫЙ ТЕСТ ВСЕХ КЛАССОВ И МЕТОДОВ IPC ===")
    board = get_kicad_board(logger=logger)
    if board is None:
        return False

    success = True

    # 1. Проверка получения базовых списков
    logger.info("1. Получение списков объектов...")
    try:
        footprints = list(board.get_footprints())
        logger.info(f"   Footprints: {len(footprints)}")
    except Exception as e:
        logger.error(f"   Ошибка get_footprints: {e}")
        success = False

    try:
        nets = list(board.get_nets())
        logger.info(f"   Nets: {len(nets)}")
    except Exception as e:
        logger.error(f"   Ошибка get_nets: {e}")
        success = False

    try:
        tracks = list(board.get_tracks())
        logger.info(f"   Tracks: {len(tracks)}")
    except Exception as e:
        logger.error(f"   Ошибка get_tracks: {e}")
        success = False

    try:
        vias = list(board.get_vias())
        logger.info(f"   Vias: {len(vias)}")
    except Exception as e:
        logger.error(f"   Ошибка get_vias: {e}")
        success = False

    try:
        zones = list(board.get_zones())
        logger.info(f"   Zones: {len(zones)}")
    except Exception as e:
        logger.error(f"   Ошибка get_zones: {e}")
        success = False

    try:
        pads = list(board.get_pads())
        logger.info(f"   Pads: {len(pads)}")
    except Exception as e:
        logger.error(f"   Ошибка get_pads: {e}")
        success = False

    try:
        texts = list(board.get_text())
        logger.info(f"   Texts: {len(texts)}")
    except Exception as e:
        logger.error(f"   Ошибка get_text: {e}")
        success = False

    try:
        shapes = list(board.get_shapes())
        logger.info(f"   Shapes: {len(shapes)}")
    except Exception as e:
        logger.error(f"   Ошибка get_shapes: {e}")
        success = False

    try:
        dimensions = list(board.get_dimensions())
        logger.info(f"   Dimensions: {len(dimensions)}")
    except Exception as e:
        logger.error(f"   Ошибка get_dimensions: {e}")
        success = False

    try:
        groups = list(board.get_groups())
        logger.info(f"   Groups: {len(groups)}")
    except Exception as e:
        logger.error(f"   Ошибка get_groups: {e}")
        success = False

    # 2. Поисковые методы
    logger.info("2. Проверка поисковых методов...")
    try:
        # get_items – используем маску 0xFFFFFFFF (все типы)
        items = board.get_items(types=0xFFFFFFFF)
        # items = board.get_items()
        logger.info(f"   get_items(all): {len(items)}")
    except Exception as e:
        logger.error(f"   Ошибка get_items: {e}")
        success = False

    # get_items_by_id – возьмём первый попавшийся ID
    if footprints:
        first_fp = footprints[0]
        if hasattr(first_fp, 'id'):
            try:
                items_by_id = board.get_items_by_id([first_fp.id])
                logger.info(f"   get_items_by_id: найдено {len(items_by_id)}")
            except Exception as e:
                logger.error(f"   Ошибка get_items_by_id: {e}")
                success = False

    # get_items_by_net – если есть цепи
    if nets:
        try:
            items_by_net = board.get_items_by_net(nets[0])
            logger.info(f"   get_items_by_net: найдено {len(items_by_net)}")
        except Exception as e:
            logger.error(f"   Ошибка get_items_by_net: {e}")
            success = False

    # get_items_by_netclass – если у цепи есть netclass
    if nets:
        net = nets[0]
        if hasattr(net, 'netclass') and net.netclass:
            try:
                items_by_nc = board.get_items_by_netclass(net.netclass)
                logger.info(f"   get_items_by_netclass: найдено {len(items_by_nc)}")
            except Exception as e:
                logger.error(f"   Ошибка get_items_by_netclass: {e}")
                success = False

    # get_connected_items – возьмём первую площадку
    if pads:
        first_pad = pads[0]
        try:
            connected = board.get_connected_items(first_pad)
            logger.info(f"   get_connected_items: найдено {len(connected)}")
        except Exception as e:
            logger.error(f"   Ошибка get_connected_items: {e}")
            success = False

    # 3. Проект и штамп
    logger.info("3. Проект и штамп...")
    try:
        project = board.get_project()
        if project:
            logger.info(f"   Проект: {project.path if hasattr(project, 'path') else '?'}")
        else:
            logger.warning("   get_project вернул None")
    except Exception as e:
        logger.error(f"   Ошибка get_project: {e}")
        success = False

    try:
        title_block = board.get_title_block_info()
        if title_block:
            logger.info(f"   Title: {title_block.title if hasattr(title_block, 'title') else '?'}")
        else:
            logger.warning("   get_title_block_info вернул None")
    except Exception as e:
        logger.error(f"   Ошибка get_title_block_info: {e}")
        success = False

    # 4. Слои
    logger.info("4. Слои...")
    try:
        copper_layers = board.get_copper_layer_count()
        logger.info(f"   Медных слоёв: {copper_layers}")
    except Exception as e:
        logger.error(f"   Ошибка get_copper_layer_count: {e}")
        success = False

    try:
        enabled_layers = board.get_enabled_layers()
        logger.info(f"   Включённых слоёв: {len(enabled_layers)}")
    except Exception as e:
        logger.error(f"   Ошибка get_enabled_layers: {e}")
        success = False

    try:
        active_layer = board.get_active_layer()
        logger.info(f"   Активный слой: {active_layer}")
    except Exception as e:
        logger.error(f"   Ошибка get_active_layer: {e}")
        success = False

    # 5. Выделение (selection)
    logger.info("5. Выделение...")
    try:
        selection = board.get_selection()
        logger.info(f"   Текущее выделение: {len(selection)} объектов")
    except Exception as e:
        logger.error(f"   Ошибка get_selection: {e}")
        success = False

    if footprints:
        try:
            board.add_to_selection([footprints[0]])
            new_sel = board.get_selection()
            logger.info(f"   После добавления: {len(new_sel)} объектов")
            board.remove_from_selection([footprints[0]])
            board.clear_selection()
            logger.info("   Очистка выделения выполнена")
        except Exception as e:
            logger.error(f"   Ошибка при работе с выделением: {e}")
            success = False

    # 6. Транзакции (с правильным завершением)
    logger.info("6. Транзакции...")
    commit = None
    try:
        commit = board.begin_commit()
        logger.info("   Транзакция начата")
        # Здесь можно было бы что-то изменить, но мы просто откатим
        board.drop_commit(commit)
        commit = None  # помечаем, что транзакция закрыта
        logger.info("   Транзакция отменена (без изменений)")
    except Exception as e:
        logger.error(f"   Ошибка при работе с транзакцией: {e}")
        success = False
        # Попытаемся откатить, если транзакция висит
        if commit is not None:
            try:
                board.drop_commit(commit)
                logger.info("   Транзакция принудительно откачена")
            except:
                pass

    # 7. Сохранение (только если нет активной транзакции)
    logger.info("7. Сохранение...")
    try:
        board.save()
        logger.info("   board.save() вызван успешно")
    except Exception as e:
        logger.error(f"   Ошибка save: {e}")
        success = False

    # 8. Экспорт (проверка наличия методов)
    logger.info("8. Проверка методов экспорта...")
    # Попробуем вызвать export_gerber, если он есть
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            if hasattr(board, 'export_gerber'):
                result = board.export_gerber(tmpdir, board.get_layer_id('F.Cu'))
                logger.info(f"   export_gerber: {'успешно' if result and result.success else 'не удался'}")
            else:
                logger.info("   Метод export_gerber отсутствует (пропускаем)")
    except Exception as e:
        logger.error(f"   Ошибка при экспорте: {e}")
        success = False

    # 9. Заливка зон (если есть зоны)
    if zones:
        logger.info("9. Заливка зон...")
        try:
            board.refill_zones(block=False, max_poll_seconds=1)
            logger.info("   refill_zones вызван (асинхронно)")
        except Exception as e:
            logger.error(f"   Ошибка refill_zones: {e}")
            success = False

    logger.info("=== ПОЛНЫЙ ТЕСТ ЗАВЕРШЁН ===")
    return success