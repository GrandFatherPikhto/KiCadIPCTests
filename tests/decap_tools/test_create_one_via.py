"""
test_create_one_via.py — минимальный диагностический тест create_items()/
remove_items_by_id() для виа. Отдельный от update_items() код-путь.

Ставит одну виа на заданную цепь рядом с ЦЕНТРОМ указанного компонента
(не от его площадки — для мелких футпринтов виа может оказаться прямо
под площадкой самого компонента, это ожидаемо для этого теста).

Id созданной виа сохраняется в .last_test_via.json рядом с этим файлом —
для удаления не нужно копировать uuid руками, remove: true без
remove_uuid сам его подхватит.

ОПАСНЫЙ: создаёт/удаляет реальный объект на плате.
"""
import json
from pathlib import Path

from runner.registry import register
from runner.step_helper import call_step
from core_api.geometry import MM, vec_mm

STATE_FILE = Path(__file__).parent / ".last_test_via.json"


@register("decap_create_one_via", suite="decap_tools", dangerous=True, needs_kicad=True)
def run_test(logger, kicad, board, ref: str = None, offset_mm: float = 1.2,
             net: str = "GND", drill_mm: float = 0.3, diameter_mm: float = 0.6,
             remove: bool = False, remove_uuid: str = None, **params) -> bool:
    logger.info(f"ПАРАМЕТРЫ: {params}")
    logger.info(f"offset_mm = {offset_mm}")
    from core_api import footprints, nets, vias

    if remove:
        target_uuid = remove_uuid
        if not target_uuid:
            if not STATE_FILE.exists():
                logger.error(f"Нет сохранённого id в {STATE_FILE} — передайте remove_uuid явно")
                return False
            target_uuid = json.loads(STATE_FILE.read_text(encoding="utf-8"))["id"]
            logger.info(f"Беру id из {STATE_FILE.name}: {target_uuid}")

        commit, ok = call_step(logger, "begin_commit()", board.begin_commit)
        if not ok or commit is None:
            return False
        try:
            _, ok = call_step(logger, "remove_by_id([...])", vias.remove_by_id, board, target_uuid)
            if not ok:
                call_step(logger, "drop_commit", board.drop_commit, commit)
                return False
            _, ok = call_step(logger, "push_commit", board.push_commit, commit,
                              "decap_create_one_via: remove")
            if ok:
                logger.info(f"Виа {target_uuid} удалена")
                if STATE_FILE.exists():
                    saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    if saved.get("id") == target_uuid:
                        STATE_FILE.unlink()
            return ok
        except Exception:
            call_step(logger, "drop_commit (после исключения)", board.drop_commit, commit)
            raise

    if not ref:
        logger.error("Нужен параметр ref (refdes компонента) или remove: true")
        return False

    target = footprints.get_by_ref(board, ref)
    if target is None:
        logger.error(f"{ref} не найден на плате")
        return False

    target_net = nets.get_by_name(board, net)
    if target_net is None:
        logger.error(f"Цепь {net!r} не найдена на плате")
        return False

    x, y = footprints.get_position_mm(target)
    via_x = x + offset_mm
    logger.info(f"{ref} на ({x:.3f}, {y:.3f}) мм, виа будет на ({via_x:.3f}, {y:.3f}) мм, net={net}")

    via = vias.make((via_x, y), target_net, drill_mm=drill_mm, diameter_mm=diameter_mm)

    commit, ok = call_step(logger, "begin_commit()", board.begin_commit)
    if not ok or commit is None:
        return False
    try:
        created, ok = call_step(logger, "create_items([via])", board.create_items, [via])
        if not ok:
            call_step(logger, "drop_commit (после ошибки)", board.drop_commit, commit)
            return False
        _, ok = call_step(logger, "push_commit", board.push_commit, commit,
                          f"decap_create_one_via: рядом с {ref}")
        if not ok:
            return False

        created_id = created[0].id.value if created else None
        logger.info(f"Готово. Виа создана, id={created_id}")
        if created_id:
            STATE_FILE.write_text(json.dumps({"id": created_id, "ref": ref}), encoding="utf-8")
            logger.info(f"id сохранён в {STATE_FILE.name} — для удаления: remove: true")
        return True
    except Exception:
        call_step(logger, "drop_commit (после исключения)", board.drop_commit, commit)
        raise
