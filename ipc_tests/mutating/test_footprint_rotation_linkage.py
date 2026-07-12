#!/usr/bin/env python3
"""
test_footprint_rotation_linkage.py — прямая проверка бага #21655
(KiCad GitLab: поворот футпринта через IPC тихо рвёт связь symbol<->footprint)
на КОНКРЕТНОМ, безопасном для мутации компоненте.

Контекст: DecapPlacer/executor.py поворачивает компоненты напрямую через
    fp.orientation = cmd.angle; board.update_items([fp])
— ровно тот путь, о котором сообщается в баге #21655. Баг нигде не
упоминается и не проверяется в коде DecapPlacer/TemplateCloner — то есть
либо он не воспроизводится в их сценарии, либо просто ещё не был замечен.

Этот тест не может проверить "связь symbol<->footprint" напрямую через IPC
(в KiCad 9/10 IPC не поддерживает редактор схем — см. память про kipy),
поэтому проверяет ближайший ДОСТУПНЫЙ через IPC косвенный признак
целостности: что footprint.reference_field / value_field / definition.id
(имя футпринта) и КОЛИЧЕСТВО/net-имена его пэдов остаются идентичными до
и после поворота. Если после поворота footprint потерял часть
полей/пэдов, изменил definition.id, либо net на пэдах пропали/обнулились —
это косвенный, но сильный сигнал разрыва линковки, наблюдаемый через IPC.

Для полной проверки (истинная связь с symbol в схеме) НУЖНА ручная
проверка в самом KiCad: после поворота открыть Schematic Editor, выполнить
Update PCB from Schematic (или наоборот) и посмотреть, не появится ли
предупреждение о "footprint link lost" / несовпадении. Этот тест ГОТОВИТ
почву (безопасный поворот на известный угол с возможностью revert) для
такой ручной проверки, но не заменяет её полностью.

ВАЖНО: работает только с ЯВНО указанным refdes — не трогает произвольный
компонент. Используйте некритичный тестовый компонент (например, один из
декаплинг-конденсаторов на тестовой плате test_boards/10CL006YE144C8G,
судя по нумерации в pcb — например C401), НЕ реальный рабочий проект.

Запуск:
    python -m ipc_tests.mutating.test_footprint_rotation_linkage C401 --angle-deg 45
    python -m ipc_tests.mutating.test_footprint_rotation_linkage C401 --revert
"""
import argparse
import sys

from kipy.geometry import Angle

from ipc_tests.core import get_kicad_board, call_ipc, setup_logging
from ipc_tests.board_utils import get_footprints
from ipc_tests.component_utils import get_reference, get_value, get_pads, get_pad_net_name


def _snapshot(fp, logger):
    """Собирает то, что доступно через IPC, для сравнения до/после поворота."""
    ref = get_reference(fp)
    val = get_value(fp)
    fp_name = str(fp.definition.id) if hasattr(fp, "definition") else "?"
    pads = get_pads(fp, logger=logger)
    pad_snapshot = sorted(
        (getattr(p, "number", "?"), get_pad_net_name(p)) for p in pads
    )
    return {
        "ref": ref,
        "value": val,
        "footprint_name": fp_name,
        "pad_count": len(pads),
        "pads": pad_snapshot,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", help="refdes тестового компонента, например C401")
    ap.add_argument("--angle-deg", type=float, default=45.0, help="на сколько градусов повернуть")
    ap.add_argument("--revert", action="store_true", help="повернуть обратно (на -angle-deg)")
    args = ap.parse_args()

    delta = -args.angle_deg if args.revert else args.angle_deg

    logger = setup_logging(log_file="logs/rotation_linkage.log")
    logger.info("=" * 78)
    logger.info(f"ПРОВЕРКА #21655: поворот {args.ref} на {delta:+.1f}° через update_items()")
    logger.info("=" * 78)

    board = get_kicad_board(logger=logger)
    if board is None:
        logger.error("Нет соединения с KiCad.")
        return False

    footprints = get_footprints(board, logger=logger)
    target = next((fp for fp in footprints if get_reference(fp) == args.ref), None)
    if target is None:
        logger.error(f"{args.ref} не найден на плате.")
        return False

    before = _snapshot(target, logger)
    logger.info(f"ДО поворота: {before}")

    old_angle_deg = target.orientation.degrees
    new_angle = Angle.from_degrees(old_angle_deg + delta)

    commit, ok = call_ipc(logger, "begin_commit", board.begin_commit)
    if not ok or commit is None:
        logger.error("Не удалось начать транзакцию.")
        return False

    try:
        target.orientation = new_angle
        _, ok = call_ipc(logger, "update_items([target])", board.update_items, [target])
        if not ok:
            call_ipc(logger, "drop_commit (откат после ошибки)", board.drop_commit, commit)
            return False
        _, ok = call_ipc(
            logger, "push_commit",
            board.push_commit, commit, f"test_footprint_rotation_linkage: {args.ref} {delta:+.1f}°"
        )
        if not ok:
            return False
    except Exception as e:
        logger.error(f"Исключение во время поворота: {type(e).__name__}: {e}")
        call_ipc(logger, "drop_commit (откат после исключения)", board.drop_commit, commit)
        raise

    # ВАЖНО (см. DecapPlacer executor.py, комментарий от 2026-07-12): после
    # операции локальный объект target может быть устаревшим — перечитываем
    # футпринты заново, а не полагаемся на закэшированный target.
    footprints_after = get_footprints(board, logger=logger)
    target_after = next((fp for fp in footprints_after if get_reference(fp) == args.ref), None)
    if target_after is None:
        logger.error(f"{args.ref} НЕ НАЙДЕН после поворота — это уже само по себе серьёзный сигнал.")
        return False

    after = _snapshot(target_after, logger)
    logger.info(f"ПОСЛЕ поворота: {after}")

    identical_except_expected = (
        before["ref"] == after["ref"]
        and before["value"] == after["value"]
        and before["footprint_name"] == after["footprint_name"]
        and before["pad_count"] == after["pad_count"]
        and before["pads"] == after["pads"]
    )

    if identical_except_expected:
        logger.info(
            "[РЕЗУЛЬТАТ] Всё, что видно через IPC (имя футпринта, число пэдов, "
            "net на каждом пэде), идентично до/после поворота. Это НЕ доказывает "
            "отсутствие #21655 (баг про symbol<->footprint linkage в схеме, а "
            "IPC схемный редактор не читает), но по крайней мере на PCB-стороне "
            "связность (net на пэдах) не пострадала. Угол реально изменился: "
            f"{old_angle_deg:.1f}° -> {target_after.orientation.degrees:.1f}°."
        )
        logger.info(
            "СЛЕДУЮЩИЙ ШАГ ДЛЯ ПОЛНОЙ ПРОВЕРКИ: откройте Schematic Editor в KiCad, "
            f"выполните Update PCB from Schematic для {args.ref} и посмотрите, не "
            "появится ли предупреждение о потере привязки к символу."
        )
    else:
        logger.error(
            f"[РЕЗУЛЬТАТ] РАСХОЖДЕНИЕ до/после поворота у {args.ref}! "
            f"ДО={before}, ПОСЛЕ={after}. Это похоже на подтверждение #21655 "
            "или связанной проблемы — не применяйте эту операцию на боевой плате, "
            "пока не разберётесь, что именно изменилось."
        )

    print(f"\nЧтобы вернуть угол обратно: python -m ipc_tests.mutating.test_footprint_rotation_linkage "
          f"{args.ref} --angle-deg {args.angle_deg} --revert")
    return identical_except_expected


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
