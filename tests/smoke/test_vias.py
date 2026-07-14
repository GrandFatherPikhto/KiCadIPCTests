"""
test_vias.py — smoke-тест модуля core_api.vias.
Создаёт одну тестовую виа рядом с компонентом ref на цепи net, сразу же
удаляет обратно — плата остаётся чистой.
"""
from runner.registry import register


@register("smoke_vias", suite="smoke", needs_kicad=True, dangerous=False)
def run_test(logger, kicad, board, ref: str = None, net: str = "GND", **params) -> bool:
    from core_api import footprints, nets, vias, board as board_api

    if not ref:
        logger.error("Нужен параметр ref (refdes компонента, рядом с которым ставим виа)")
        return False

    fp = footprints.get_by_ref(board, ref)
    if fp is None:
        logger.error(f"Компонент {ref!r} не найден")
        return False

    target_net = nets.get_by_name(board, net)
    if target_net is None:
        logger.error(f"Цепь {net!r} не найдена")
        return False

    x, y = footprints.get_position_mm(fp)
    pos_mm = (x + 2.0, y)  # небольшое смещение, чтобы не сесть точно на компонент
    via = vias.make(pos_mm, target_net, drill_mm=0.3, diameter_mm=0.6)

    created_id = None

    def create_work():
        nonlocal created_id
        created = board.create_items([via])
        if created:
            created_id = created[0].id.value

    ok_create = board_api.commit_with_retry(board, "smoke_vias: создание тестовой виа", create_work)
    if not ok_create or created_id is None:
        logger.error("Не удалось создать тестовую виа")
        return False
    logger.info(f"Тестовая виа создана: id={created_id}")

    def remove_work():
        vias.remove_by_id(board, created_id)

    ok_remove = board_api.commit_with_retry(board, "smoke_vias: удаление тестовой виа", remove_work)
    if not ok_remove:
        logger.error(f"Виа создана (id={created_id}), но НЕ удалена — на плате остался мусор, "
                     f"уберите вручную")
        return False

    logger.info("Тестовая виа удалена, плата чистая")
    return True
