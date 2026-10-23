"""
build_polish.py  (stage 6)
==========================
Look-and-feel polish pass. Additive + targeted; does NOT re-run earlier stages.

  1. Leafy grass: generates a 12-blade curved grass clump OBJ, imports it as
     SM_GrassClump, builds M_VGGrassLeaf (two-sided, MPC wind sway) and points
     GT_VillageGrass at it — replaces the cone tufts with long leaves.
  2. Doors ajar: every interior door leaf (houses + landmarks) is re-hung on
     its hinge jamb, opened ~38 deg into the room, instead of parked flat.
  3. Interior lighting: a warm non-shadow PointLight at every interior bulb.
  4. Roadmap minimap: re-imports T_VillageMap from the new location-map PNG
     (real house footprints, roads, labels — no circular disc).
  5. Footstep FX: clears the NS_JumpPad placeholder from BP_VillageCharacter
     (the glowing rings that chased the player while walking).

RUN (auto via init_unreal.py when Saved/village_polish_done.txt is missing):
  py "D:/rural_games/rural_pardeep/Scripts/build_polish.py"
"""

import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_upgrade as _bu
from build_upgrade import *                      # noqa: F401,F403
from build_upgrade import _expr                  # import * skips _-prefixed names

import unreal


SRC_DIR = os.path.join(unreal.Paths.project_dir(), "Content", "Village", "Map", "src")
MAP_SRC = os.path.join(SRC_DIR, "village_map.png")
GRASS_OBJ = os.path.join(SRC_DIR, "grass_clump.obj")
MAP_DIR = "/Game/Village/Map"
MESH_DIR = "/Game/Village/Meshes"
GRASS_MESH = MESH_DIR + "/SM_GrassClump"
GRASS_MAT = MAT_DIR + "/M_VGGrassLeaf"
GT_PATH = "/Game/Village/GT_VillageGrass"


# ---------------------------- grass clump mesh ------------------------------

def write_grass_obj(path, z_up=True):
    """12 long curved tapered blades as ribbon strips. z_up=False emits the
    same clump with Y as the up axis (fallback if the importer converts)."""
    rng = random.Random(51)
    verts, faces = [], []
    vi = 0
    SEG = 5
    for _b in range(12):
        ba = rng.random() * 2 * math.pi
        br = math.sqrt(rng.random()) * 20.0
        bx, by = math.cos(ba) * br, math.sin(ba) * br
        la = ba + (rng.random() - 0.5) * 1.2
        dx, dy = math.cos(la), math.sin(la)
        px, py = -dy, dx
        H = 40.0 + rng.random() * 32.0
        LEAN = 10.0 + rng.random() * 22.0
        W0 = 2.6 + rng.random() * 1.2
        base = vi
        for s in range(SEG + 1):
            t = s / float(SEG)
            z = H * t
            drift = LEAN * t * t
            cx, cy = bx + dx * drift, by + dy * drift
            w = W0 * (1.0 - t * 0.92)
            for sx, sy in ((cx + px * w, cy + py * w), (cx - px * w, cy - py * w)):
                if z_up:
                    verts.append("v {:.2f} {:.2f} {:.2f}".format(sx, sy, z))
                else:
                    verts.append("v {:.2f} {:.2f} {:.2f}".format(sx, z, -sy))
                vi += 1
        for s in range(SEG):
            a = base + s * 2 + 1
            faces.append("f {} {} {}".format(a, a + 1, a + 3))
            faces.append("f {} {} {}".format(a, a + 3, a + 2))
    with open(path, "w") as f:
        f.write("o GrassClump\n")
        f.write("\n".join(verts))
        f.write("\nusemtl grass\n")
        f.write("\n".join(faces))
        f.write("\n")


def _import_obj(path):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", MESH_DIR)
    task.set_editor_property("destination_name", "SM_GrassClump")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return EAL.load_asset(GRASS_MESH)


def make_grass_leaf_material(mpc):
    if EAL.does_asset_exist(GRASS_MAT):
        return EAL.load_asset(GRASS_MAT)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGGrassLeaf", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("two_sided", True)

    # colour: dark green base -> brighter leaf green with large-scale noise
    lo = _expr(mat, unreal.MaterialExpressionConstant3Vector, -700, -100)
    lo.set_editor_property("constant", unreal.LinearColor(0.10, 0.30, 0.06, 1.0))
    hi = _expr(mat, unreal.MaterialExpressionConstant3Vector, -700, 80)
    hi.set_editor_property("constant", unreal.LinearColor(0.24, 0.52, 0.13, 1.0))
    n = _expr(mat, unreal.MaterialExpressionNoise, -700, 260)
    n.set_editor_property("scale", 0.002)
    n.set_editor_property("output_min", 0.0)
    n.set_editor_property("output_max", 1.0)
    lerp = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -420, 0)
    MEL.connect_material_expressions(lo, "", lerp, "A")
    MEL.connect_material_expressions(hi, "", lerp, "B")
    MEL.connect_material_expressions(n, "", lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rough = _expr(mat, unreal.MaterialExpressionConstant, -420, 220)
    rough.set_editor_property("r", 0.75)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    # ---- MPC-driven wind sway (same recipe as the tree canopies) ----
    x0, y0 = -1400, 600
    wp = _expr(mat, unreal.MaterialExpressionWorldPosition, x0, y0)
    objpos = _expr(mat, unreal.MaterialExpressionObjectPositionWS, x0, y0 + 220)
    time = _expr(mat, unreal.MaterialExpressionTime, x0, y0 + 420)
    mask_xy = _expr(mat, unreal.MaterialExpressionComponentMask, x0 + 180, y0)
    mask_xy.set_editor_property("r", True); mask_xy.set_editor_property("g", True)
    mask_xy.set_editor_property("b", False); mask_xy.set_editor_property("a", False)
    MEL.connect_material_expressions(wp, "", mask_xy, "")
    dot1 = _expr(mat, unreal.MaterialExpressionDotProduct, x0 + 360, y0)
    ones = _expr(mat, unreal.MaterialExpressionConstant2Vector, x0 + 180, y0 + 90)
    ones.set_editor_property("r", 0.004); ones.set_editor_property("g", 0.003)
    MEL.connect_material_expressions(mask_xy, "", dot1, "A")
    MEL.connect_material_expressions(ones, "", dot1, "B")
    tspeed = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 360, y0 + 420)
    tconst = _expr(mat, unreal.MaterialExpressionConstant, x0 + 180, y0 + 520)
    tconst.set_editor_property("r", 1.6)
    MEL.connect_material_expressions(time, "", tspeed, "A")
    MEL.connect_material_expressions(tconst, "", tspeed, "B")
    phase = _expr(mat, unreal.MaterialExpressionAdd, x0 + 560, y0 + 200)
    MEL.connect_material_expressions(dot1, "", phase, "A")
    MEL.connect_material_expressions(tspeed, "", phase, "B")
    sway = _expr(mat, unreal.MaterialExpressionSine, x0 + 720, y0 + 200)
    MEL.connect_material_expressions(phase, "", sway, "")
    hz = _expr(mat, unreal.MaterialExpressionSubtract, x0 + 360, y0 + 640)
    wpz = _expr(mat, unreal.MaterialExpressionComponentMask, x0 + 180, y0 + 620)
    wpz.set_editor_property("r", False); wpz.set_editor_property("g", False)
    wpz.set_editor_property("b", True); wpz.set_editor_property("a", False)
    opz = _expr(mat, unreal.MaterialExpressionComponentMask, x0 + 180, y0 + 720)
    opz.set_editor_property("r", False); opz.set_editor_property("g", False)
    opz.set_editor_property("b", True); opz.set_editor_property("a", False)
    MEL.connect_material_expressions(wp, "", wpz, "")
    MEL.connect_material_expressions(objpos, "", opz, "")
    MEL.connect_material_expressions(wpz, "", hz, "A")
    MEL.connect_material_expressions(opz, "", hz, "B")
    hdiv = _expr(mat, unreal.MaterialExpressionDivide, x0 + 560, y0 + 640)
    hrange = _expr(mat, unreal.MaterialExpressionConstant, x0 + 360, y0 + 760)
    hrange.set_editor_property("r", 55.0)
    MEL.connect_material_expressions(hz, "", hdiv, "A")
    MEL.connect_material_expressions(hrange, "", hdiv, "B")
    hclamp = _expr(mat, unreal.MaterialExpressionClamp, x0 + 720, y0 + 640)
    MEL.connect_material_expressions(hdiv, "", hclamp, "")
    wind = _expr(mat, unreal.MaterialExpressionCollectionParameter, x0 + 720, y0 + 420)
    wind.set_editor_property("collection", mpc)
    wind.set_editor_property("parameter_name", "WindIntensity")
    amp = _expr(mat, unreal.MaterialExpressionConstant, x0 + 720, y0 + 520)
    amp.set_editor_property("r", 14.0)
    m1 = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 900, y0 + 300)
    MEL.connect_material_expressions(sway, "", m1, "A")
    MEL.connect_material_expressions(wind, "", m1, "B")
    m2 = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 1060, y0 + 360)
    MEL.connect_material_expressions(m1, "", m2, "A")
    MEL.connect_material_expressions(amp, "", m2, "B")
    m3 = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 1220, y0 + 420)
    MEL.connect_material_expressions(m2, "", m3, "A")
    MEL.connect_material_expressions(hclamp, "", m3, "B")
    wdir = _expr(mat, unreal.MaterialExpressionConstant3Vector, x0 + 1220, y0 + 560)
    wdir.set_editor_property("constant", unreal.LinearColor(1.0, 0.35, 0.08, 0.0))
    out = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 1400, y0 + 470)
    MEL.connect_material_expressions(m3, "", out, "A")
    MEL.connect_material_expressions(wdir, "", out, "B")
    MEL.connect_material_property(out, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    MEL.recompile_material(mat)
    EAL.save_asset(GRASS_MAT)
    log("created M_VGGrassLeaf (two-sided, wind sway)")
    return mat


def leafy_grass(mpc):
    """Import the blade clump and repoint GT_VillageGrass at it."""
    write_grass_obj(GRASS_OBJ, z_up=True)
    mesh = _import_obj(GRASS_OBJ)
    if mesh is None:
        warn("grass clump import failed — cone tufts kept")
        return
    # self-heal: if the importer treated the OBJ as Y-up, the clump comes in
    # flat (Z extent tiny). Regenerate with swapped axes and reimport.
    try:
        bb = mesh.get_bounding_box()
        if (bb.max.z - bb.min.z) < 30.0:
            log("grass clump imported flat — regenerating with swapped axes")
            write_grass_obj(GRASS_OBJ, z_up=False)
            mesh = _import_obj(GRASS_OBJ)
    except Exception as e:
        warn("grass bounds probe failed ({}) — keeping import as-is".format(e))
    if mesh is None:
        warn("grass clump reimport failed — cone tufts kept")
        return

    leaf_mat = make_grass_leaf_material(mpc)
    try:
        mesh.set_editor_property("static_materials", [
            unreal.StaticMaterial(material_interface=leaf_mat,
                                  material_slot_name="grass")])
    except Exception:
        try:
            unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_lod_material_slot(
                mesh, leaf_mat, 0, "grass")
        except Exception as e:
            warn("grass material assignment failed: {}".format(e))
    EAL.save_asset(GRASS_MESH)

    gt = EAL.load_asset(GT_PATH)
    if gt is None:
        warn("GT_VillageGrass missing — run stage 5 first")
        return
    density = unreal.PerPlatformFloat()
    density.set_editor_property("default", 90.0)      # clumps are bigger than cones
    scale = unreal.FloatInterval()
    scale.set_editor_property("min", 0.7)
    scale.set_editor_property("max", 1.25)
    varieties = list(gt.get_editor_property("grass_varieties"))
    if not varieties:
        varieties = [unreal.GrassVariety()]
    v = varieties[0]
    v.set_editor_property("grass_mesh", mesh)
    v.set_editor_property("grass_density", density)
    v.set_editor_property("scale_x", scale)
    v.set_editor_property("scale_y", scale)
    v.set_editor_property("scale_z", scale)
    v.set_editor_property("random_rotation", True)
    v.set_editor_property("align_to_surface", True)
    gt.set_editor_property("grass_varieties", varieties)
    EAL.save_asset(GT_PATH)
    log("GT_VillageGrass -> SM_GrassClump (long leafy blades, wind sway)")


# ------------------------------- doors ajar --------------------------------

# (label regex, hinge dx, hinge dy, leaf half-length, hinge side)
# dx/dy = jamb offset from the CURRENT leaf centre in the building's local
# frame; side -1 = left-hinged (opens yaw-38), +1 = right-hinged (yaw+38).
DOOR_TABLE = (
    (re.compile(r"^VG3_House_\d+_doorleaf$"),      62.0, -19.0, 57.5, -1),
    (re.compile(r"^VG3_ShivMandir_doorleaf$"),     52.0, -22.0, 52.5, -1),
    (re.compile(r"^VG3_School_doorleaf$"),         60.0, -23.0, 57.5, -1),
    (re.compile(r"^VG3_Bank_doorleaf$"),           55.0, -20.0, 55.0, -1),
    (re.compile(r"^VG3_Gurdwara_\w+_doorL$"),      55.0, -22.5, 50.0, -1),
    (re.compile(r"^VG3_Gurdwara_\w+_doorR$"),     -55.0, -22.5, 50.0, +1),
)
OPEN_DEG = 38.0


def doors_ajar():
    hung = 0
    for actor in EAS.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue
        for pat, dx, dy, half, side in DOOR_TABLE:
            if not pat.match(label):
                continue
            loc = actor.get_actor_location()
            yaw = actor.get_actor_rotation().yaw
            r = math.radians(yaw)
            hx = loc.x + dx * math.cos(r) - dy * math.sin(r)
            hy = loc.y + dx * math.sin(r) + dy * math.cos(r)
            new_yaw = yaw + side * OPEN_DEG
            nr = math.radians(new_yaw)
            # left-hinged leaves extend -X from the jamb, right-hinged +X
            ext = -half if side < 0 else half
            cx = hx + ext * math.cos(nr)
            cy = hy + ext * math.sin(nr)
            actor.set_actor_location(unreal.Vector(cx, cy, loc.z), False, False)
            actor.set_actor_rotation(unreal.Rotator(0.0, new_yaw, 0.0), False)
            hung += 1
            break
    log("doors re-hung ajar: {}".format(hung))


# ---------------------------- interior lighting -----------------------------

def interior_lights():
    # sweep any previous pass
    removed = 0
    for actor in list(EAS.get_all_level_actors()):
        try:
            if actor.get_actor_label().startswith("VG6_Light_"):
                EAS.destroy_actor(actor)
                removed += 1
        except Exception:
            continue
    if removed:
        log("removed {} old interior lights".format(removed))

    lit = 0
    for actor in list(EAS.get_all_level_actors()):
        try:
            label = actor.get_actor_label()
        except Exception:
            continue
        if "_bulb" not in label:
            continue
        loc = actor.get_actor_location()
        light = EAS.spawn_actor_from_class(
            unreal.PointLight, unreal.Vector(loc.x, loc.y, loc.z - 28.0),
            unreal.Rotator(0, 0, 0))
        if light is None:
            continue
        light.set_actor_label("VG6_Light_{:02d}".format(lit))
        light.set_folder_path("Village/Lights")
        try:
            comp = light.get_editor_property("point_light_component")
            comp.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
            comp.set_editor_property("intensity", 2200.0)
            comp.set_editor_property("attenuation_radius", 850.0)
            comp.set_editor_property("cast_shadows", False)
            comp.set_light_color(unreal.LinearColor(1.0, 0.72, 0.45, 1.0))
        except Exception as e:
            warn("light {} config: {}".format(lit, e))
        lit += 1
    log("{} warm interior lights placed".format(lit))


# ------------------------------ minimap texture -----------------------------

def reimport_map():
    if not os.path.exists(MAP_SRC):
        warn("map PNG missing at {} — skipped".format(MAP_SRC))
        return
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", MAP_SRC)
    task.set_editor_property("destination_path", MAP_DIR)
    task.set_editor_property("destination_name", "T_VillageMap")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = EAL.load_asset(MAP_DIR + "/T_VillageMap")
    if tex:
        try:
            tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
            tex.set_editor_property("srgb", True)
            EAL.save_asset(MAP_DIR + "/T_VillageMap")
        except Exception:
            pass
        log("T_VillageMap re-imported (roadmap style, real footprints)")


# ------------------------------ footstep rings ------------------------------

def clear_footstep_rings():
    bp = EAL.load_asset("/Game/ThirdPerson/Blueprints/BP_VillageCharacter")
    if bp is None:
        warn("BP_VillageCharacter missing — footstep FX not cleared")
        return
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        cdo.set_editor_property("footstep_dust_system", None)
        EAL.save_asset("/Game/ThirdPerson/Blueprints/BP_VillageCharacter",
                       only_if_is_dirty=False)
        log("footstep ring FX cleared from BP_VillageCharacter")
    except Exception as e:
        warn("footstep FX clear failed: {}".format(e))


# --------------------------------- driver -----------------------------------

def main():
    _bu._WORLD = _bu.UES.get_editor_world()
    if _bu._WORLD is None or "Lvl_Village" not in _bu._WORLD.get_name():
        warn("Lvl_Village not loaded — polish aborted")
        return
    mpc = EAL.load_asset(MPC_PATH)

    for name, fn in (("leafy_grass", lambda: leafy_grass(mpc)),
                     ("doors_ajar", doors_ajar),
                     ("interior_lights", interior_lights),
                     ("reimport_map", reimport_map),
                     ("clear_footstep_rings", clear_footstep_rings)):
        try:
            fn()
        except Exception as e:
            warn("{} failed: {}".format(name, e))

    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("polish: all dirty packages saved")
    except Exception as e:
        warn("save failed: {}".format(e))
    log("POLISH COMPLETE")


if __name__ == "__main__":
    main()
