"""
registry.py — единый реестр тестов/скриптов для всего инструментария.

Контракт ОДИН на всё (никаких блокирующих input() нигде — см. историю
про selection-тест): функция теста принимает logger первым позиционным
аргументом, дальше — произвольные именованные параметры (ref, pad, zone,
net, kicad, board, adapter — что нужно конкретному тесту), и возвращает
bool (успех/неуспех). Любое исключение внутри — само по себе means "тест
упал", раннер это отдельно перехватывает, тесту самому оборачивать в
try/except не обязательно.

Регистрация — декоратором, в момент импорта модуля теста:

    from runner.registry import register

    @register("connection", suite="safe")
    def run_test(logger, kicad, board, **params) -> bool:
        ...
        return True

    @register("busy_repro", suite="mutating", dangerous=True)
    def run_test(logger, board, **params) -> bool:
        ...
"""
from dataclasses import dataclass
from typing import Callable, Dict, Any

_REGISTRY: Dict[str, "RegisteredTest"] = {}


@dataclass
class RegisteredTest:
    name: str
    suite: str
    dangerous: bool
    needs_kicad: bool
    func: Callable[..., bool]


def register(name: str, suite: str, dangerous: bool = False, needs_kicad: bool = False):
    """
    Декоратор регистрации теста. name должен быть уникален глобально
    (across всех суит) — так проще запускать один конкретный тест по имени
    без указания суиты.

    needs_kicad: если True, раннер перед вызовом инжектит в параметры
    theста kicad/board — ОДНО общее, переиспользуемое на весь прогон
    соединение (см. run.py). НИКОГДА не открывайте kipy.KiCad() внутри
    самого теста — так уже наступали на грабли (см. историю KiCadIPCTests:
    каждый test_*.py открывал своё соединение -> 8+ утёкших сокетов ->
    ложный "busy" на тяжёлых вызовах).
    """
    def decorator(func: Callable[..., bool]):
        if name in _REGISTRY:
            raise ValueError(f"Тест с именем {name!r} уже зарегистрирован "
                              f"(суита {_REGISTRY[name].suite!r}) — имена должны быть уникальны")
        _REGISTRY[name] = RegisteredTest(name=name, suite=suite, dangerous=dangerous,
                                          needs_kicad=needs_kicad, func=func)
        return func
    return decorator


def get(name: str) -> RegisteredTest:
    if name not in _REGISTRY:
        raise KeyError(f"Тест {name!r} не зарегистрирован (проверьте, что модуль с ним импортирован)")
    return _REGISTRY[name]


def all_tests() -> Dict[str, RegisteredTest]:
    return dict(_REGISTRY)


def tests_in_suite(suite: str) -> Dict[str, RegisteredTest]:
    return {name: t for name, t in _REGISTRY.items() if t.suite == suite}


def clear():
    """Для тестов самого раннера — сбросить реестр между прогонами."""
    _REGISTRY.clear()
