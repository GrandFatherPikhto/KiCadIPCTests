"""
test_footprint_rotation_linkage.py — прямая проверка бага #21655 (KiCad
GitLab: поворот футпринта через IPC тихо рвёт связь symbol<->footprint) на
конкретном, безопасном для мутации компоненте.

IPC в KiCad 9/10 не поддерживает редактор схем — проверить связь
symbol<->footprint напрямую нельзя. Тест проверяет ближайший ДОСТУПНЫЙ
через IPC косвенный признак целостности: что reference/value/имя
футпринта и net на каждом паде остаются идентичными до и после поворота.
Полная проверка (истинная связь с symbol) требует ручной проверки в самом
KiCad: Update PCB from Schematic и наблюдение за предупреждениями.

УЛУЧШЕНИЕ при переносе (2026-07-14): раньше тест оставлял компонент
повёрнутым насовсем, требуя отдельный ручной запуск с --revert. Теперь
auto_revert=True по умолчанию — тест сам возвращает угол назад в конце,
плата не остаётся в изменённом состоянии просто по факту прогона теста.
Если хотите оставить компонент повёрнутым для ручной проверки в
Schematic Editor — передайте auto_revert: false в конфиге.

ОПАСНЫЙ: мутирует реальный угол реального компонента (хоть и возвращает
обратно по умолчанию). Требует параметр ref — НЕ боевой компонент.
"""
from kipy.geometry import Angle

from runner.registry import register
from runner.step_helper import call_step


def _snapshot(fp):
    from core_api import footprints, pads
    pads_list = pads.get_all(fp)
    pad_snapshot = sorted((p.number, pads.get_net_name(p)) for p in pads_list)
    return {
        "ref": footprints.get_reference(fp),
        "value": footprints.get_value(fp),
        "footprint_name": footprints.get_footprint_name(fp),
        "pad_count": len(pads_list),
        "pads": pad_snapshot,
    }


@register("mutating_footprint_rotation_linkage", suite="mutating", dangerous=True, needs_kicad=True)
def run_test(logger, kicad, board, ref: str = None, angle_deg: float = 45.0,
             auto_revert: bool = True, **params) -> bool:
    from core_api import footprints

    if not ref:
        logger.error("Нужен параметр ref (refdes тестового компонента, НЕ боевого)")
        return False

    target = footprints.get_by_ref(board, ref)
    if target is None:
        logger.error(f"{ref} не найден на плате")
        return False

    def _rotate_by(delta_deg: float):
        fp = footprints.get_by_ref(board, ref)
        before = _snapshot(fp)
        old_angle_deg = fp.orientation.degrees
        new_angle = Angle.from_degrees(old_angle_deg + delta_deg)

        commit, ok = call_step(logger, f"begin_commit (поворот {delta_deg:+.1f}°)", board.begin_commit)
        if not ok or commit is None:
            return None, None, False

        fp.orientation = new_angle
        _, ok = call_step(logger, "update_items([target])", board.update_items, [fp])
        if not ok:
            call_step(logger, "drop_commit (откат после ошибки)", board.drop_commit, commit)
            return None, None, False
        call_step(logger, "push_commit", board.push_commit, commit,
                  f"test_footprint_rotation_linkage: {ref} {delta_deg:+.1f}°")

        # ВАЖНО: локальный объект после операции может быть устаревшим —
        # перечитываем заново (см. test_flip_then_update_items).
        fp_after = footprints.get_by_ref(board, ref)
        if fp_after is None:
            return before, None, False
        after = _snapshot(fp_after)
        logger.info(f"Угол: {old_angle_deg:.1f}° -> {fp_after.orientation.degrees:.1f}°")
        return before, after, True

    logger.info(f"Поворачиваю {ref} на {angle_deg:+.1f}°")
    before, after, ok = _rotate_by(angle_deg)
    if not ok:
        return False

    identical_except_expected = (
        before["ref"] == after["ref"]
        and before["value"] == after["value"]
        and before["footprint_name"] == after["footprint_name"]
        and before["pad_count"] == after["pad_count"]
        and before["pads"] == after["pads"]
    )

    if identical_except_expected:
        logger.info("Всё, что видно через IPC (имя футпринта, число пад, net на каждом паде), "
                    "идентично до/после поворота. Не доказывает отсутствие #21655 на стороне схемы, "
                    "но на PCB-стороне связность (net на падах) не пострадала.")
    else:
        logger.error(f"РАСХОЖДЕНИЕ до/после поворота у {ref}! ДО={before}, ПОСЛЕ={after}. "
                     "Похоже на подтверждение #21655 — не применяйте эту операцию на боевой плате.")

    if auto_revert:
        logger.info(f"auto_revert=True — возвращаю угол обратно (-{angle_deg:.1f}°)")
        _rotate_by(-angle_deg)
    else:
        logger.warning(f"auto_revert=False — {ref} ОСТАЁТСЯ повёрнутым на {angle_deg:+.1f}° для "
                       f"ручной проверки в Schematic Editor (Update PCB from Schematic)")

    return identical_except_expected
