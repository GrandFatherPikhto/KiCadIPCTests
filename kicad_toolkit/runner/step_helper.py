"""
step_helper.py — общий хелпер степ-логирования вызовов API с таймингом.

Тот самый паттерн step()/call_ipc(), который заново писался почти в
каждом диагностическом скрипте на протяжении всего проекта
(test_move_one_cap.py, test_flip_one_cap.py, test_create_one_via.py,
ipc_tests/core.py и т.д.) — теперь один общий источник.
"""
import time
import logging
from typing import Callable, Tuple, Any


def call_step(logger: logging.Logger, label: str, fn: Callable, *args, **kwargs) -> Tuple[Any, bool]:
    """
    Вызывает fn(*args, **kwargs), логирует метку и время выполнения.
    Возвращает (результат, успех). При исключении логирует и возвращает
    (None, False) — НЕ поднимает исключение дальше. Это осознанно другое
    поведение, чем у core_api (там исключения свободно летят наружу) —
    тесты в этом стиле сами решают шаг за шагом, что делать при неудаче
    конкретного вызова, не обязательно прерывая весь тест сразу.
    """
    logger.debug(f"[...] {label}")
    t0 = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        logger.debug(f"[OK]  {label} — {elapsed} мс")
        return result, True
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        logger.warning(f"[ERR] {label} — {elapsed} мс — {type(e).__name__}: {e}")
        return None, False
