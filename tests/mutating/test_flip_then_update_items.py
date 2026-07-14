"""
test_flip_then_update_items.py — регрессия на баг, найденный и исправленный
2026-07-12 в KiCadDecapPlacer/placement/executor.py:

    "флип — отдельный GUI-action, не update_items. Перечитываем футпринты
    заново, иначе следующий шаг (простановка position/orientation через
    update_items) молча откатит флип устаревшими данными."

run_action("pcbnew.InteractiveEdit.flip") меняет плату НЕ через
update_items(), а как отдельное GUI-действие на стороне KiCad. Если после
этого использовать ЗАКЭШИРОВАННЫЙ локальный объект footprint (полученный
ДО флипа) и вызвать board.update_items([тот_же_объект]) для чего-то
другого — этот update_items() отправляет на сервер СТАРОЕ состояние
layer, и сервер тихо откатывает layer обратно.

Тест воспроизводит оба варианта на одном компоненте по очереди:
  A. "Неправильный" путь: флип -> update_items() со СТАРЫМ объектом.
  B. "Правильный" путь (core_api.footprints.flip_selected + board.refresh):
     флип -> перечитывание -> update_items() со СВЕЖИМ объектом.

ОПАСНЫЙ: мутирует реальный компонент (флип на другую сторону + сдвиг
позиции на 0.5мм). Восстанавливает исходную сторону/позицию в конце
(вариант B — это одновременно и "правильный путь", и восстановление).
Требует параметр ref — НЕ используйте боевой компонент, только тестовый.
"""
from kipy.geometry import Vector2

from runner.registry import register
from runner.step_helper import call_step
from core_api.geometry import MM


@register("mutating_flip_then_update_items", suite="mutating", dangerous=True, needs_kicad=True)
def run_test(logger, kicad, board, ref: str = None, **params) -> bool:
    from core_api import footprints

    if not ref:
        logger.error("Нужен параметр ref (refdes тестового компонента, НЕ боевого)")
        return False

    target = footprints.get_by_ref(board, ref)
    if target is None:
        logger.error(f"{ref} не найден на плате")
        return False

    original_layer = target.layer
    original_position = target.position
    logger.info(f"Исходное состояние {ref}: layer={original_layer}, "
                f"pos=({original_position.x/MM:.3f}, {original_position.y/MM:.3f}) мм")

    # --- Вариант A: "неправильный" путь (стухший объект) ---
    logger.info("--- Вариант A: флип, затем update_items() СО СТАРЫМ объектом ---")
    call_step(logger, "clear_selection", board.clear_selection)
    call_step(logger, "add_to_selection([target])", board.add_to_selection, [target])
    _, ok = call_step(logger, "run_action('pcbnew.InteractiveEdit.flip')",
                       kicad.run_action, "pcbnew.InteractiveEdit.flip")
    call_step(logger, "clear_selection", board.clear_selection)
    if not ok:
        logger.error("Флип не выполнился — прерываю тест")
        return False

    commit, ok = call_step(logger, "begin_commit (вариант A)", board.begin_commit)
    if ok and commit is not None:
        target.position = Vector2.from_xy(original_position.x + int(0.5 * MM), original_position.y)
        _, ok2 = call_step(logger, "update_items([стухший target]) (вариант A)",
                           board.update_items, [target])
        if ok2:
            call_step(logger, "push_commit (вариант A)", board.push_commit, commit,
                      "test_flip_then_update_items: вариант A")
        else:
            call_step(logger, "drop_commit (вариант A)", board.drop_commit, commit)

    after_a = footprints.get_by_ref(board, ref)
    layer_after_a = after_a.layer if after_a else None
    logger.info(f"После варианта A: layer={layer_after_a} "
                f"(ожидание бага: откатился на {original_layer}, а не остался перевёрнутым)")

    bug_reproduced = (layer_after_a == original_layer)

    # --- Вариант B: "правильный" путь — core_api.footprints.flip_selected ---
    logger.info("--- Вариант B: core_api.footprints.flip_selected() + board.refresh ---")
    if after_a is None:
        logger.error(f"{ref} не найден после варианта A — не могу продолжить вариант B")
        return not bug_reproduced

    footprints.flip_selected(kicad, board, [after_a])

    # ВАЖНО (та же причина, по которой существует этот тест): после флипа
    # локальный объект после_a устарел — перечитываем заново.
    fresh_target = footprints.get_by_ref(board, ref)
    if fresh_target is None:
        logger.error(f"{ref} не найден после второго флипа")
        return not bug_reproduced

    commit, ok = call_step(logger, "begin_commit (вариант B)", board.begin_commit)
    if ok and commit is not None:
        fresh_target.position = original_position  # заодно возвращаем позицию
        _, ok2 = call_step(logger, "update_items([свежий fresh_target]) (вариант B)",
                           board.update_items, [fresh_target])
        if ok2:
            call_step(logger, "push_commit (вариант B)", board.push_commit, commit,
                      "test_flip_then_update_items: вариант B (restore)")
        else:
            call_step(logger, "drop_commit (вариант B)", board.drop_commit, commit)

    after_b = footprints.get_by_ref(board, ref)
    layer_after_b = after_b.layer if after_b else None
    logger.info(f"После варианта B: layer={layer_after_b} "
                f"(ожидание фикса: {original_layer} — второй флип вернул на исходную сторону)")

    fix_confirmed = (layer_after_b == original_layer)

    if bug_reproduced:
        logger.warning("[ПОДТВЕРЖДЕНО] Вариант A воспроизвёл баг: update_items() со стухшим "
                       "объектом после флипа откатил layer обратно.")
    else:
        logger.info("[НЕ ВОСПРОИЗВЕДЕНО] Вариант A не откатил layer в этом прогоне.")

    logger.info(f"Итог по слою: исходный={original_layer}, после A={layer_after_a}, "
                f"после B={layer_after_b} (должен = исходному — второй флип это возврат)")

    return fix_confirmed
