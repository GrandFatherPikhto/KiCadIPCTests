"""
test_move_one_cap.py — минимальный диагностический тест IPC-записи.

Изначальная цель (создание скрипта): изолировать зависание на
begin_commit() до предела — взять ОДИН компонент, сдвинуть на заданное
расстояние по X, закоммитить. Если и это виснет — проблема не в размере
батча/коммита, а в чём-то более фундаментальном (зависшая транзакция от
предыдущего запуска, сломанное состояние сессии KiCad) — тогда нужен
полный перезапуск KiCad.

ОПАСНЫЙ: мутирует реальную позицию реального компонента. revert: true
возвращает на то же расстояние в обратную сторону — не "восстановление
из снимка", а просто симметричный обратный сдвиг, как и в оригинале.
"""
from runner.registry import register
from runner.step_helper import call_step
from core_api.geometry import MM, vec_mm


@register("decap_move_one_cap", suite="decap_tools", dangerous=True, needs_kicad=True)
def run_test(logger, kicad, board, ref: str = None, delta_mm: float = 1.0,
             revert: bool = False, **params) -> bool:
    from core_api import footprints

    if not ref:
        logger.error("Нужен параметр ref (refdes компонента, НЕ боевого)")
        return False

    delta = -delta_mm if revert else delta_mm

    target = footprints.get_by_ref(board, ref)
    if target is None:
        logger.error(f"{ref} не найден на плате")
        return False

    old_x, old_y = footprints.get_position_mm(target)
    new_x = old_x + delta
    logger.info(f"{ref}: ({old_x:.3f}, {old_y:.3f}) мм -> ({new_x:.3f}, {old_y:.3f}) мм "
                f"(сдвиг {delta:+.2f} мм по X)")

    commit, ok = call_step(logger, "begin_commit()", board.begin_commit)
    if not ok or commit is None:
        return False

    try:
        target.position = vec_mm(new_x, old_y)
        _, ok = call_step(logger, "update_items([target])", board.update_items, [target])
        if not ok:
            call_step(logger, "drop_commit (откат после ошибки)", board.drop_commit, commit)
            return False
        _, ok = call_step(logger, "push_commit(commit, ...)", board.push_commit, commit,
                          f"decap_move_one_cap: {ref}")
        if ok:
            logger.info(f"Готово. {ref} сдвинут на {delta:+.2f} мм по X. "
                        f"Чтобы вернуть: тот же тест с revert: true")
        return ok
    except Exception:
        call_step(logger, "drop_commit (откат после исключения)", board.drop_commit, commit)
        raise
