#!/usr/bin/env python3
"""
Основные утилиты: подключение к IPC, настройка логирования.

ГЛАВНОЕ ИЗМЕНЕНИЕ (2026-07-12):
    Раньше каждый test_*.py вызывал get_kicad_board() самостоятельно, и
    каждый такой вызов создавал НОВОЕ IPC-подключение (kipy.KiCad(...) со
    случайным client_name). У kipy.KiCad в версии 0.7.1 нет close()/__exit__,
    так что за один прогон test_all.py накапливалось 7-8 незакрытых
    клиентских сокетов к одному процессу KiCad. По логам это било по тяжёлым
    списочным вызовам (get_footprints/get_tracks/get_pads/...) ошибкой
    "KiCad is busy and cannot respond to API requests right now", в то время
    как лёгкий get_nets() проскакивал.

    Фикс: get_kicad_board() теперь кэширует ОДНО соединение на процесс и
    переиспользует его во всех тестах. Перед выдачей из кэша проверяется
    board.get_project() как элементарный "пинг" — если соединение протухло
    (KiCad перезапущен, сокет закрыт), переподключаемся автоматически.

    Подтвердить/опровергнуть исходную гипотезу можно тестом
    test_connection_reuse.py — он явно проверяет, что два подряд идущих
    вызова get_kicad_board() возвращают один и тот же объект без пересоздания
    соединения.
"""
import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from kipy import KiCad

DEFAULT_SOCKET_PATH = r"ipc://C:\Users\grand\AppData\Local\Temp\kicad\api.sock"

# --- Кэш соединения на весь процесс -----------------------------------
_cached_kicad = None
_cached_board = None
_cached_socket_path = None


def _elapsed_ms(t0):
    return round((time.perf_counter() - t0) * 1000, 1)


def setup_logging(log_file="logs/test.log", console_level=logging.INFO, file_level=logging.DEBUG):
    """
    Настраивает логирование: вывод в консоль и в файл с ротацией.
    Возвращает объект logger.

    console_level/file_level разведены специально: в консоли по умолчанию
    только INFO и выше (не захламляем экран), а в файле — DEBUG, где
    оседают все тайминги вызовов call_ipc() ниже. Если нужно видеть тайминги
    прямо в консоли во время отладки — передайте console_level=logging.DEBUG.
    """
    logger = logging.getLogger("KiCadIPCTests")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    logger.addHandler(console_handler)

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_kicad_board(socket_path=None, logger=None, timeout_ms=10000, force_reconnect=False):
    """
    Подключается к KiCad через IPC и возвращает объект Board.

    Переиспользует закэшированное соединение между вызовами (см. докстринг
    модуля). force_reconnect=True форсирует новое подключение — полезно в
    самом первом тесте прогона или если явно нужно проверить именно
    "холодное" подключение.
    """
    global _cached_kicad, _cached_board, _cached_socket_path

    if socket_path is None:
        socket_path = os.environ.get("KICAD_IPC_SOCKET", DEFAULT_SOCKET_PATH)

    can_reuse = (
        not force_reconnect
        and _cached_kicad is not None
        and _cached_board is not None
        and _cached_socket_path == socket_path
    )

    if can_reuse:
        t0 = time.perf_counter()
        try:
            # Простейшая проверка живости кэшированного соединения.
            _cached_board.get_project()
            if logger:
                logger.debug(
                    f"Переиспользую существующее IPC-соединение "
                    f"(проверка за {_elapsed_ms(t0)} мс)"
                )
            return _cached_board
        except Exception as e:
            if logger:
                logger.warning(
                    f"Кэшированное соединение недоступно ({type(e).__name__}: {e}), "
                    f"переподключаюсь"
                )
            _cached_kicad = None
            _cached_board = None

    if logger:
        logger.info(f"Подключение к IPC по сокету: {socket_path}")
    t0 = time.perf_counter()
    try:
        kicad = KiCad(socket_path=socket_path, timeout_ms=timeout_ms)
        board = kicad.get_board()
        elapsed = _elapsed_ms(t0)
        if logger:
            logger.info(f"Подключение успешно за {elapsed} мс, объект Board получен.")
        _cached_kicad, _cached_board, _cached_socket_path = kicad, board, socket_path
        return board
    except Exception as e:
        elapsed = _elapsed_ms(t0)
        if logger:
            logger.error(f"Не удалось подключиться к IPC за {elapsed} мс: {type(e).__name__}: {e}")
        return None


def call_ipc(logger, label, func, *args, **kwargs):
    """
    Единая обёртка для вызова любого метода IPC API с таймингом и
    подробным логом. Убирает дублирование try/except-блоков в тестах и,
    что важнее для диагностики, всегда пишет ВРЕМЯ вызова — по нему видно,
    падает запрос мгновенно (сервер сразу отвечает "busy") или висит до
    таймаута (реальная перегрузка/сетевая проблема) — раньше эта разница
    просто терялась.

    Возвращает (result, ok). При ошибке result=None, ok=False.
    """
    t0 = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        elapsed = _elapsed_ms(t0)
        count = f", {len(result)} шт." if hasattr(result, "__len__") else ""
        logger.debug(f"[OK]  {label} — {elapsed} мс{count}")
        return result, True
    except Exception as e:
        elapsed = _elapsed_ms(t0)
        logger.error(f"[ERR] {label} — {elapsed} мс — {type(e).__name__}: {e}")
        return None, False
