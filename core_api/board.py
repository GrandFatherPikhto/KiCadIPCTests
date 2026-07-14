"""
board.py — обновление платы и транзакции (коммиты).
"""
import time


def refresh(kicad):
    """
    Перечитывает плату заново. ОБЯЗАТЕЛЬНО после действий, меняющих объекты
    мимо update_items() — например, после footprints.flip_selected():
    локальные Python-объекты после флипа хранят СТАРЫЙ layer/orientation, и
    если пушить их как есть, это молча откатит флип.
    """
    return kicad.get_board()


def begin_commit(board):
    """Начинает транзакцию."""
    return board.begin_commit()


def push_commit(board, commit, description: str = ""):
    """Применяет транзакцию (коммитит изменения на плату)."""
    board.push_commit(commit, description)


def drop_commit(board, commit):
    """Откатывает транзакцию."""
    board.drop_commit(commit)


def commit_with_retry(board, description: str, work_fn, retries: int = 1) -> bool:
    """
    Выполняет work_fn() внутри транзакции, с одним повтором при ошибке по
    умолчанию.

    ВАЖНО: commit = None объявляется ДО try. Если begin_commit() падает
    САМ ПО СЕБЕ (реальный воспроизведённый сценарий — зависшая после
    сбойного коммита IPC-сессия), без этой строчки except-блок обращается
    к ещё не созданной переменной commit и падает с UnboundLocalError,
    полностью маскируя настоящую причину сбоя.
    """
    last_exc = None
    for attempt in range(retries + 1):
        commit = None
        try:
            commit = begin_commit(board)
            work_fn()
            push_commit(board, commit, description)
            return True
        except Exception as e:
            last_exc = e
            if commit is not None:
                try:
                    drop_commit(board, commit)
                except Exception:
                    pass
            if attempt == retries:
                raise
            time.sleep(0.5)
    if last_exc:
        raise last_exc
    return False
