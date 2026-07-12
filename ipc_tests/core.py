#!/usr/bin/env python3
"""
Основные утилиты: подключение к IPC, настройка логирования.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from kipy import KiCad

DEFAULT_SOCKET_PATH = r"ipc://C:\Users\grand\AppData\Local\Temp\kicad\api.sock"

def setup_logging(log_file="logs/test.log", console_level=logging.INFO, file_level=logging.DEBUG):
    """
    Настраивает логирование: вывод в консоль и в файл с ротацией.
    Возвращает объект logger.
    """
    logger = logging.getLogger("KiCadIPCTests")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # Формат логов (без эмодзи)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Обработчик для консоли с явной кодировкой UTF-8 (если возможно)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    # Попробуем установить кодировку, если это TextIOWrapper
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    logger.addHandler(console_handler)

    # Обработчик для файла (кодировка UTF-8)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def get_kicad_board(socket_path=None, logger=None):
    """Подключается к KiCad через IPC и возвращает объект Board."""
    if socket_path is None:
        socket_path = os.environ.get("KICAD_IPC_SOCKET", DEFAULT_SOCKET_PATH)
    if logger:
        logger.info(f"Подключение к IPC по сокету: {socket_path}")
    try:
        kicad = KiCad(socket_path=socket_path)
        board = kicad.get_board()
        if logger:
            logger.info("Подключение успешно, объект Board получен.")
        return board
    except Exception as e:
        if logger:
            logger.error(f"Не удалось подключиться к IPC: {e}")
        return None