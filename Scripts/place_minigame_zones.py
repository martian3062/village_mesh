"""
place_minigame_zones.py
=======================
Places the three mini-game zones (Darts / Kancha / Kite) onto the landscape of
the currently open level, plus the kite building, player spawn and a NavMesh
bounds volume. Everything lands in World Outliner folders under MiniGames/.

PREREQUISITES
  1. The C++ module is compiled (DartsZone / KanchaZone / KiteZone exist) and
     the editor has been restarted since.
  2. The level you want to decorate is open. With World Partition, load the
     region around the village first (World Partition minimap > select area >
     Load Region From Selection) or the landscape won't be found/traceable.

RUN (exact console command — editor menu Window > Output Log, Cmd input):
  py "D:/rural_games/rural_pardeep/Scripts/place_minigame_zones.py"

Re-running is safe: actors labelled MG_* from a previous run are removed first.

Zone placement is map-inspired (Google-Maps sample of Pandori Nijjaran):
  - Darts   : courtyard in the west of the village core
  - Kancha  : open ground by the sarkari school, south-east
  - Kite    : rooftop among the houses north of the centre
Fractions below are of the landscape half-extent; tweak freely.
"""

import math
import unreal

# ----------------------------- configuration -----------------------------

# (x_offset_cm, y_offset_cm, yaw_degrees) — ABSOLUTE offsets from the
# landscape centre, where build_environment.py puts the village core.
# Darts: courtyard inside the ring lane south-west. Kancha: open ground by
# the school along the main road (south-east). Kite: rooftop north of centre.
ZONE_LAYOUT = {
    "Darts":  (-12000.0, -5000.0, 30.0),
    # Kancha stays west of the hills that rise beyond x~23000 (needs flat
    # ground for marble physics); it sits by the relocated school.
    "Kancha": (19500.0,  11000.0,  0.0),
    "Kite":   (4000.0,  -13000.0, -15.0),
}
MAX_PLACEMENT_FRACTION = 0.70   # keep zones inside 70% of the landscape
MIN_ZONE_SPACING = 4000.0       # cm between zone centres (auto-shrunk on small maps)
ROAD_CLEARANCE = 1500.0         # cm from any road spline point
ROAD_LABEL_HINTS = ("road", "path", "track")  # spline actors to keep clear of
NUDGE_STEP = 800.0              # cm per attempt when escaping a road
NAV_VOLUME_MARGIN = 3000.0      # cm of navmesh beyond the outermost zones
FOLIAGE_CLEAR_RADIUS = 600.0    # cm of grass/foliage instances removed per zone

# Kite building dimensions (cm)
BLDG_W = 1000.0   # X
BLDG_D = 800.0    # Y
BLDG_H = 600.0    # two storeys
STEP_RISE = 40.0  # < default MaxStepHeight (45) so the character just walks up
STEP_TREAD = 40.0
STEP_WIDTH = 150.0

CUBE = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
CYLINDER = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
WORLD = UES.get_editor_world()


# ------------------------------- helpers ---------------------------------

def log(msg):
    unreal.log("[place_minigame_zones] {}".format(msg))


def warn(msg):
    unreal.log_warning("[place_minigame_zones] {}".format(msg))


def game_class(name):
    """Resolve a C++ class from the rural_pardeep module, with a clear error."""
    cls = getattr(unreal, name, None)
    if cls is not None:
        return cls
    cls = unreal.load_class(None, "/Script/rural_pardeep.{}".format(name))
    if cls is None:
        raise RuntimeError(
            "Class '{}' not found. Compile the rural_pardeep C++ module and "
            "restart the editor before running this script.".format(name))
    return cls


def ground_z(x, y, z_top, z_bottom, default_z):
    """Line-trace straight down to find the ground height at (x, y)."""
    start = unreal.Vector(x, y, z_top)
    end = unreal.Vector(x, y, z_bottom)
    hit = unreal.SystemLibrary.line_trace_single(
        WORLD, start, end,
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,  # Visibility
        False, [], unreal.DrawDebugTrace.NONE, True)
    if hit:
        # HitResult exposes no plain attributes to Python; go through the
        # native break (same pattern as Epic's own editor scripts).
        return hit.to_dict()["location"].z
    return default_z


def landscape_bounds():
    """
    World-space bounds of the landscape (all loaded LandscapeProxy actors,
    which covers World Partition streaming proxies). Falls back to the actor
    labelled 'Floor', then to a 50x50 m box at the origin.
    """
    proxies = [a for a in EAS.get_all_level_actors()
               if isinstance(a, unreal.LandscapeProxy)]
    boxes = []
    if proxies:
        for proxy in proxies:
            origin, extent = proxy.get_actor_bounds(False)
            boxes.append((origin, extent))
        log("Found {} landscape proxy(ies).".format(len(proxies)))
    else:
        warn("No LandscapeProxy loaded! (World Partition region not loaded, "
             "or this level has no landscape.) Falling back to the Floor/origin.")
        for actor in EAS.get_all_level_actors():
            if actor.get_actor_label().lower() == "floor":
                origin, extent = actor.get_actor_bounds(False)
                boxes.append((origin, extent))
                break

    if not boxes:
        return unreal.Vector(0, 0, 0), unreal.Vector(2500, 2500, 500)

    min_v = unreal.Vector(
        min(o.x - e.x for o, e in boxes),
        min(o.y - e.y for o, e in boxes),
        min(o.z - e.z for o, e in boxes))
    max_v = unreal.Vector(
        max(o.x + e.x for o, e in boxes),
        max(o.y + e.y for o, e in boxes),
        max(o.z + e.z for o, e in boxes))
    center = unreal.Vector((min_v.x + max_v.x) / 2.0,
                           (min_v.y + max_v.y) / 2.0,
                           (min_v.z + max_v.z) / 2.0)
    extent = unreal.Vector((max_v.x - min_v.x) / 2.0,
                           (max_v.y - min_v.y) / 2.0,
                           (max_v.z - min_v.z) / 2.0)
    return center, extent


def road_sample_points():
    """World locations sampled every 5 m along every road/path spline actor."""
    points = []
    for actor in EAS.get_all_level_actors():
        label = actor.get_actor_label().lower()
        if not any(hint in label for hint in ROAD_LABEL_HINTS):
            continue
        spline = actor.get_component_by_class(unreal.SplineComponent)
        if spline is None:
            continue
        length = spline.get_spline_length()
        dist = 0.0
        while dist <= length:
            points.append(spline.get_location_at_distance_along_spline(
                dist, unreal.SplineCoordinateSpace.WORLD))
            dist += 500.0
    if points:
        log("Sampled {} road spline points for clearance checks.".format(len(points)))
    return points


def clear_of_roads(x, y, road_points):
    return all(math.hypot(p.x - x, p.y - y) >= ROAD_CLEARANCE for p in road_points)


def spot_ok(x, y, road_points, resolved, min_spacing, center, extent):
    """All placement constraints at once: roads, zone spacing, landscape bounds."""
    if not clear_of_roads(x, y, road_points):
        return False
    if any(math.hypot(x - rx, y - ry) < min_spacing for rx, ry in resolved):
        return False
    if abs(x - center.x) > MAX_PLACEMENT_FRACTION * extent.x:
        return False
    if abs(y - center.y) > MAX_PLACEMENT_FRACTION * extent.y:
        return False
    return True


def resolve_position(name, x, y, road_points, resolved, min_spacing, center, extent):
    """Spiral outward from the preferred spot until every constraint holds.

    Zones are resolved one at a time against the already-placed ones, so a
    road nudge can never silently break spacing or push outside the bounds.
    """
    if spot_ok(x, y, road_points, resolved, min_spacing, center, extent):
        return x, y
    for i in range(1, 25):
        angle = i * 0.8 * math.pi
        radius = NUDGE_STEP * (1.0 + i * 0.5)
        nx = x + math.cos(angle) * radius
        ny = y + math.sin(angle) * radius
        if spot_ok(nx, ny, road_points, resolved, min_spacing, center, extent):
            log("Nudged {} by {:.0f} cm to satisfy road/spacing/bounds.".format(
                name, math.hypot(nx - x, ny - y)))
            return nx, ny
    warn("{}: no nearby spot satisfies all constraints; using the preferred "
         "spot — verify roads/spacing manually.".format(name))
    return x, y


def clear_foliage_instances(x, y, z, radius):
    """
    Remove painted-foliage / ISM / PCG-generated instances overlapping a play
    area (covers HISM + foliage components, which subclass ISM). NOTE: if a
    PCG graph regenerates it will respawn its instances — for a durable fix
    add a PCG difference/exclusion volume over the zone and regenerate.
    """
    removed = 0
    centre = unreal.Vector(x, y, z)
    for actor in EAS.get_all_level_actors():
        for comp in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            indices = list(comp.get_instances_overlapping_sphere(centre, radius, True))
            if indices:
                comp.remove_instances(indices)
                removed += len(indices)
    if removed:
        log("Cleared {} foliage/ISM instances within {:.0f} cm of "
            "({:.0f}, {:.0f}).".format(removed, radius, x, y))


def spawn_zone(class_name, label, location, yaw):
    actor = EAS.spawn_actor_from_class(
        game_class(class_name), location, unreal.Rotator(0.0, 0.0, yaw))
    actor.set_actor_label(label)
    return actor


def spawn_mesh(mesh, label, folder, location, scale, yaw=0.0):
    actor = EAS.spawn_actor_from_object(mesh, location, unreal.Rotator(0.0, 0.0, yaw))
    actor.set_actor_label(label)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    actor.set_folder_path(folder)
    return actor


def set_trigger_extent(zone, extent):
    box = zone.get_component_by_class(unreal.BoxComponent)
    if box:
        box.set_box_extent(unreal.Vector(*extent))


def rot_offset(x, y, yaw_deg):
    """Rotate a local (x, y) offset by the zone yaw."""
    r = math.radians(yaw_deg)
    return x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)


def cleanup_previous_run():
    stale = [a for a in EAS.get_all_level_actors()
             if a.get_actor_label().startswith("MG_")]
    for actor in stale:
        EAS.destroy_actor(actor)
    if stale:
        log("Removed {} actors from a previous run.".format(len(stale)))


# ------------------------------ main ------------------------------------

def main():
    cleanup_previous_run()

    center, extent = landscape_bounds()
    z_top = center.z + extent.z + 5000.0
    z_bottom = center.z - extent.z - 5000.0
    log("Placement bounds: centre=({:.0f}, {:.0f}) half-extent=({:.0f}, {:.0f})".format(
        center.x, center.y, extent.x, extent.y))

    road_points = road_sample_points()
    min_spacing = min(MIN_ZONE_SPACING,
                      max(extent.x, extent.y) * MAX_PLACEMENT_FRACTION)

    # Resolve XY per zone sequentially so every constraint (roads, spacing,
    # bounds) is checked against the zones already placed. Offsets are
    # absolute cm from the landscape centre, clamped inside the bounds.
    positions = {}
    for name, (ox, oy, _yaw) in ZONE_LAYOUT.items():
        max_x = MAX_PLACEMENT_FRACTION * extent.x
        max_y = MAX_PLACEMENT_FRACTION * extent.y
        x = center.x + max(-max_x, min(max_x, ox))
        y = center.y + max(-max_y, min(max_y, oy))
        positions[name] = resolve_position(
            name, x, y, road_points, list(positions.values()),
            min_spacing, center, extent)

    ground = {name: ground_z(x, y, z_top, z_bottom, center.z)
              for name, (x, y) in positions.items()}

    # The kite building needs FLAT ground: sample its footprint corners and
    # the stair foot; sink the base to the lowest sample, hunt for flatter
    # ground nearby if the spread exceeds a walkable step (45 cm).
    byaw = ZONE_LAYOUT["Kite"][2]

    def building_ground(cx, cy):
        samples = []
        for lx, ly in ((-BLDG_W / 2, -BLDG_D / 2), (BLDG_W / 2, -BLDG_D / 2),
                       (-BLDG_W / 2, BLDG_D / 2), (BLDG_W / 2, BLDG_D / 2),
                       (BLDG_W / 2 + STEP_WIDTH, -300.0),
                       (BLDG_W / 2 + STEP_WIDTH, 260.0)):
            ox, oy = rot_offset(lx, ly, byaw)
            samples.append(ground_z(cx + ox, cy + oy, z_top, z_bottom, center.z))
        return min(samples), max(samples) - min(samples)

    kx0, ky0 = positions["Kite"]
    base_z, spread = building_ground(kx0, ky0)
    if spread > 45.0:
        for i in range(1, 9):
            angle = i * 0.8 * math.pi
            nx = kx0 + math.cos(angle) * NUDGE_STEP * i
            ny = ky0 + math.sin(angle) * NUDGE_STEP * i
            others = [p for n, p in positions.items() if n != "Kite"]
            if not spot_ok(nx, ny, road_points, others, min_spacing, center, extent):
                continue
            nz, nspread = building_ground(nx, ny)
            if nspread <= 45.0:
                positions["Kite"] = (nx, ny)
                base_z, spread = nz, nspread
                log("Moved kite building {:.0f} cm to flatter ground "
                    "({:.0f} cm spread).".format(math.hypot(nx - kx0, ny - ky0), nspread))
                break
        else:
            warn("Kite building ground varies {:.0f} cm across its footprint; "
                 "base sunk to the lowest corner — check the stair foot is "
                 "reachable.".format(spread))
    ground["Kite"] = base_z

    # Clear grass/foliage instances out of the play areas.
    for name, (x, y) in positions.items():
        clear_foliage_instances(x, y, ground[name], FOLIAGE_CLEAR_RADIUS)

    # ---------------- Darts: courtyard target game ----------------
    dx, dy = positions["Darts"]
    dz = ground["Darts"]
    dyaw = ZONE_LAYOUT["Darts"][2]
    darts = spawn_zone("DartsZone", "MG_DartsZone", unreal.Vector(dx, dy, dz), dyaw)
    darts.set_folder_path("MiniGames/Darts")
    set_trigger_extent(darts, (350, 300, 250))

    # Mud wall behind the board (board hangs at local +X 237 / height 173).
    wx, wy = rot_offset(260.0, 0.0, dyaw)
    spawn_mesh(CUBE, "MG_Darts_Wall", "MiniGames/Darts",
               unreal.Vector(dx + wx, dy + wy, dz + 140.0),
               (0.3, 4.0, 2.8), dyaw)

    # ---------------- Kancha: marbles ring ----------------
    kx, ky = positions["Kancha"]
    kz = ground["Kancha"]
    kancha = spawn_zone("KanchaZone", "MG_KanchaZone", unreal.Vector(kx, ky, kz),
                        ZONE_LAYOUT["Kancha"][2])
    kancha.set_folder_path("MiniGames/Kancha")
    set_trigger_extent(kancha, (450, 450, 250))

    # Flat dirt patch disc under the ring (assign a dirt material later).
    spawn_mesh(CYLINDER, "MG_Kancha_DirtPatch", "MiniGames/Kancha",
               unreal.Vector(kx, ky, kz + 2.0), (5.6, 5.6, 0.05))

    # ---------------- Kite: rooftop building ----------------
    bx, by = positions["Kite"]
    bz = ground["Kite"]
    byaw = ZONE_LAYOUT["Kite"][2]
    folder = "MiniGames/Kite/Building"

    def bpos(lx, ly, lz):
        ox, oy = rot_offset(lx, ly, byaw)
        return unreal.Vector(bx + ox, by + oy, bz + lz)

    # Solid 2-storey block; its flat top IS the walkable roof.
    spawn_mesh(CUBE, "MG_Kite_Building", folder,
               bpos(0, 0, BLDG_H / 2.0), (BLDG_W / 100.0, BLDG_D / 100.0, BLDG_H / 100.0), byaw)

    # Parapet (1 m high, 20 cm thick) around the roof edge.
    spawn_mesh(CUBE, "MG_Kite_Parapet_N", folder, bpos(0, BLDG_D / 2 - 10, BLDG_H + 50),
               (BLDG_W / 100.0, 0.2, 1.0), byaw)
    spawn_mesh(CUBE, "MG_Kite_Parapet_S", folder, bpos(0, -BLDG_D / 2 + 10, BLDG_H + 50),
               (BLDG_W / 100.0, 0.2, 1.0), byaw)
    spawn_mesh(CUBE, "MG_Kite_Parapet_W", folder, bpos(-BLDG_W / 2 + 10, 0, BLDG_H + 50),
               (0.2, (BLDG_D - 40) / 100.0, 1.0), byaw)
    # East side leaves a 160 cm gap where the stair lands (y 180..340).
    spawn_mesh(CUBE, "MG_Kite_Parapet_E1", folder, bpos(BLDG_W / 2 - 10, -110, BLDG_H + 50),
               (0.2, 5.8, 1.0), byaw)
    spawn_mesh(CUBE, "MG_Kite_Parapet_E2", folder, bpos(BLDG_W / 2 - 10, 370, BLDG_H + 50),
               (0.2, 0.6, 1.0), byaw)

    # Exterior stair up the east wall: full-height blocks so nothing floats.
    # The first step extends 50 cm below the base so it stays reachable on
    # residual slope (the base is already sunk to the lowest corner sample).
    steps = int(BLDG_H / STEP_RISE)  # 15
    for i in range(steps):
        h = STEP_RISE * (i + 1)
        sink = -50.0 if i == 0 else 0.0
        spawn_mesh(CUBE, "MG_Kite_Step_{:02d}".format(i), folder,
                   bpos(BLDG_W / 2 + STEP_WIDTH / 2, -300.0 + STEP_TREAD * i, (h + sink) / 2.0),
                   (STEP_WIDTH / 100.0, STEP_TREAD / 100.0, (h - sink) / 100.0), byaw)

    # Zone actor sits on the roof; trigger covers the whole rooftop.
    kite = spawn_zone("KiteZone", "MG_KiteZone", bpos(0, 0, BLDG_H + 10.0), byaw)
    kite.set_folder_path("MiniGames/Kite")
    set_trigger_extent(kite, (BLDG_W / 2 - 40, BLDG_D / 2 - 40, 220))

    # ---------------- Player spawn ----------------
    psx, psy = dx - 600.0, dy - 600.0
    psz = ground_z(psx, psy, z_top, z_bottom, dz) + 100.0
    yaw_to_zone = math.degrees(math.atan2(dy - psy, dx - psx))
    player_start = EAS.spawn_actor_from_class(
        unreal.PlayerStart, unreal.Vector(psx, psy, psz),
        unreal.Rotator(0.0, 0.0, yaw_to_zone))
    player_start.set_actor_label("MG_PlayerStart")
    player_start.set_folder_path("Character")

    # ---------------- NavMesh bounds ----------------
    # Cover the zones AND the villagers' whole roaming range (homes, fields,
    # gurdwaras — build_environment stamps work spots up to 45000 cm out).
    xs = [p[0] for p in positions.values()] + [center.x - 45000, center.x + 45000]
    ys = [p[1] for p in positions.values()] + [center.y - 45000, center.y + 45000]
    nav_center = unreal.Vector((min(xs) + max(xs)) / 2.0,
                               (min(ys) + max(ys)) / 2.0,
                               (min(ground.values()) + max(ground.values())) / 2.0 + 200.0)
    nav_size = (max(xs) - min(xs) + 2 * NAV_VOLUME_MARGIN,
                max(ys) - min(ys) + 2 * NAV_VOLUME_MARGIN,
                3000.0)
    nav = EAS.spawn_actor_from_class(unreal.NavMeshBoundsVolume, nav_center,
                                     unreal.Rotator(0.0, 0.0, 0.0))
    nav.set_actor_label("MG_NavBounds")
    nav.set_folder_path("MiniGames/Nav")
    # Spawned volumes carry a default 200 cm brush cube -> scale to fit.
    nav.set_actor_scale3d(unreal.Vector(nav_size[0] / 200.0,
                                        nav_size[1] / 200.0,
                                        nav_size[2] / 200.0))
    _, nav_extent = nav.get_actor_bounds(False)
    if nav_extent.x < 100.0:
        unreal.log_error(
            "[place_minigame_zones] NavMeshBoundsVolume spawned with NO brush "
            "geometry — no navmesh will build and villager NPCs will fall back "
            "to straight-line strolling. Drag a NavMeshBoundsVolume from Place "
            "Actors > Volumes over the village and Build > Build Paths.")

    # ---------------- summary ----------------
    log("Done. Zones placed:")
    for name, (x, y) in positions.items():
        log("  {:<7} at ({:>8.0f}, {:>8.0f}, {:>7.0f})".format(name, x, y, ground[name]))
    log("NOTE: PCG foliage is not auto-cleared. Add PCG difference/exclusion "
        "volumes over each zone and regenerate, or the grass will poke through.")
    log("Verify nav coverage with the 'P' key in the viewport; run "
        "Build > Build Paths if the green overlay is missing.")


main()
