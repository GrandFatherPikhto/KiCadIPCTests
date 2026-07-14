"""
dummy_tests.py — тесты-заглушки исключительно для проверки механики
раннера (конфиг -> отбор -> запуск -> логирование), без какой-либо
реальной работы с KiCad. Реальные тесты появятся здесь на следующем шаге,
когда будем переносить содержимое ipc_tests/core_api-smoke/decap_tools.
"""
from runner.registry import register


@register("dummy_ok", suite="toy")
def run_dummy_ok(logger, **params) -> bool:
    logger.info(f"dummy_ok: параметры={params}")
    return True


@register("dummy_fail", suite="toy")
def run_dummy_fail(logger, **params) -> bool:
    logger.info("dummy_fail: специально возвращает False")
    return False


@register("dummy_raises", suite="toy")
def run_dummy_raises(logger, **params) -> bool:
    logger.info("dummy_raises: сейчас упадёт с исключением")
    raise RuntimeError("нарочная ошибка для проверки обработки исключений раннером")


@register("dummy_needs_params", suite="toy")
def run_dummy_needs_params(logger, ref: str = None, pad: str = None, **params) -> bool:
    logger.info(f"dummy_needs_params: ref={ref!r}, pad={pad!r}, остальное={params}")
    return ref is not None and pad is not None


@register("dummy_dangerous", suite="toy", dangerous=True)
def run_dummy_dangerous(logger, **params) -> bool:
    logger.warning("dummy_dangerous: этот тест реально выполнился — если видите это "
                    "без явного enabled:true в конфиге, значит защита не сработала!")
    return True
