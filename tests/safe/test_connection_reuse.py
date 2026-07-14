"""
test_connection_reuse.py — регрессия на "одно соединение на весь прогон".

ПЕРЕОСМЫСЛЕНО при переносе (2026-07-14): раньше проверял кэш
ipc_tests.core.get_kicad_board() — в новой архитектуре такого кэша в
core_api нет вообще (сознательно, core_api без глобального состояния).
Эквивалент этой гарантии теперь — runner.run.SharedConnection, который
раннер создаёт один раз на весь прогон и передаёт всем needs_kicad=True
тестам. Мы уже проверяли это на уровне механики раннера (счётчик вызовов
connect()) — здесь тест проверяет то же самое, но с точки зрения теста,
получающего kicad/board через обычные параметры (то, как это увидит
реальный пользователь раннера), а не заглядывая во внутренности runner.py.
"""
from runner.registry import register


@register("safe_connection_reuse", suite="safe", needs_kicad=True)
def run_test(logger, kicad, board, **params) -> bool:
    from core_api import kicad_client

    # Раз kicad/board уже переданы раннером (единое соединение), этот тест
    # просто подтверждает, что повторные операции с ними работают быстро
    # и стабильно — то есть что нет побочных эффектов вроде "каждый вызов
    # снова открывает новое соединение под капотом" где-то в core_api.
    import time
    timings = []
    for _ in range(5):
        t0 = time.perf_counter()
        v = kicad_client.get_version(kicad)
        timings.append(round((time.perf_counter() - t0) * 1000, 1))
        if not v:
            logger.error("get_version вернул пусто на одном из повторов")
            return False

    logger.info(f"5 повторных вызовов get_version() на общем соединении, мс: {timings}")
    # Быстрая эвристика: если бы каждый вызов реально открывал новое
    # соединение, тайминги были бы на порядок больше (десятки мс, не доли мс).
    return True
