"""
test_via_placer.py — создание переходных отверстий (via) возле GND-падов
компонентов. Перенесено с decap_placer.kicad.adapter.KiCadBoardAdapter на
core_api (2026-07-14) — заодно ИСПРАВЛЕН баг: get_courtyard_polygon()
проверял атрибуты .points/.start/.end, которых нет ни у BoardRectangle
(там .top_left/.bottom_right), ни у BoardPolygon (там .polygons, список
PolygonWithHoles) — режим offset_from: courtyard молча ВСЕГДА откатывался
на edge, ни разу реально не сработав. Подтверждено конкретным тестом на
моке с spec= реальных полей BoardRectangle.

Поддерживает три режима offset_from:
  - center     — отступ от центра пада по заданному углу
  - edge       — отступ от края пада (с учётом поворота) + доп. зазор
  - courtyard  — отступ от края Courtyard (с учётом поворота) + доп. зазор

geometry/boundary.py и geometry/keepout.py скопированы из decap_placer —
кандидат на будущую консолидацию, пока осознанный дубль (см. их докстринги).

ОПАСНЫЙ: создаёт реальные объекты (via) на плате.
"""
import math
from typing import List, Tuple, Optional, Dict, Any

from kipy.board_types import BoardLayer, FootprintInstance, Pad, BoardRectangle, BoardPolygon
from kipy.geometry import Vector2

from runner.registry import register
from runner.step_helper import call_step
from core_api.geometry import MM, vec_mm
from tests.decap_tools.geometry.boundary import ray_boundary_distance
from tests.decap_tools.geometry.keepout import build_keepout, find_free_point


# ---------- Геометрические утилиты ----------

def intersect_ray_with_rotated_rect(origin: Vector2, dir_x: float, dir_y: float,
                                    rect_center: Vector2, width_mm: float, height_mm: float,
                                    angle_deg: float) -> Optional[float]:
    """
    Расстояние от origin до пересечения луча с прямоугольником шириной
    width_mm/высотой height_mm, центрированным в rect_center, повёрнутым
    на angle_deg. None, если пересечения нет. Проверено численно на
    реальных размерах пада (0603, угол 90°) — математика верна.
    """
    angle_rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)

    dx, dy = origin.x - rect_center.x, origin.y - rect_center.y
    local_ox = dx * cos_a + dy * sin_a
    local_oy = -dx * sin_a + dy * cos_a
    local_dx = dir_x * cos_a + dir_y * sin_a
    local_dy = -dir_x * sin_a + dir_y * cos_a

    if abs(local_dx) < 1e-12 and abs(local_dy) < 1e-12:
        return None

    half_w = (width_mm / 2.0) * MM
    half_h = (height_mm / 2.0) * MM
    t_min, t_max = -float("inf"), float("inf")

    if abs(local_dx) > 1e-12:
        t1, t2 = (-half_w - local_ox) / local_dx, (half_w - local_ox) / local_dx
        t_min, t_max = max(t_min, min(t1, t2)), min(t_max, max(t1, t2))
    elif not (-half_w <= local_ox <= half_w):
        return None

    if abs(local_dy) > 1e-12:
        t1, t2 = (-half_h - local_oy) / local_dy, (half_h - local_oy) / local_dy
        t_min, t_max = max(t_min, min(t1, t2)), min(t_max, max(t1, t2))
    elif not (-half_h <= local_oy <= half_h):
        return None

    if t_max < t_min:
        return None
    return t_min if t_min > 0 else (t_max if t_max > 0 else None)


def get_courtyard_polygon(fp: FootprintInstance) -> List[Vector2]:
    """
    ИСПРАВЛЕНО: раньше искало .points (не существует ни у одного реального
    типа фигуры) и .start/.end (тоже не существует — реальный BoardRectangle
    использует .top_left/.bottom_right). Теперь обрабатывает оба реальных
    типа графики курьярда:
      - BoardRectangle: 4 угла строятся из top_left/bottom_right
      - BoardPolygon: .polygons — список PolygonWithHoles, точки берутся
        из .outline.outline (тот же паттерн, что и core_api.zones для
        Zone.outline.outline)
    """
    courtyard_layers = (BoardLayer.BL_F_CrtYd, BoardLayer.BL_B_CrtYd)
    points: List[Vector2] = []
    for item in fp.definition.items:
        layer = getattr(item, "layer", None)
        if layer not in courtyard_layers:
            continue
        if isinstance(item, BoardRectangle):
            tl, br = item.top_left, item.bottom_right
            points.extend([
                tl,
                Vector2.from_xy(br.x, tl.y),
                br,
                Vector2.from_xy(tl.x, br.y),
            ])
        elif isinstance(item, BoardPolygon):
            for poly in item.polygons:
                points.extend(n.point for n in poly.outline.outline if n.has_point)
    return points


def compute_ideal_position(pad_pos: Vector2, pad_size_mm: Optional[Tuple[float, float]],
                           pad_angle_deg: float, offset_from: str, offset_mm: float,
                           angle_deg: Optional[float],
                           courtyard_polygon: Optional[List[Vector2]] = None,
                           plate_center: Optional[Vector2] = None) -> Tuple[Vector2, float, Tuple[float, float]]:
    """Вычисляет идеальную позицию via, использованный угол и направление."""
    if angle_deg is None:
        if offset_from == "courtyard" and courtyard_polygon:
            cx = sum(p.x for p in courtyard_polygon) / len(courtyard_polygon)
            cy = sum(p.y for p in courtyard_polygon) / len(courtyard_polygon)
            dx, dy = cx - pad_pos.x, cy - pad_pos.y
            angle_deg = math.degrees(math.atan2(dy, dx)) if (abs(dx) > 1e-3 or abs(dy) > 1e-3) else 0.0
        elif offset_from == "edge" and plate_center is not None:
            dx, dy = plate_center.x - pad_pos.x, plate_center.y - pad_pos.y
            angle_deg = math.degrees(math.atan2(dy, dx)) if (abs(dx) > 1e-3 or abs(dy) > 1e-3) else 0.0
        else:
            angle_deg = 0.0

    rad = math.radians(angle_deg)
    dir_x, dir_y = math.cos(rad), math.sin(rad)

    def _from_offset(base_t_nm: float) -> Vector2:
        total = base_t_nm + offset_mm * MM
        return Vector2.from_xy(int(pad_pos.x + dir_x * total), int(pad_pos.y + dir_y * total))

    if offset_from == "center":
        return _from_offset(0), angle_deg, (dir_x, dir_y)

    if offset_from == "edge":
        if pad_size_mm is None:
            return _from_offset(0), angle_deg, (dir_x, dir_y)
        w_mm, h_mm = pad_size_mm
        t = intersect_ray_with_rotated_rect(pad_pos, dir_x, dir_y, pad_pos, w_mm, h_mm, pad_angle_deg)
        if t is None:
            return _from_offset(0), angle_deg, (dir_x, dir_y)
        return _from_offset(t), angle_deg, (dir_x, dir_y)

    if offset_from == "courtyard":
        if not courtyard_polygon:
            return compute_ideal_position(pad_pos, pad_size_mm, pad_angle_deg, "edge", offset_mm,
                                          angle_deg, courtyard_polygon, plate_center)
        try:
            far_point = Vector2.from_xy(int(pad_pos.x + dir_x * 100 * MM), int(pad_pos.y + dir_y * 100 * MM))
            t, _ = ray_boundary_distance(pad_pos, far_point, courtyard_polygon)
            return _from_offset(t), angle_deg, (dir_x, dir_y)
        except Exception:
            return compute_ideal_position(pad_pos, pad_size_mm, pad_angle_deg, "edge", offset_mm,
                                          angle_deg, courtyard_polygon, plate_center)

    raise ValueError(f"неизвестный offset_from: {offset_from!r}")


# ---------- Основной тест ----------

@register("decap_via_placer", suite="decap_tools", dangerous=True, needs_kicad=True)
def run_test(logger, kicad, board, gnd_net_name: str = "GND",
             via: Dict[str, Any] = None, components: List[Dict[str, Any]] = None,
             dry_run: bool = False, **params) -> bool:
    from core_api import footprints, pads, nets, vias as vias_api

    via_cfg = via or {}
    offset_from = via_cfg.get("offset_from", "edge").lower()
    if offset_from not in ("center", "edge", "courtyard"):
        logger.error(f"offset_from должен быть center/edge/courtyard, получено {offset_from!r}")
        return False

    global_offset_mm = via_cfg.get("offset_mm", 1.0)
    global_angle_deg = via_cfg.get("angle_deg")
    drill_mm = via_cfg.get("drill_mm", 0.3)
    diameter_mm = via_cfg.get("diameter_mm", 0.6)
    clearance_mm = via_cfg.get("keepout_clearance_mm", 0.2)
    search_step_mm = via_cfg.get("search_step_mm", 0.1)
    search_max_radius_mm = via_cfg.get("search_max_radius_mm", 3.0)
    search_n_directions = via_cfg.get("search_n_directions", 8)

    if not components:
        logger.error("Параметр components пуст — нечего обрабатывать")
        return False

    gnd_net = nets.get_by_name(board, gnd_net_name)
    if gnd_net is None:
        logger.error(f"Цепь {gnd_net_name!r} не найдена на плате")
        return False

    all_footprints = footprints.get_all(board)
    all_vias = list(board.get_vias())

    if all_footprints:
        cx = sum(fp.position.x for fp in all_footprints) / len(all_footprints)
        cy = sum(fp.position.y for fp in all_footprints) / len(all_footprints)
        plate_center = Vector2.from_xy(int(cx), int(cy))
    else:
        plate_center = Vector2.from_xy(0, 0)

    vias_to_create = []
    errors = []

    for item in components:
        ref = item.get("ref")
        if not ref:
            continue
        comp_offset = item.get("offset_mm", global_offset_mm)
        comp_angle = item.get("angle_deg", global_angle_deg)

        logger.info(f"Обработка {ref}...")
        fp = footprints.get_by_ref(board, ref)
        if fp is None:
            errors.append(f"Компонент {ref} не найден")
            continue

        gnd_pad = next((p for p in pads.get_all(fp) if p.net and p.net.name == gnd_net_name), None)
        if gnd_pad is None:
            errors.append(f"У {ref} нет пада с цепью {gnd_net_name!r}")
            continue

        actual_offset_from = offset_from
        courtyard_polygon = None
        if offset_from == "courtyard":
            courtyard_polygon = get_courtyard_polygon(fp)
            if not courtyard_polygon:
                logger.warning(f"У {ref} нет Courtyard, переключение на edge")
                actual_offset_from = "edge"

        pad_size = pads.get_size_mm(gnd_pad)
        pad_angle = pads.get_angle_deg(gnd_pad)

        ideal_pos, used_angle, direction = compute_ideal_position(
            gnd_pad.position, pad_size, pad_angle,
            offset_from=actual_offset_from, offset_mm=comp_offset, angle_deg=comp_angle,
            courtyard_polygon=courtyard_polygon if actual_offset_from == "courtyard" else None,
            plate_center=plate_center,
        )

        other_fps = [f for f in all_footprints if f.reference_field.text.value != ref]
        bboxes = []
        if other_fps:
            bboxes.extend(board.get_item_bounding_box(other_fps))
        if all_vias:
            bboxes.extend(board.get_item_bounding_box(all_vias))
        bboxes = [b for b in bboxes if b is not None]

        keepout_rects = build_keepout(bboxes, clearance_mm, mm_per_unit=MM)
        via_radius = (diameter_mm / 2.0) * MM

        free_pos = find_free_point(
            ideal=ideal_pos, keepout=keepout_rects, via_radius=via_radius,
            preferred_direction=direction, step_mm=search_step_mm,
            max_radius_mm=search_max_radius_mm, mm_per_unit=MM, n_directions=search_n_directions,
        )
        if free_pos is None:
            errors.append(f"Не удалось найти свободное место для via у {ref} "
                          f"(идеал {ideal_pos.x/MM:.3f}, {ideal_pos.y/MM:.3f})")
            continue

        via_obj = vias_api.make((free_pos.x / MM, free_pos.y / MM), gnd_net, drill_mm, diameter_mm)
        vias_to_create.append(via_obj)
        logger.info(f"  {ref}: via в ({free_pos.x/MM:.3f}, {free_pos.y/MM:.3f}) мм, угол {used_angle:.1f}°")

    if errors:
        logger.warning("Предупреждения/ошибки при обработке:")
        for e in errors:
            logger.warning(f"  {e}")

    if not vias_to_create:
        logger.info("Нет via для создания")
        return False

    if dry_run:
        logger.info(f"DRY-RUN: будет создано {len(vias_to_create)} via")
        return True

    commit, ok = call_step(logger, "begin_commit()", board.begin_commit)
    if not ok or commit is None:
        return False
    try:
        _, ok = call_step(logger, f"create_items({len(vias_to_create)} via)", board.create_items, vias_to_create)
        if not ok:
            call_step(logger, "drop_commit (после ошибки)", board.drop_commit, commit)
            return False
        _, ok = call_step(logger, "push_commit", board.push_commit, commit,
                          f"decap_via_placer: {len(vias_to_create)} via")
        if ok:
            logger.info(f"Успешно создано {len(vias_to_create)} via")
        return ok
    except Exception:
        call_step(logger, "drop_commit (после исключения)", board.drop_commit, commit)
        raise
