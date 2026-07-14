"""
logging_setup.py — единая настройка логирования для всего инструментария:
консоль + файл с ротацией. Раньше это было продублировано (в разных видах)
между ipc_tests/core.py и просто отсутствовало в test_api.py/via_placer.py
(там были голые print() или logging.basicConfig без файла/ротации) — теперь
один источник для всех.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logging(
    logger_name: str = "kicad_toolkit",
    console_level: str = "INFO",
    file_path: Optional[str] = None,
    file_level: str = "DEBUG",
    rotate_max_bytes: int = 5 * 1024 * 1024,
    rotate_backups: int = 3,
) -> logging.Logger:
    """
    Настраивает и возвращает логгер с двумя обработчиками: консоль (уровень
    console_level) и, если указан file_path, файл с ротацией (уровень
    file_level, обычно подробнее консоли).

    Идемпотентно: повторный вызов с тем же logger_name не плодит
    дублирующиеся обработчики (сначала снимает уже навешанные).
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # сами обработчики фильтруют по своим уровням

    # Идемпотентность — не плодим обработчики при повторном вызове
    # (например, если runner вызывается несколько раз в одном процессе).
    for h in list(logger.handlers):
        logger.removeHandler(h)

    fmt = logging.Formatter("%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
                             datefmt="%Y-%m-%d %H:%M:%S")

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, console_level.upper()))
    console.setFormatter(fmt)
    logger.addHandler(console)

    if file_path:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            file_path, maxBytes=rotate_max_bytes, backupCount=rotate_backups, encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, file_level.upper()))
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    logger.propagate = False  # не дублировать в root-логгер
    return logger
