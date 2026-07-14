"""
test_flip_one_cap.py — минимальный диагностический тест "настоящего" флипа.

Пересекается по теме с mutating_flip_then_update_items (та проверяет два
варианта работы с "стухшим" объектом после флипа), но этот — проще: один
флип, показ состояния до/после. Полезен как быстрая самостоятельная
проверка "флип вообще работает на этой версии KiCad", без более сложного
сценария A/B.

Настоящий переворот — GUI-action pcbnew.InteractiveEdit.flip (хоткей F),
работает через ТЕКУЩЕЕ ВЫДЕЛЕНИЕ. Простое footprint.layer = BL_B_Cu НЕ
зеркалирует площадки/шёлкографию.

ОПАСНЫЙ: реально переворачивает компонент на другую сторону, без
автоматического возврата — используйте dangerous-гейт и, при
необходимости, отдельный повторный вызов этого же теста для возврата
(флип — операция-тумблер, второй вызов возвращает как было).
"""
from kipy.board_types import BoardLayer

from runner.registry import register
from runner.step_helper import call_step


def _describe(fp):
    from core_api import footprints
    layer_name = "F.Cu" if fp.layer == BoardLayer.BL_F_Cu else "B.Cu" if fp.layer == BoardLayer.BL_B_Cu else str(fp.layer)
    x, y = footprints.get_position_mm(fp)
    return f"layer={layer_name}, pos=({x:.3f}, {y:.3f}) мм, angle={fp.orientation.degrees:.1f}°"


@register("decap_flip_one_cap", suite="decap_tools", dangerous=True, needs_kicad=True)
def run_test(logger, kicad, board, ref: str = None, **params) -> bool:
    from core_api import footprints

    if not ref:
        logger.error("Нужен параметр ref (refdes компонента, НЕ боевого)")
        return False

    target = footprints.get_by_ref(board, ref)
    if target is None:
        logger.error(f"{ref} не найден на плате")
        return False

    logger.info(f"До флипа: {_describe(target)}")

    footprints.flip_selected(kicad, board, [target])

    # Перечитываем заново -- старый объект target не обновится сам после
    # GUI-действия, выполненного мимо update_items().
    target_after = footprints.get_by_ref(board, ref)
    if target_after is None:
        logger.error(f"{ref} не найден после флипа?!")
        return False

    logger.info(f"После флипа: {_describe(target_after)}")

    if target_after.layer == BoardLayer.BL_B_Cu:
        logger.info("Сработало — слой реально сменился на B.Cu")
        return True

    logger.warning("Слой НЕ сменился на B.Cu (был, видимо, уже B.Cu до теста, "
                   "либо флип не сработал так, как ожидалось)")
    return target_after.layer != target.layer  # хоть какое-то изменение — уже сигнал, что подействовало
