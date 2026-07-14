"""
board.py — обновление платы и транзакции (коммиты).
"""
import time

from .geometry import MM


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


def get_edge_bounding_box_mm(board):
    """
    (width_mm, height_mm) контура платы (слой Edge.Cuts), или None, если
    контур не найден. В kicad-python 0.7.1 у Board НЕТ метода get_size() —
    размер платы нужно считать самому: графика на Edge.Cuts через
    get_items([KOT_PCB_SHAPE]), затем общий bounding box через
    get_item_bounding_box() (для списка элементов — список боксов, не
    один общий, сводим через .merge() сами).
    """
    from kipy.board_types import BoardLayer
    from kipy.proto.common.types import KiCadObjectType

    shapes = board.get_items([KiCadObjectType.KOT_PCB_SHAPE])
    edge_shapes = [s for s in shapes if getattr(s, "layer", None) == BoardLayer.BL_Edge_Cuts]
    if not edge_shapes:
        return None

    boxes = board.get_item_bounding_box(edge_shapes)
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return None

    total = boxes[0]
    for b in boxes[1:]:
        total.merge(b)
    return total.size.x / MM, total.size.y / MM


def get_copper_layer_count(board):
    """Число медных слоёв платы. None при ошибке (не должно случаться в норме)."""
    try:
        return board.get_copper_layer_count()
    except Exception:
        return None


def get_info(board) -> dict:
    """
    Сводка по плате: количество футпринтов/цепей, размер контура (мм),
    число медных слоёв. Объединяет несколько отдельных вызовов в один
    удобный словарь — то же, что раньше делал ipc_tests.board_utils.get_board_info().
    """
    footprints_count = len(list(board.get_footprints()))
    nets_count = len(list(board.get_nets()))
    board_size_mm = get_edge_bounding_box_mm(board)
    copper_layer_count = get_copper_layer_count(board)
    return {
        "footprints_count": footprints_count,
        "nets_count": nets_count,
        "board_size_mm": board_size_mm,
        "copper_layer_count": copper_layer_count,
    }
