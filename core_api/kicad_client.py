"""
kicad_client.py — подключение к KiCad, запуск GUI-действий, версия.

Все функции пакета принимают уже готовый kicad/board объект первым
аргументом — никакого скрытого глобального состояния, легко тестировать
и переиспользовать.
"""
import kipy
from typing import Optional

# Дефолтный таймаут kipy.KiCad() — 2000мс, для тяжёлых коммитов (батчи по
# 10+ объектов) этого реально не хватает — зависал begin_commit() на живой
# сессии. У нас везде 20000мс.
DEFAULT_TIMEOUT_MS = 20000


def connect(timeout_ms: int = DEFAULT_TIMEOUT_MS, socket_path: Optional[str] = None) -> kipy.KiCad:
    """
    Подключается к запущенному экземпляру KiCad. Требует открытого GUI —
    headless-режим появится только в KiCad 11 (на момент версии 9/10 IPC
    работает только с живым интерфейсом PCB-редактора).

    ИСПРАВЛЕНО (2026-07-14, аудит против старого ipc_tests/core.py):
    socket_path раньше был только в KicadConfig (схема YAML), но никуда
    не подключался — реальный connect() принимал только timeout_ms, и
    заданный в конфиге путь к сокету молча игнорировался. Старый код
    поддерживал явный путь (например, KICAD_IPC_SOCKET) на случай
    нестандартного расположения сокета или нескольких открытых
    экземпляров KiCad одновременно — теперь это снова работает.
    """
    if socket_path:
        return kipy.KiCad(socket_path=socket_path, timeout_ms=timeout_ms)
    return kipy.KiCad(timeout_ms=timeout_ms)


def get_board(kicad: kipy.KiCad):
    """Возвращает текущую открытую плату."""
    return kicad.get_board()


def run_action(kicad: kipy.KiCad, action: str):
    """
    Запускает именованное действие интерфейса (TOOL_ACTION) — как если бы
    пользователь нажал хоткей/пункт меню. ОФИЦИАЛЬНО НЕСТАБИЛЬНЫЙ API —
    имена действий и сам факт их наличия не гарантируются между версиями.

    Известное и проверенное нами действие:
      "pcbnew.InteractiveEdit.flip" — настоящий переворот выделенных
      футпринтов на обратную сторону с зеркалированием площадок/
      шёлкографии. Это ЕДИНСТВЕННЫЙ способ добиться реального переворота —
      простое footprint.layer = BL_B_Cu меняет только поле в данных и
      НИЧЕГО не зеркалирует. См. footprints.flip_selected().
    """
    return kicad.run_action(action)


def get_version(kicad: kipy.KiCad) -> str:
    """Версия KiCad, с которым установлено соединение (для диагностики логов)."""
    return kicad.get_version()
