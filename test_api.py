#!/usr/bin/env python3
"""
test_api.py — живой smoke-test всего core_api на реальном KiCad.

Не мок, не синтетика — реальные вызовы к открытой плате. Каждый раздел
проверяет один модуль core_api и печатает, что получилось. Требует
открытого KiCad с платой (и, для разделов footprints/pads/vias —
желательно наличие хотя бы одного компонента и одной зоны на плате).

Запуск:
    python test_api.py [--ref C5] [--pad 1] [--zone RA_DECAP_ZONE] [--net GND]

Если конкретные имена компонента/пада/зоны/цепи на вашей плате другие —
передайте своими аргументами, иначе разделы, где они не найдутся, просто
пропустятся с пометкой (это не ошибка теста, а особенность вашей платы).
"""
import argparse
import time
import sys

from core_api import kicad_client, board as board_api, footprints, pads, vias, zones, nets, selection, geometry


def step(label, func, *args, **kwargs):
    print(f"[...] {label}", flush=True)
    t0 = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        print(f"[OK]  {label} — {elapsed} мс", flush=True)
        return result
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        print(f"[ERR] {label} — {elapsed} мс — {type(e).__name__}: {e}", flush=True)
        return None


def section(title):
    print(f"\n=== {title} ===")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=None, help="refdes для теста footprints/pads (например, C5)")
    ap.add_argument("--pad", default="1", help="номер пада для теста pads")
    ap.add_argument("--zone", default=None, help="имя зоны для теста zones")
    ap.add_argument("--net", default="GND", help="имя цепи для теста nets/vias")
    ap.add_argument("--timeout-ms", type=int, default=kicad_client.DEFAULT_TIMEOUT_MS)
    args = ap.parse_args()

    # --- kicad_client ---
    section("kicad_client")
    kicad = step("kicad_client.connect(...)", kicad_client.connect, timeout_ms=args.timeout_ms)
    if kicad is None:
        sys.exit("Не удалось подключиться к KiCad — дальше тест не имеет смысла продолжать.")
    version = step("kicad_client.get_version(kicad)", kicad_client.get_version, kicad)
    if version:
        print(f"   Версия KiCad: {version}")

    board = step("kicad_client.get_board(kicad)", kicad_client.get_board, kicad)
    if board is None:
        sys.exit("Не удалось получить плату — дальше тест не имеет смысла продолжать.")

    # --- footprints ---
    section("footprints")
    all_fps = step("footprints.get_all(board)", footprints.get_all, board)
    print(f"   Всего футпринтов на плате: {len(all_fps) if all_fps else 0}")

    target_ref = args.ref or (footprints.get_reference(all_fps[0]) if all_fps else None)
    fp = None
    if target_ref:
        fp = step(f"footprints.get_by_ref(board, '{target_ref}')", footprints.get_by_ref, board, target_ref)
    if fp:
        print(f"   ref={footprints.get_reference(fp)}  value={footprints.get_value(fp)}")
        print(f"   footprint={footprints.get_footprint_name(fp)}")
        print(f"   позиция={footprints.get_position_mm(fp)} мм  угол={footprints.get_angle_deg(fp)}°")
        print(f"   layer={footprints.get_layer(fp)}  is_back={footprints.is_back(fp)}")
        size = step("footprints.get_bounding_box_mm(board, fp)", footprints.get_bounding_box_mm, board, fp)
        if size:
            print(f"   размер={size[0]:.3f}x{size[1]:.3f} мм")
        sizes = step("footprints.get_bounding_boxes_mm(board, [fp])", footprints.get_bounding_boxes_mm, board, [fp])
        print(f"   батч-версия вернула: {sizes}")
    else:
        print("   [пропуск] не нашли компонент для теста — передайте --ref")

    # --- pads ---
    section("pads")
    if fp:
        all_pads = step("pads.get_all(fp)", pads.get_all, fp)
        print(f"   Пад у {target_ref}: {len(all_pads) if all_pads else 0}")
        pad = step(f"pads.get_by_number(fp, '{args.pad}')", pads.get_by_number, fp, args.pad)
        if pad:
            print(f"   pad {args.pad}: позиция={pads.get_position_mm(pad)} мм")
            print(f"   net={pads.get_net_name(pad)!r}  размер={pads.get_size_mm(pad)}  угол={pads.get_angle_deg(pad)}°")
        else:
            print(f"   [пропуск] нет пада с номером {args.pad!r} — передайте --pad")
    else:
        print("   [пропуск] нет футпринта из предыдущего раздела")

    # --- nets ---
    section("nets")
    all_nets = step("nets.get_all(board)", nets.get_all, board)
    print(f"   Всего цепей на плате: {len(all_nets) if all_nets else 0}")
    net = step(f"nets.get_by_name(board, '{args.net}')", nets.get_by_name, board, args.net)
    if net:
        print(f"   Найдена цепь: {net.name}")
    else:
        print(f"   [пропуск] цепь {args.net!r} не найдена — передайте --net")

    # --- zones ---
    section("zones")
    if args.zone:
        zone = step(f"zones.get_by_name(board, '{args.zone}')", zones.get_by_name, board, args.zone)
        if zone:
            pts = step("zones.get_boundary_points(zone)", zones.get_boundary_points, zone)
            print(f"   Точек контура: {len(pts) if pts else 0}")
        else:
            print(f"   [пропуск] зона {args.zone!r} не найдена")
    else:
        print("   [пропуск] имя зоны не передано — используйте --zone ИМЯ")

    # --- vias (создаём и сразу удаляем — не оставляем мусор на плате) ---
    section("vias")
    if fp and net:
        pos_mm = footprints.get_position_mm(fp)
        via = step("vias.make(...)", vias.make, pos_mm, net, drill_mm=0.3, diameter_mm=0.6)
        if via is not None:
            commit = step("board.begin_commit()", board.begin_commit)
            if commit is not None:
                try:
                    created = step("board.create_items([via])", board.create_items, [via])
                    step("board.push_commit(...)", board.push_commit, commit, "test_api: временная виа")
                    if created:
                        via_id = created[0].id.value
                        print(f"   Создана тестовая виа id={via_id}, удаляю обратно...")
                        commit2 = step("board.begin_commit() (для удаления)", board.begin_commit)
                        if commit2 is not None:
                            step("vias.remove_by_id(board, via_id)", vias.remove_by_id, board, via_id)
                            step("board.push_commit(...) (удаление)", board.push_commit, commit2, "test_api: удаление временной виа")
                            print("   Тестовая виа удалена, плата чистая.")
                except Exception as e:
                    print(f"[ERR] не удалось создать/удалить тестовую виа: {e}")
                    board.drop_commit(commit)
    else:
        print("   [пропуск] нет футпринта или цепи для теста")

    # --- board (commit_with_retry на пустом действии) ---
    section("board")
    ok = step("board_api.commit_with_retry(board, 'noop', lambda: None)",
              board_api.commit_with_retry, board, "test_api: пустой коммит", lambda: None)
    print(f"   commit_with_retry на пустом действии: {ok}")

    # --- selection (п.5: выделите что-нибудь глазами перед этим шагом) ---
    section("selection — ВЫДЕЛИТЕ ЧТО-НИБУДЬ НА ПЛАТЕ ПЕРЕД ЭТИМ ШАГОМ")
    input("   Нажмите Enter, когда выделите один или несколько компонентов в KiCad...")
    board = step("kicad_client.get_board(kicad) (заново)", kicad_client.get_board, kicad)
    desc = step("selection.describe_selected(board)", selection.describe_selected, board)
    if desc:
        print(f"   Выделено компонентов: {len(desc)}")
        for comp in desc:
            size_str = f"{comp['width_mm']:.3f}x{comp['height_mm']:.3f}мм" if comp["width_mm"] else "?"
            print(f"   {comp['ref']:<6} {comp['value']:<12} "
                  f"поз=({comp['x_mm']:.3f},{comp['y_mm']:.3f})мм угол={comp['angle_deg']:.1f}° "
                  f"размер={size_str} цепи={comp['nets']}")
            for pad in comp["pads"]:
                print(f"       pad {pad['number']:<4} net={pad['net'] or '?':<12} "
                      f"({pad['x_mm']:.3f},{pad['y_mm']:.3f})мм "
                      f"{pad['width_mm']}x{pad['height_mm']}мм")
    else:
        print("   Ничего не выделено (или выделены не компоненты) — раздел пропущен по факту, не ошибка.")

    print("\n=== ГОТОВО ===")


if __name__ == "__main__":
    main()
