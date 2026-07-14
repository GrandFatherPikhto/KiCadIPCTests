"""
test_selection.py — smoke-тест модуля core_api.selection.

ВАЖНО: раньше (в старом test_api.py) этот раздел блокировал выполнение
через input("Нажмите Enter..."), поджидая, пока пользователь что-то
выделит. Договорились это убрать — единый контракт run_test(logger,
**params) -> bool не должен нигде ждать клавиатуру. Тест просто читает,
что выделено ПРЯМО СЕЙЧАС; если ничего не выделено — это не ошибка (в
отличие от остальных smoke-тестов), тест просто честно об этом сообщает.
Практика использования не меняется: выделите что-то в KiCad глазами,
затем запустите именно этот тест по имени.
"""
from runner.registry import register


@register("smoke_selection", suite="smoke", needs_kicad=True)
def run_test(logger, kicad, board, **params) -> bool:
    from core_api import selection

    desc = selection.describe_selected(board)
    if not desc:
        logger.info("Сейчас ничего не выделено (или выделены не компоненты) — "
                    "выделите что-то в KiCad и запустите тест снова")
        return True  # отсутствие выделения — не ошибка теста

    logger.info(f"Выделено компонентов: {len(desc)}")
    for comp in desc:
        size_str = f"{comp['width_mm']:.3f}x{comp['height_mm']:.3f}мм" if comp["width_mm"] else "?"
        logger.info(f"  {comp['ref']:<6} {comp['value']:<12} "
                    f"поз=({comp['x_mm']:.3f},{comp['y_mm']:.3f})мм угол={comp['angle_deg']:.1f}° "
                    f"размер={size_str} цепи={comp['nets']}")
        for pad in comp["pads"]:
            logger.info(f"      pad {pad['number']:<4} net={pad['net'] or '?':<12} "
                        f"({pad['x_mm']:.3f},{pad['y_mm']:.3f})мм "
                        f"{pad['width_mm']}x{pad['height_mm']}мм")
    return True
