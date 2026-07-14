"""
config_schema.py — модель данных и загрузчик для YAML-конфига единого раннера.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import yaml


@dataclass
class KicadConfig:
    timeout_ms: int = 20000
    socket_path: Optional[str] = None  # None = дефолтный путь kipy


@dataclass
class LoggingConfig:
    console_level: str = "INFO"
    file: Optional[str] = "logs/test.log"
    file_level: str = "DEBUG"
    rotate_max_bytes: int = 5 * 1024 * 1024
    rotate_backups: int = 3


@dataclass
class BoardProfile:
    """Именованный набор параметров под конкретную плату (borта разные —
    refdes/pad/zone/net на них разные)."""
    ref: Optional[str] = None
    pad: Optional[str] = None
    zone: Optional[str] = None
    net: Optional[str] = None
    # Открыто для расширения — доп. параметры конкретных тестов/скриптов,
    # которых нет в общем наборе выше, кладутся сюда как есть.
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestEntry:
    """Один тест внутри суиты: включён ли, опасен ли, и его собственные
    параметры (переопределяют/дополняют параметры из BoardProfile)."""
    name: str
    enabled: bool = True
    dangerous: bool = False
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SuiteConfig:
    """Одна суита (static / safe / mutating / smoke / decap_tools / ...)."""
    name: str
    enabled: bool = True
    tests: Dict[str, TestEntry] = field(default_factory=dict)


@dataclass
class RootConfig:
    kicad: KicadConfig
    logging: LoggingConfig
    boards: Dict[str, BoardProfile]
    suites: Dict[str, SuiteConfig]


def _load_board_profile(data: Dict[str, Any]) -> BoardProfile:
    known = {"ref", "pad", "zone", "net"}
    extra = {k: v for k, v in data.items() if k not in known}
    return BoardProfile(
        ref=data.get("ref"),
        pad=data.get("pad"),
        zone=data.get("zone"),
        net=data.get("net"),
        extra=extra,
    )


def _load_test_entry(name: str, data: Any) -> TestEntry:
    # Тест может быть указан просто как "test_name: true/false" (без
    # доп. параметров) — тогда data это bool, не dict.
    if isinstance(data, bool):
        return TestEntry(name=name, enabled=data)
    data = data or {}
    known = {"enabled", "dangerous"}
    params = {k: v for k, v in data.items() if k not in known}
    return TestEntry(
        name=name,
        enabled=data.get("enabled", True),
        dangerous=data.get("dangerous", False),
        params=params,
    )


def _load_suite(name: str, data: Dict[str, Any]) -> SuiteConfig:
    data = data or {}
    tests_data = data.get("tests", {}) or {}
    tests = {tname: _load_test_entry(tname, tdata) for tname, tdata in tests_data.items()}
    return SuiteConfig(name=name, enabled=data.get("enabled", True), tests=tests)


def load_config(path: str) -> RootConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    kicad = KicadConfig(**(data.get("kicad", {}) or {}))
    logging_cfg = LoggingConfig(**(data.get("logging", {}) or {}))

    boards_data = data.get("boards", {}) or {}
    boards = {name: _load_board_profile(bdata or {}) for name, bdata in boards_data.items()}

    suites_data = data.get("suites", {}) or {}
    suites = {name: _load_suite(name, sdata) for name, sdata in suites_data.items()}

    return RootConfig(kicad=kicad, logging=logging_cfg, boards=boards, suites=suites)


def resolve_params(board: Optional[BoardProfile], test_entry: TestEntry) -> Dict[str, Any]:
    """
    Собирает итоговые параметры для запуска теста: сначала общие поля
    борта (ref/pad/zone/net + extra), потом поверх — собственные параметры
    теста (test_entry.params побеждает при совпадении ключей).
    """
    merged: Dict[str, Any] = {}
    if board is not None:
        for key in ("ref", "pad", "zone", "net"):
            value = getattr(board, key)
            if value is not None:
                merged[key] = value
        merged.update(board.extra)
    merged.update(test_entry.params)
    return merged
