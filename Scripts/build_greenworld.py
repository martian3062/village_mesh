"""
build_greenworld.py  (stage 5)
==============================
Additive "green + interiors + birds + map" pass. Reuses stage-3 (build_upgrade)
helpers/builders by import, and applies ONLY the new content with TARGETED
cleanup, so it does NOT re-run roads/fields/trees/existing houses:

  1. green_ground + add_landscape_grass  -> much greener M_VillageGround +
     real GPU landscape grass across the whole terrain (Grass Output pin only,
     Wetness wiring preserved).
  2. absorb_arch_houses -> the GLB stylised houses (VG_House_NN_arch, no
     interior) become engine-built hollow VG3_ houses (walk-in interiors).
  3. build_landmarks_v3 -> gurdwaras / mandir / school / bank / farm rebuilt as
     hollow walk-in structures (real doorways + furniture).
  4. build_bird_flock -> a flock of animated C++ ABirdActor soaring over the core.
  5. import_village_map -> imports the stylised T_VillageMap texture used by the
     minimap HUD (drawn separately to Content/Village/Map/src/village_map.png).

Idempotent: green/grass are guarded by metadata tags; landmarks/birds and any
already-converted arch houses are swept by targeted label cleanup before rebuild.

RUN (auto via init_unreal.py when Saved/village_greenworld_done.txt is missing):
  py "D:/rural_games/rural_pardeep/Scripts/build_greenworld.py"
"""

import os
import sys

# Reuse every stage-3 helper/builder. build_upgrade guards main() behind
# __main__, so importing it only loads constants + the BasicShape meshes.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_upgrade as _bu
from build_upgrade import *                      # noqa: F401,F403 (helpers/constants/builders)
from build_upgrade import _expr, _wetness_nodes  # import * skips _-prefixed names

import math
import random

import unreal


MAP_DIR = "/Game/Village/Map"
MAP_TEX = MAP_DIR + "/T_VillageMap"
MAP_SRC = os.path.join(unreal.Paths.project_dir(), "Content", "Village", "Map",
                       "src", "village_map.png")


# ============================ greener ground ================================

def green_ground(mpc):
    """Re-own M_VillageGround's base-colour + roughness with much greener
    constants (grass-biased grass/dirt/noise lerp, then the same Wetness mix as
    rewire_ground_wetness). Re-applies ONCE over the older vg3_wet wiring, guarded
    by a new 'vg5_green' metadata tag. Preserves the Wetness wiring."""
    path = MAT_DIR + "/M_VillageGround"
    if not EAL.does_asset_exist(path):
        warn("M_VillageGround missing -- green_ground skipped")
        return
    mat = EAL.load_asset(path)
    try:
        if EAL.get_metadata_tag(mat, "vg5_green") == "1":
            return
    except Exception:
        pass

    grass = _expr(mat, unreal.MaterialExpressionConstant3Vector, -700, 2400)
    grass.set_editor_property("constant", unreal.LinearColor(0.20, 0.46, 0.12, 1.0))
    dirt = _expr(mat, unreal.MaterialExpressionConstant3Vector, -700, 2560)
    dirt.set_editor_property("constant", unreal.LinearColor(0.33, 0.40, 0.20, 1.0))
    cnoise = _expr(mat, unreal.MaterialExpressionNoise, -700, 2720)
    cnoise.set_editor_property("scale", 0.00035)
    cnoise.set_editor_property("turbulence", True)
    cnoise.set_editor_property("output_min", 0.0)
    cnoise.set_editor_property("output_max", 0.45)
    lerp = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -420, 2500)
    MEL.connect_material_expressions(grass, "", lerp, "A")
    MEL.connect_material_expressions(dirt, "", lerp, "B")
    MEL.connect_material_expressions(cnoise, "", lerp, "Alpha")

    wet = _wetness_nodes(mat, mpc, -420, 2700)
    darkm = _expr(mat, unreal.MaterialExpressionMultiply, -220, 2560)
    dk = _expr(mat, unreal.MaterialExpressionConstant, -420, 2620)
    dk.set_editor_property("r", 0.45)
    MEL.connect_material_expressions(lerp, "", darkm, "A")
    MEL.connect_material_expressions(dk, "", darkm, "B")
    colfinal = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -40, 2500)
    MEL.connect_material_expressions(lerp, "", colfinal, "A")
    MEL.connect_material_expressions(darkm, "", colfinal, "B")
    MEL.connect_material_expressions(wet, "", colfinal, "Alpha")
    MEL.connect_material_property(colfinal, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rlo = _expr(mat, unreal.MaterialExpressionConstant, -700, 2900)
    rlo.set_editor_property("r", 0.55)
    rhi = _expr(mat, unreal.MaterialExpressionConstant, -700, 2980)
    rhi.set_editor_property("r", 0.95)
    rnoise = _expr(mat, unreal.MaterialExpressionNoise, -700, 3080)
    rnoise.set_editor_property("scale", 0.0011)
    rnoise.set_editor_property("output_min", 0.0)
    rnoise.set_editor_property("output_max", 1.0)
    rlerp = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -420, 2960)
    MEL.connect_material_expressions(rlo, "", rlerp, "A")
    MEL.connect_material_expressions(rhi, "", rlerp, "B")
    MEL.connect_material_expressions(rnoise, "", rlerp, "Alpha")
    rwet = _expr(mat, unreal.MaterialExpressionConstant, -420, 3100)
    rwet.set_editor_property("r", 0.22)
    rfinal = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -40, 2980)
    MEL.connect_material_expressions(rlerp, "", rfinal, "A")
    MEL.connect_material_expressions(rwet, "", rfinal, "B")
    MEL.connect_material_expressions(wet, "", rfinal, "Alpha")
    MEL.connect_material_property(rfinal, "", unreal.MaterialProperty.MP_ROUGHNESS)

    try:
        EAL.set_metadata_tag(mat, "vg5_green", "1")
    except Exception:
        pass
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("M_VillageGround: greener ground re-owned (vg5_green)")


def add_landscape_grass(mpc):
    """Scatter real GPU landscape grass across the whole terrain. Creates
    SM_GrassTuft (a vertical Cone = a blade/tuft) + GT_VillageGrass and adds a
    LandscapeGrassOutput node to M_VillageGround (only the Grass Output pin is
    written; base colour / roughness / Wetness untouched). Guarded by vg5_grass."""
    ground_path = MAT_DIR + "/M_VillageGround"
    if not EAL.does_asset_exist(ground_path):
        warn("M_VillageGround missing -- landscape grass skipped")
        return
    ground = EAL.load_asset(ground_path)
    try:
        if EAL.get_metadata_tag(ground, "vg5_grass") == "1":
            return
    except Exception:
        pass

    mesh_path = "/Game/Village/Meshes/SM_GrassTuft"
    if EAL.does_asset_exist(mesh_path):
        mesh = EAL.load_asset(mesh_path)
    else:
        mesh = EAL.duplicate_asset("/Engine/BasicShapes/Cone.Cone", mesh_path)
    if mesh is None:
        warn("SM_GrassTuft could not be created -- landscape grass skipped")
        return
    grass_mi = flat_mi("GrassBlade", (0.20, 0.44, 0.13))
    try:
        mesh.set_editor_property("static_materials", [
            unreal.StaticMaterial(material_interface=grass_mi,
                                  material_slot_name="grass")])
    except Exception as e:
        warn("grass mesh material set failed ({}); trying set_material".format(e))
        try:
            mesh.set_material(0, grass_mi)
        except Exception as e2:
            warn("grass mesh material fallback failed: {}".format(e2))
    EAL.save_asset(mesh_path)

    gt_path = "/Game/Village/GT_VillageGrass"
    if EAL.does_asset_exist(gt_path):
        gt = EAL.load_asset(gt_path)
    else:
        gt = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "GT_VillageGrass", "/Game/Village", unreal.LandscapeGrassType,
            unreal.LandscapeGrassTypeFactory())
    if gt is None:
        warn("GT_VillageGrass could not be created -- landscape grass skipped")
        return
    density = unreal.PerPlatformFloat()
    density.set_editor_property("default", 180.0)
    tuft = unreal.FloatInterval()
    tuft.set_editor_property("min", 0.12)
    tuft.set_editor_property("max", 0.4)
    variety = unreal.GrassVariety()
    variety.set_editor_property("grass_mesh", mesh)
    variety.set_editor_property("grass_density", density)
    try:
        variety.set_editor_property("scaling", unreal.GrassScaling.UNIFORM)
    except Exception:
        pass
    variety.set_editor_property("scale_x", tuft)
    variety.set_editor_property("scale_y", tuft)
    variety.set_editor_property("scale_z", tuft)
    variety.set_editor_property("random_rotation", True)
    variety.set_editor_property("align_to_surface", True)
    gt.set_editor_property("grass_varieties", [variety])
    EAL.save_asset(gt_path)

    grass_out = _expr(ground, unreal.MaterialExpressionLandscapeGrassOutput, -40, 2600)
    gi = unreal.GrassInput()
    gi.set_editor_property("name", "VillageGrass")
    gi.set_editor_property("grass_type", gt)
    grass_out.set_editor_property("grass_types", [gi])
    dcon = _expr(ground, unreal.MaterialExpressionConstant, -260, 2600)
    dcon.set_editor_property("r", 1.0)
    try:
        MEL.connect_material_expressions(dcon, "", grass_out, "VillageGrass")
    except Exception:
        try:
            MEL.connect_material_expressions(dcon, "", grass_out, "")
        except Exception as e:
            warn("grass density connect failed ({}); leaving unconnected".format(e))

    try:
        EAL.set_metadata_tag(ground, "vg5_grass", "1")
    except Exception:
        pass
    MEL.recompile_material(ground)
    EAL.save_asset(ground_path)
    log("M_VillageGround: landscape grass output added (GT_VillageGrass)")


# ========================= GLB houses -> hollow ============================

ARCH_HOUSE_RE = _bu.re.compile(r"^VG_House_(\d+)_arch")


def absorb_arch_houses(existing_plots):
    """Convert stage-1 GLB stylised houses (label 'VG_House_NN_arch', no
    interior) into generated-house plots (idx 100+), then DESTROY the GLB
    actors. Returns existing_plots + the new arch-derived plots. Idempotent:
    a re-run finds no '_arch' actors and returns existing_plots unchanged."""
    arch_actors = []
    for actor in EAS.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue
        m = ARCH_HOUSE_RE.match(label)
        if m:
            arch_actors.append((int(m.group(1)), actor))

    max_existing = max((p[6] for p in existing_plots), default=0)
    next_idx = max(max_existing + 1, 100)

    new_plots = []
    seen = set()
    n = 0
    for arch_no, actor in arch_actors:
        if arch_no not in seen:
            seen.add(arch_no)
            loc = actor.get_actor_location()
            yaw = actor.get_actor_rotation().yaw
            origin, extent = actor.get_actor_bounds(False)
            w = max(760.0, min(1200.0, extent.x * 2.0))
            d = max(640.0, min(950.0, extent.y * 2.0))
            storeys = 2 if extent.z * 2.0 > 520.0 else 1
            new_plots.append((loc.x, loc.y, yaw, w, d, storeys, next_idx + n))
            n += 1
        EAS.destroy_actor(actor)

    log("absorbed {} arch house(s) into hollow plots ({} GLB actor(s) removed)".format(
        len(new_plots), len(arch_actors)))
    return list(existing_plots) + new_plots


# ========================= walk-in landmark interiors =======================

LANDMARK_POS = {
    "gurdwaras": [
        ("VG3_Gurdwara_Ravidass",    -1500.0, -14000.0, 1500.0),
        ("VG3_Gurdwara_NihangSingh",  6000.0,  -1500.0, 1200.0),
        ("VG3_Gurdwara_NanakDev",    -2500.0,   2200.0, 1300.0),
    ],
    "mandir": (-15500.0, 800.0),
    "school": (22000.0, 8800.0),
    "bank":   (-32000.0, 16800.0),
    "farm":   (40000.0, -26000.0),
}

# old solid landmark blocks + any prior VG3 landmark parts to sweep before rebuild
LANDMARK_CLEANUP = ("VG_Gurdwara_", "VG_ShivMandir", "VG_School", "VG_Bank", "VG_Farm_",
                    "VG3_Gurdwara_", "VG3_ShivMandir", "VG3_School", "VG3_Bank", "VG3_Farm")


def _part_frame(x, y, gz, yaw, label, folder):
    def local(lx, ly, lz):
        r = math.radians(yaw)
        return unreal.Vector(x + lx * math.cos(r) - ly * math.sin(r),
                             y + lx * math.sin(r) + ly * math.cos(r), gz + lz)

    def part(mesh, m, suffix, lx, ly, lz, scale, extra_yaw=0.0, pitch=0.0):
        return spawn_mesh(mesh, m, label + suffix, folder, local(lx, ly, lz),
                          scale, (pitch, yaw + extra_yaw, 0.0))
    return local, part


def build_gurdwara_v3(label, x, y, size):
    gz = ground_z(x, y)
    yaw = 0.0
    folder = "Village/Landmarks"
    white = flat_mi("PlasterWhite", PLASTER_COLORS[3][1])
    white_in = flat_mi("PlasterInner", (0.90, 0.86, 0.76))
    gold = flat_mi("DomeGold", (0.85, 0.68, 0.28))
    dark = flat_mi("DarkWood", (0.16, 0.11, 0.08))
    saff = flat_mi("Rumala", (0.90, 0.55, 0.12))
    marble = flat_mi("PalkiMarble", (0.92, 0.90, 0.85))
    bulb = make_bulb_material()
    local, part = _part_frame(x, y, gz, yaw, label, folder)

    W = D = size
    t = 25.0
    wh = size * 0.5
    door_w = min(size * 0.22, 320.0)
    door_h = min(size * 0.30, wh - 120.0)

    part(CUBE, white, "_plinth", 0, 0, 18, ((W + 80) / 100, (D + 80) / 100, 0.36))
    part(CUBE, marble, "_floor", 0, 0, 40, ((W - 2 * t) / 100, (D - 2 * t) / 100, 0.06))
    z0 = 36.0

    col_w = (W - door_w) / 2.0
    part(CUBE, white, "_fL", -(door_w / 2 + col_w / 2), -D / 2 + t / 2, z0 + wh / 2,
         (col_w / 100, t / 100, wh / 100))
    part(CUBE, white, "_fR", (door_w / 2 + col_w / 2), -D / 2 + t / 2, z0 + wh / 2,
         (col_w / 100, t / 100, wh / 100))
    part(CUBE, white, "_fLintel", 0, -D / 2 + t / 2, z0 + door_h + (wh - door_h) / 2,
         (door_w / 100, t / 100, (wh - door_h) / 100))
    part(CUBE, dark, "_doorL", -door_w / 2 - 55, -D / 2 + t + 10, z0 + door_h / 2 - 2,
         (1.0, 0.05, (door_h - 8) / 100))
    part(CUBE, dark, "_doorR", door_w / 2 + 55, -D / 2 + t + 10, z0 + door_h / 2 - 2,
         (1.0, 0.05, (door_h - 8) / 100))

    part(CUBE, white, "_back", 0, D / 2 - t / 2, z0 + wh / 2, (W / 100, t / 100, wh / 100))
    part(CUBE, white, "_left", -W / 2 + t / 2, 0, z0 + wh / 2, (t / 100, (D - 2 * t) / 100, wh / 100))
    part(CUBE, white, "_right", W / 2 - t / 2, 0, z0 + wh / 2, (t / 100, (D - 2 * t) / 100, wh / 100))
    part(CUBE, white_in, "_ceil", 0, 0, z0 + wh + 10, (W / 100, D / 100, 0.2))

    pdx, pdy = W * 0.42, D * 0.30
    plat_h = 70.0
    part(CUBE, marble, "_palki", 0, D * 0.24, z0 + plat_h / 2, (pdx / 100, pdy / 100, plat_h / 100))
    part(CUBE, saff, "_manji", 0, D * 0.24, z0 + plat_h + 12, (pdx * 0.7 / 100, pdy * 0.7 / 100, 0.16))

    canopy_h = z0 + wh * 0.82
    hxp, hyp = pdx * 0.55, pdy * 0.55
    for i, (sx, sy) in enumerate(((-hxp, -hyp), (hxp, -hyp), (-hxp, hyp), (hxp, hyp))):
        part(CYLINDER, gold, "_canPole{}".format(i), sx, D * 0.24 + sy,
             (z0 + canopy_h) / 2, (0.10, 0.10, (canopy_h - z0) / 100))
    part(CUBE, saff, "_canopy", 0, D * 0.24, canopy_h,
         (pdx * 1.25 / 100, pdy * 1.25 / 100, 0.12))

    part(CUBE, bulb, "_bulb", 0, 0, z0 + wh - 40, (0.14, 0.14, 0.22))

    s = size / 100.0
    part(SPHERE, gold, "_Dome", 0, 0, z0 + wh + size * 0.12, (s * 0.36, s * 0.36, s * 0.30))
    corner = size / 2 - 60
    for i, (cx, cy) in enumerate(((-corner, -corner), (corner, -corner),
                                  (-corner, corner), (corner, corner))):
        part(CYLINDER, white, "_T{}".format(i), cx, cy, wh * 0.62, (0.9, 0.9, wh / 100 * 1.24))
    part(CYLINDER, gold, "_Nishan", size / 2 + 150, 0, 350, (0.15, 0.15, 7.0))
    part(CUBE, saff, "_NishanFlag", size / 2 + 210, 0, 600, (1.2, 0.05, 0.9))


def build_mandir_v3(x, y):
    gz = ground_z(x, y)
    yaw = 0.0
    folder = "Village/Landmarks"
    label = "VG3_ShivMandir"
    cream = flat_mi("MandirStone", (0.88, 0.80, 0.66))
    cream_in = flat_mi("PlasterInner", (0.90, 0.86, 0.76))
    orange = flat_mi("MandirOrange", (0.85, 0.42, 0.12))
    dark = flat_mi("DarkWood", (0.16, 0.11, 0.08))
    steel = flat_mi("TankSteel", (0.55, 0.58, 0.62))
    marble = flat_mi("PalkiMarble", (0.92, 0.90, 0.85))
    bulb = make_bulb_material()
    local, part = _part_frame(x, y, gz, yaw, label, folder)

    W = D = 900.0
    t = 24.0
    wh = 420.0
    door_w, door_h = 170.0, 260.0

    part(CUBE, cream, "_plinth", 0, 0, 18, ((W + 70) / 100, (D + 70) / 100, 0.36))
    part(CUBE, marble, "_floor", 0, 0, 40, ((W - 2 * t) / 100, (D - 2 * t) / 100, 0.06))
    z0 = 36.0

    col_w = (W - door_w) / 2.0
    part(CUBE, cream, "_fL", -(door_w / 2 + col_w / 2), -D / 2 + t / 2, z0 + wh / 2,
         (col_w / 100, t / 100, wh / 100))
    part(CUBE, cream, "_fR", (door_w / 2 + col_w / 2), -D / 2 + t / 2, z0 + wh / 2,
         (col_w / 100, t / 100, wh / 100))
    part(CUBE, cream, "_fLintel", 0, -D / 2 + t / 2, z0 + door_h + (wh - door_h) / 2,
         (door_w / 100, t / 100, (wh - door_h) / 100))
    part(CUBE, dark, "_doorleaf", -door_w / 2 - 52, -D / 2 + t + 10, z0 + door_h / 2 - 2,
         (1.05, 0.05, (door_h - 8) / 100))

    part(CUBE, cream, "_back", 0, D / 2 - t / 2, z0 + wh / 2, (W / 100, t / 100, wh / 100))
    part(CUBE, cream, "_left", -W / 2 + t / 2, 0, z0 + wh / 2, (t / 100, (D - 2 * t) / 100, wh / 100))
    part(CUBE, cream, "_right", W / 2 - t / 2, 0, z0 + wh / 2, (t / 100, (D - 2 * t) / 100, wh / 100))
    part(CUBE, cream_in, "_ceil", 0, 0, z0 + wh + 8, (W / 100, D / 100, 0.18))

    part(CUBE, marble, "_altar", 0, D * 0.22, z0 + 35, (2.4, 2.4, 0.7))
    part(CYLINDER, dark, "_lingam", 0, D * 0.22, z0 + 100, (0.5, 0.5, 0.9))
    part(CYLINDER, steel, "_bellrod", 0, -D * 0.30, z0 + wh - 6, (0.05, 0.05, 0.4))
    part(SPHERE, steel, "_bell", 0, -D * 0.30, z0 + wh - 70, (0.28, 0.28, 0.34))
    part(CUBE, bulb, "_bulb", 0, 0, z0 + wh - 32, (0.11, 0.11, 0.16))

    top = z0 + wh
    part(CUBE, cream, "_T1", 0, 0, top + 125, (5, 5, 2.5))
    part(CUBE, cream, "_T2", 0, 0, top + 350, (3.5, 3.5, 2.0))
    part(CONE, orange, "_Tip", 0, 0, top + 600, (2.5, 2.5, 3.0))


def build_school_v3(x, y):
    gz = ground_z(x, y)
    yaw = 12.0
    folder = "Village/Landmarks"
    label = "VG3_School"
    cream = flat_mi("PlasterCream", PLASTER_COLORS[1][1])
    cream_in = flat_mi("PlasterInner", (0.90, 0.86, 0.76))
    dark = flat_mi("DarkWood", (0.16, 0.11, 0.08))
    board = flat_mi("Blackboard", (0.08, 0.12, 0.09))
    wood = flat_mi("DeskWood", (0.60, 0.44, 0.26))
    floor_mi = flat_mi("SchoolFloor", (0.68, 0.62, 0.52))
    bulb = make_bulb_material()
    local, part = _part_frame(x, y, gz, yaw, label, folder)

    W, D, wh = 2000.0, 1300.0, 350.0
    t = 22.0
    door_w, door_h = 180.0, 250.0

    part(CUBE, cream, "_plinth", 0, 0, 16, ((W + 80) / 100, (D + 80) / 100, 0.32))
    part(CUBE, floor_mi, "_floor", 0, 0, 34, ((W - 2 * t) / 100, (D - 2 * t) / 100, 0.06))
    z0 = 30.0

    col_w = (W - door_w) / 2.0
    part(CUBE, cream, "_fL", -(door_w / 2 + col_w / 2), -D / 2 + t / 2, z0 + wh / 2,
         (col_w / 100, t / 100, wh / 100))
    part(CUBE, cream, "_fR", (door_w / 2 + col_w / 2), -D / 2 + t / 2, z0 + wh / 2,
         (col_w / 100, t / 100, wh / 100))
    part(CUBE, cream, "_fLintel", 0, -D / 2 + t / 2, z0 + door_h + (wh - door_h) / 2,
         (door_w / 100, t / 100, (wh - door_h) / 100))
    part(CUBE, dark, "_doorleaf", -door_w / 2 - 60, -D / 2 + t + 12, z0 + door_h / 2 - 2,
         (1.15, 0.05, (door_h - 8) / 100))

    part(CUBE, cream, "_back", 0, D / 2 - t / 2, z0 + wh / 2, (W / 100, t / 100, wh / 100))
    part(CUBE, cream, "_left", -W / 2 + t / 2, 0, z0 + wh / 2, (t / 100, (D - 2 * t) / 100, wh / 100))
    part(CUBE, cream, "_right", W / 2 - t / 2, 0, z0 + wh / 2, (t / 100, (D - 2 * t) / 100, wh / 100))
    part(CUBE, dark, "_winB1", -W * 0.28, D / 2 - 2, z0 + 200, (2.4, 0.05, 0.9))
    part(CUBE, dark, "_winB2", W * 0.28, D / 2 - 2, z0 + 200, (2.4, 0.05, 0.9))
    part(CUBE, cream_in, "_ceil", 0, 0, z0 + wh + 8, (W / 100, D / 100, 0.16))

    inner_gap = 160.0
    gap_y = -D * 0.12
    front_a, front_b = -D / 2 + t, gap_y - inner_gap / 2
    back_a, back_b = gap_y + inner_gap / 2, D / 2 - t
    part(CUBE, cream_in, "_pA", 0, (front_a + front_b) / 2, z0 + wh / 2,
         (0.12, (front_b - front_a) / 100, wh / 100))
    part(CUBE, cream_in, "_pB", 0, (back_a + back_b) / 2, z0 + wh / 2,
         (0.12, (back_b - back_a) / 100, wh / 100))
    part(CUBE, cream_in, "_pLintel", 0, gap_y, z0 + door_h + (wh - door_h) / 2,
         (0.12, inner_gap / 100, (wh - door_h) / 100))

    for room, rx in enumerate((-W * 0.25, W * 0.25)):
        part(CUBE, board, "_board{}".format(room), rx, D / 2 - t - 4, z0 + 195,
             (4.6, 0.06, 1.3))
        for r in range(3):
            ry = D * 0.22 - r * 300.0
            part(CUBE, wood, "_desk{}_{}".format(room, r), rx, ry, z0 + 38, (1.7, 0.55, 0.06))
            part(CUBE, dark, "_deskL{}_{}".format(room, r), rx, ry, z0 + 18, (1.5, 0.4, 0.36))
            part(CUBE, wood, "_bench{}_{}".format(room, r), rx, ry - 95, z0 + 26, (1.7, 0.35, 0.05))
            part(CUBE, dark, "_benchL{}_{}".format(room, r), rx, ry - 95, z0 + 12, (1.5, 0.25, 0.22))
        part(CUBE, bulb, "_bulb{}".format(room), rx, 0, z0 + wh - 30, (0.12, 0.12, 0.18))


def build_bank_v3(x, y):
    gz = ground_z(x, y)
    yaw = -5.0
    folder = "Village/Landmarks"
    label = "VG3_Bank"
    blue = flat_mi("BankBlue", (0.35, 0.45, 0.62))
    blue_in = flat_mi("PlasterInner", (0.90, 0.86, 0.76))
    dark = flat_mi("DarkWood", (0.16, 0.11, 0.08))
    wood = flat_mi("DeskWood", (0.60, 0.44, 0.26))
    steel = flat_mi("TankSteel", (0.55, 0.58, 0.62))
    floor_mi = flat_mi("BankFloor", (0.70, 0.70, 0.66))
    bulb = make_bulb_material()
    local, part = _part_frame(x, y, gz, yaw, label, folder)

    W, D, wh = 1000.0, 700.0, 350.0
    t = 20.0
    door_w, door_h = 170.0, 250.0

    part(CUBE, blue, "_plinth", 0, 0, 16, ((W + 70) / 100, (D + 70) / 100, 0.32))
    part(CUBE, floor_mi, "_floor", 0, 0, 34, ((W - 2 * t) / 100, (D - 2 * t) / 100, 0.06))
    z0 = 30.0

    col_w = (W - door_w) / 2.0
    part(CUBE, blue, "_fL", -(door_w / 2 + col_w / 2), -D / 2 + t / 2, z0 + wh / 2,
         (col_w / 100, t / 100, wh / 100))
    part(CUBE, blue, "_fR", (door_w / 2 + col_w / 2), -D / 2 + t / 2, z0 + wh / 2,
         (col_w / 100, t / 100, wh / 100))
    part(CUBE, blue, "_fLintel", 0, -D / 2 + t / 2, z0 + door_h + (wh - door_h) / 2,
         (door_w / 100, t / 100, (wh - door_h) / 100))
    part(CUBE, dark, "_doorleaf", -door_w / 2 - 55, -D / 2 + t + 10, z0 + door_h / 2 - 2,
         (1.1, 0.05, (door_h - 8) / 100))

    part(CUBE, blue, "_back", 0, D / 2 - t / 2, z0 + wh / 2, (W / 100, t / 100, wh / 100))
    part(CUBE, blue, "_left", -W / 2 + t / 2, 0, z0 + wh / 2, (t / 100, (D - 2 * t) / 100, wh / 100))
    part(CUBE, blue, "_right", W / 2 - t / 2, 0, z0 + wh / 2, (t / 100, (D - 2 * t) / 100, wh / 100))
    part(CUBE, blue_in, "_ceil", 0, 0, z0 + wh + 8, (W / 100, D / 100, 0.16))

    part(CUBE, wood, "_counter", 0, D * 0.12, z0 + 55, (7.0, 0.7, 1.1))
    part(CUBE, dark, "_counterTop", 0, D * 0.12, z0 + 112, (7.4, 1.0, 0.08))
    part(CUBE, steel, "_grille", 0, D * 0.12, z0 + 190, (7.0, 0.05, 1.0))
    for i, cx in enumerate((-W * 0.2, W * 0.2)):
        part(CUBE, dark, "_chair{}".format(i), cx, -D * 0.18, z0 + 22, (0.5, 0.5, 0.04))
        part(CUBE, dark, "_chairBack{}".format(i), cx, -D * 0.18 - 22, z0 + 42, (0.5, 0.05, 0.42))
    part(CUBE, dark, "_staffChair", 0, D * 0.30, z0 + 22, (0.5, 0.5, 0.04))
    part(CUBE, dark, "_staffBack", 0, D * 0.30 + 22, z0 + 42, (0.5, 0.05, 0.42))
    part(CUBE, bulb, "_bulb", 0, 0, z0 + wh - 28, (0.11, 0.11, 0.16))


def build_farm_v3(x, y):
    gz = ground_z(x, y)
    yaw = 20.0
    folder = "Village/Landmarks"
    label = "VG3_Farm"
    barn = flat_mi("BarnBrown", (0.5, 0.3, 0.18))
    barn_in = flat_mi("BarnInner", (0.42, 0.26, 0.16))
    steel = flat_mi("TankSteel", (0.55, 0.58, 0.62))
    hay = flat_mi("HayBale", (0.78, 0.66, 0.32))
    wood = flat_mi("StumpWood", (0.72, 0.60, 0.40))
    floor_mi = flat_mi("BarnFloor", (0.40, 0.32, 0.22))
    local, part = _part_frame(x, y, gz, yaw, label, folder)

    W, D, wh = 1400.0, 900.0, 500.0
    t = 28.0

    part(CUBE, barn, "_plinth", 0, 0, 16, ((W + 80) / 100, (D + 80) / 100, 0.32))
    part(CUBE, floor_mi, "_floor", 0, 0, 34, ((W - 2 * t) / 100, (D - 2 * t) / 100, 0.06))
    z0 = 30.0

    for sx, tag in ((-1, "L"), (1, "R")):
        part(CYLINDER, wood, "_frontPost" + tag, sx * (W / 2 - t), -D / 2 + t / 2,
             z0 + wh / 2, (0.22, 0.22, wh / 100))
    part(CUBE, barn, "_frontBeam", 0, -D / 2 + t / 2, z0 + wh - 30, (W / 100, t / 100, 0.6))

    part(CUBE, barn, "_back", 0, D / 2 - t / 2, z0 + wh / 2, (W / 100, t / 100, wh / 100))
    part(CUBE, barn, "_left", -W / 2 + t / 2, 0, z0 + wh / 2, (t / 100, (D - 2 * t) / 100, wh / 100))
    part(CUBE, barn, "_right", W / 2 - t / 2, 0, z0 + wh / 2, (t / 100, (D - 2 * t) / 100, wh / 100))
    part(CUBE, barn, "_roof", 0, 0, z0 + wh + 12, (W / 100, D / 100, 0.24))
    part(CUBE, barn_in, "_ridge", 0, 0, z0 + wh + 40, (W / 100, 0.5, 0.5))

    bales = [(-W * 0.30, D * 0.26, 0), (-W * 0.30 + 130, D * 0.26, 0),
             (-W * 0.30 + 65, D * 0.26, 1), (W * 0.30, -D * 0.05, 0),
             (W * 0.30, -D * 0.05, 1)]
    for i, (bx, by, layer) in enumerate(bales):
        part(CUBE, hay, "_hay{}".format(i), bx, by, z0 + 40 + layer * 84,
             (1.2, 1.4, 0.8), extra_yaw=(i * 17) % 40)

    stall_d = D * 0.42
    for i, sx in enumerate((-W * 0.22, 0.0, W * 0.22)):
        part(CUBE, wood, "_stallDiv{}".format(i), sx, D / 2 - t - stall_d / 2,
             z0 + 90, (0.12, stall_d / 100, 1.8))

    sgz = ground_z(x + 900, y - 500)
    spawn_mesh(CYLINDER, steel, label + "_Silo", folder,
               unreal.Vector(x + 900, y - 500, sgz + 450), (2.6, 2.6, 9.0))


def build_landmarks_v3():
    built = 0
    for lbl, gx, gy, gsz in LANDMARK_POS["gurdwaras"]:
        try:
            build_gurdwara_v3(lbl, gx, gy, gsz)
            built += 1
        except Exception as e:
            warn("{} failed: {}".format(lbl, e))
    for name, fn, pos in (("mandir", build_mandir_v3, LANDMARK_POS["mandir"]),
                          ("school", build_school_v3, LANDMARK_POS["school"]),
                          ("bank", build_bank_v3, LANDMARK_POS["bank"]),
                          ("farm", build_farm_v3, LANDMARK_POS["farm"])):
        try:
            fn(pos[0], pos[1])
            built += 1
        except Exception as e:
            warn("{} failed: {}".format(name, e))
    log("landmarks v3: {} walk-in structures".format(built))


# ============================== bird flock ================================

def bird_class():
    cls = getattr(unreal, "BirdActor", None)
    if cls is None:
        try:
            cls = unreal.load_class(None, "/Script/rural_pardeep.BirdActor")
        except Exception:
            cls = None
    return cls


def build_bird_flock(rng):
    cls = bird_class()
    if cls is None:
        warn("BirdActor missing — compile the module. Bird flock skipped.")
        return

    bird_colors = [("BirdDark", (0.06, 0.05, 0.05)),
                   ("BirdBrown", (0.20, 0.13, 0.08)),
                   ("BirdSlate", (0.12, 0.12, 0.14))]

    cx0, cy0 = VILLAGE_CENTER
    n_clusters = rng.randint(2, 3)
    clusters = []
    for _ in range(n_clusters):
        a = rng.uniform(0.0, 2.0 * math.pi)
        r = rng.uniform(2000.0, 9000.0)
        clusters.append((cx0 + math.cos(a) * r, cy0 + math.sin(a) * r))

    total = rng.randint(10, 14)
    count = 0
    for i in range(total):
        ccx, ccy = clusters[i % n_clusters]
        a = rng.uniform(0.0, 2.0 * math.pi)
        rr = rng.uniform(600.0, 3400.0)
        x = ccx + math.cos(a) * rr
        y = ccy + math.sin(a) * rr
        dd = math.hypot(x - cx0, y - cy0)
        if dd > 12000.0:
            s = 12000.0 / dd
            x = cx0 + (x - cx0) * s
            y = cy0 + (y - cy0) * s
        az = ground_z(x, y) + rng.uniform(2500.0, 6000.0)
        bird = EAS.spawn_actor_from_class(cls, unreal.Vector(x, y, az), unreal.Rotator(0, 0, 0))
        if bird is None:
            continue
        bird.set_actor_label("VG3_Bird_{}".format(i))
        bird.set_folder_path("Village/Birds")
        sc = rng.uniform(0.8, 1.6)
        bird.set_actor_scale3d(unreal.Vector(sc, sc, sc))
        cname, rgb = bird_colors[i % len(bird_colors)]
        mi = flat_mi(cname, rgb)
        try:
            bird.set_editor_property("ambient_auto_fly", True)
            bird.set_editor_property("circle_radius", rng.uniform(1400.0, 3200.0))
            bird.set_editor_property("circle_speed", rng.uniform(16.0, 34.0) * rng.choice([-1, 1]))
            bird.set_editor_property("bob_amplitude", rng.uniform(120.0, 320.0))
            bird.set_editor_property("flap_speed", rng.uniform(2.6, 4.2))
            bird.set_editor_property("body_material", mi)
        except Exception as e:
            warn("bird {} config: {}".format(i, e))
        count += 1
    log("{} birds soaring over the village".format(count))


# ============================ minimap texture ==============================

def import_village_map():
    """Import the stylised village map PNG (drawn to Content/Village/Map/src)
    as T_VillageMap, a UI texture for the minimap HUD. No-op if the PNG is
    missing (the C++ minimap falls back to a flat panel)."""
    if not os.path.exists(MAP_SRC):
        warn("village map PNG not found at {} — minimap texture skipped".format(MAP_SRC))
        return
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", MAP_SRC)
    task.set_editor_property("destination_path", MAP_DIR)
    task.set_editor_property("destination_name", "T_VillageMap")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    try:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    except Exception as e:
        warn("village map import failed: {}".format(e))
        return
    tex = EAL.load_asset(MAP_TEX)
    if tex:
        try:
            tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
            tex.set_editor_property("srgb", True)
            EAL.save_asset(MAP_TEX)
        except Exception:
            pass
        log("T_VillageMap imported for the minimap HUD")


# ================================= driver ==================================

def _cleanup_labels(prefixes):
    n = 0
    actors = list(EAS.get_all_level_actors())
    for a in actors:
        try:
            label = a.get_actor_label()
        except Exception:
            continue
        if any(label.startswith(p) for p in prefixes):
            EAS.destroy_actor(a)
            n += 1
    return n


def main():
    _bu._WORLD = _bu.UES.get_editor_world()
    if _bu._WORLD is None or "Lvl_Village" not in _bu._WORLD.get_name():
        warn("Lvl_Village not loaded — greenworld aborted")
        return
    rng = random.Random(5150)
    mpc = EAL.load_asset(MPC_PATH)

    # 1. greener ground + real grass
    try:
        green_ground(mpc)
    except Exception as e:
        warn("green_ground failed: {}".format(e))
    try:
        add_landscape_grass(mpc)
    except Exception as e:
        warn("add_landscape_grass failed: {}".format(e))

    # 2. GLB stylised houses -> hollow walk-in houses
    try:
        arch_plots = absorb_arch_houses([])
        if arch_plots:
            bulb = make_bulb_material()
            for plot in arch_plots:
                try:
                    build_house_v3(plot, bulb, rng)
                except Exception as e:
                    warn("arch house {} failed: {}".format(plot[6], e))
    except Exception as e:
        warn("absorb_arch_houses failed: {}".format(e))

    # 3. landmark interiors (sweep old solid + prior VG3 landmarks, then rebuild)
    try:
        removed = _cleanup_labels(LANDMARK_CLEANUP)
        log("landmark cleanup removed {} parts".format(removed))
        build_landmarks_v3()
    except Exception as e:
        warn("landmarks failed: {}".format(e))

    # 4. animated bird flock
    try:
        _cleanup_labels(("VG3_Bird_",))
        build_bird_flock(rng)
    except Exception as e:
        warn("bird flock failed: {}".format(e))

    # 5. minimap map texture
    try:
        import_village_map()
    except Exception as e:
        warn("import_village_map failed: {}".format(e))

    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("greenworld: all dirty packages saved")
    except Exception as e:
        warn("save failed: {}".format(e))
    log("GREENWORLD COMPLETE")


if __name__ == "__main__":
    main()
