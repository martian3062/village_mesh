"""
build_upgrade.py  (stage 3)
===========================
The "finish it properly" pass. Idempotent: everything it creates is labelled
VG3_*; it also owns (removes + rebuilds) these older generations:
  VG_Road_* / VG_DirtRoad_*  -> terrain-conformed roads: 2 asphalt HIGHWAYS
                                (main + side_ne, with edge lines + dashed
                                centre line) and dirt lanes, every segment
                                pitched/rolled onto the ground. No more
                                floating/clipping strips.
  VG_Field_*                 -> fields tilted to the terrain (corner-sampled),
                                crop-row material, dirt bunds, exclusion zones
                                around the new playgrounds.
  VG_Tree_*                  -> multi-lobe peepal/neem/mango trees with wind
                                (replaces the cylinder+ball lollipops).
  VG_House_NN (generated)    -> hollow ENTERABLE houses: real door opening,
                                one real window, two rooms, charpai, chulha,
                                shelf, matka, warm bulb. (_arch GLB houses stay.)
  VGX_Mountain_*             -> calmer, farther, deeper-sunk ring; the two scan
                                sets that shredded are dropped.
New content: cricket maidan + kancha playground dressing, grazing animals
(cows/buffalo/horses, C++ AGrazingAnimal), farm pen, ambient auto-flying
kites (C++ AKiteActor.bAmbientAutoFly), MPC Wetness wired into ground/road
materials so rain visibly darkens + slicks them.

RUN (auto via init_unreal.py when Saved/village_upgrade_done.txt is missing):
  py "D:/rural_games/rural_pardeep/Scripts/build_upgrade.py"
"""

import json
import math
import os
import random
import re

import unreal

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
MEL = unreal.MaterialEditingLibrary

MAT_DIR = "/Game/Village/Materials"
MPC_PATH = "/Game/Village/MPC_Weather"

CUBE = EAL.load_asset("/Engine/BasicShapes/Cube.Cube")
CYLINDER = EAL.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
SPHERE = EAL.load_asset("/Engine/BasicShapes/Sphere.Sphere")
PLANE = EAL.load_asset("/Engine/BasicShapes/Plane.Plane")
CONE = EAL.load_asset("/Engine/BasicShapes/Cone.Cone")

_WORLD = None
_ZTOP = 150000.0
_ZBOT = -150000.0

# ------------- layout constants (must match build_environment v2) -----------
VILLAGE_CENTER = (0.0, 0.0)
CORE_RADIUS = 16000.0
FIELD_INNER = 19000.0
FIELD_OUTER = 120000.0
FIELD_STEP = (14000.0, 10000.0)
FIELD_MAX_FRACTION = 0.85
RING_RADIUS = 10000.0
ROADS = {
    "main": [(-60000, 20000), (-30000, 17000), (0, 14500), (30000, 12000), (60000, 9500)],
    "side_ne": [(16000, 13300), (28000, -4000), (42000, -18000), (55000, -30000)],
    "ring": [(RING_RADIUS * math.cos(math.radians(a)),
              RING_RADIUS * math.sin(math.radians(a))) for a in range(0, 361, 45)],
    "lane_ns": [(0, 13800), (300, 4000), (-300, -4000), (0, -14000)],
    "lane_ew": [(-14000, 500), (-4000, 200), (4000, -200), (14000, -500)],
    "in_h1": [(-11000, -9000), (-2000, -8600), (9000, -9200)],
    "in_h2": [(-12000, -4500), (-3000, -4800), (11000, -4300)],
    "in_h3": [(-11500, 4500), (0, 4200), (11000, 4800)],
    "in_h4": [(-9000, 9000), (2000, 8700), (10000, 9300)],
    "in_v1": [(-9000, -11000), (-8600, -2000), (-9200, 9000)],
    "in_v2": [(-4500, -12000), (-4800, 0), (-4300, 11000)],
    "in_v3": [(4500, -11500), (4200, 2000), (4800, 11000)],
    "in_v4": [(9000, -10000), (8700, 2000), (9300, 10000)],
    "exit_nw": [(-7500, -7500), (-20000, -20000), (-38000, -33000)],
    "exit_n": [(500, -13800), (2000, -30000), (1000, -48000)],
    "exit_w": [(-13900, 600), (-30000, 2000), (-52000, 2500)],
}
HIGHWAYS = ("main", "side_ne")

CRICKET_CENTER = (-13000.0, 22500.0)
CRICKET_BOUNDARY = 5000.0
PEN_CENTER = (12000.0, 19000.0)
POND_CENTER = (18500.0, 20500.0)

PLASTER_COLORS = [
    ("Tan", (0.85, 0.78, 0.62)),
    ("Cream", (0.92, 0.88, 0.78)),
    ("PaleBlue", (0.65, 0.75, 0.85)),
    ("White", (0.95, 0.95, 0.92)),
]


def log(msg):
    unreal.log("[build_upgrade] {}".format(msg))


def warn(msg):
    unreal.log_warning("[build_upgrade] {}".format(msg))


def ground_z(x, y, default_z=0.0):
    hit = unreal.SystemLibrary.line_trace_single(
        _WORLD, unreal.Vector(x, y, _ZTOP), unreal.Vector(x, y, _ZBOT),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
        unreal.DrawDebugTrace.NONE, True)
    if hit:
        return hit.to_dict()["location"].z
    return default_z


def spawn_mesh(mesh, mi, label, folder, loc, scale, rot=(0.0, 0.0, 0.0)):
    """rot = (pitch, yaw, roll). unreal.Rotator's positional order is
    (roll, pitch, yaw)."""
    actor = EAS.spawn_actor_from_object(
        mesh, loc, unreal.Rotator(rot[2], rot[0], rot[1]))
    actor.set_actor_label(label)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    actor.set_folder_path(folder)
    if mi:
        actor.static_mesh_component.set_material(0, mi)
    return actor


# ------------------------------ materials ----------------------------------

def _expr(mat, cls, x, y):
    return MEL.create_material_expression(mat, cls, x, y)


_MI_CACHE = {}


def flat_parent():
    return EAL.load_asset(MAT_DIR + "/M_VGFlat")


def flat_mi(name, rgb):
    if name in _MI_CACHE:
        return _MI_CACHE[name]
    path = "{}/MI_{}".format(MAT_DIR, name)
    if EAL.does_asset_exist(path):
        inst = EAL.load_asset(path)
    else:
        inst = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "MI_" + name, MAT_DIR, unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew())
        inst.set_editor_property("parent", flat_parent())
        MEL.set_material_instance_vector_parameter_value(
            inst, "Color", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
        MEL.update_material_instance(inst)
        EAL.save_asset(path)
    _MI_CACHE[name] = inst
    return inst


def _wetness_nodes(mat, mpc, x, y):
    """Returns the MPC Wetness scalar expression."""
    wet = _expr(mat, unreal.MaterialExpressionCollectionParameter, x, y)
    wet.set_editor_property("collection", mpc)
    wet.set_editor_property("parameter_name", "Wetness")
    return wet


def make_asphalt_material(mpc):
    path = MAT_DIR + "/M_VGAsphalt"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGAsphalt", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())

    dark = _expr(mat, unreal.MaterialExpressionConstant3Vector, -900, -100)
    dark.set_editor_property("constant", unreal.LinearColor(0.035, 0.035, 0.038, 1.0))
    pale = _expr(mat, unreal.MaterialExpressionConstant3Vector, -900, 60)
    pale.set_editor_property("constant", unreal.LinearColor(0.085, 0.083, 0.080, 1.0))
    noise = _expr(mat, unreal.MaterialExpressionNoise, -900, 220)
    noise.set_editor_property("scale", 0.02)
    noise.set_editor_property("output_min", 0.0)
    noise.set_editor_property("output_max", 1.0)
    col = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -640, 0)
    MEL.connect_material_expressions(dark, "", col, "A")
    MEL.connect_material_expressions(pale, "", col, "B")
    MEL.connect_material_expressions(noise, "", col, "Alpha")

    # rain: darken toward 40% and polish the surface
    wet = _wetness_nodes(mat, mpc, -640, 240)
    wetcol = _expr(mat, unreal.MaterialExpressionMultiply, -420, 60)
    wetk = _expr(mat, unreal.MaterialExpressionConstant, -640, 140)
    wetk.set_editor_property("r", 0.4)
    MEL.connect_material_expressions(col, "", wetcol, "A")
    MEL.connect_material_expressions(wetk, "", wetcol, "B")
    colfinal = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -220, 0)
    MEL.connect_material_expressions(col, "", colfinal, "A")
    MEL.connect_material_expressions(wetcol, "", colfinal, "B")
    MEL.connect_material_expressions(wet, "", colfinal, "Alpha")
    MEL.connect_material_property(colfinal, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rdry = _expr(mat, unreal.MaterialExpressionConstant, -420, 320)
    rdry.set_editor_property("r", 0.82)
    rwet = _expr(mat, unreal.MaterialExpressionConstant, -420, 400)
    rwet.set_editor_property("r", 0.18)
    rough = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -220, 340)
    MEL.connect_material_expressions(rdry, "", rough, "A")
    MEL.connect_material_expressions(rwet, "", rough, "B")
    MEL.connect_material_expressions(wet, "", rough, "Alpha")
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("created M_VGAsphalt")
    return mat


def make_dirtroad_material(mpc):
    path = MAT_DIR + "/M_VGDirtRoad2"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGDirtRoad2", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    packed = _expr(mat, unreal.MaterialExpressionConstant3Vector, -900, -100)
    packed.set_editor_property("constant", unreal.LinearColor(0.34, 0.26, 0.17, 1.0))
    dust = _expr(mat, unreal.MaterialExpressionConstant3Vector, -900, 60)
    dust.set_editor_property("constant", unreal.LinearColor(0.46, 0.38, 0.26, 1.0))
    noise = _expr(mat, unreal.MaterialExpressionNoise, -900, 220)
    noise.set_editor_property("scale", 0.008)
    noise.set_editor_property("turbulence", True)
    noise.set_editor_property("output_min", 0.0)
    noise.set_editor_property("output_max", 1.0)
    col = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -640, 0)
    MEL.connect_material_expressions(packed, "", col, "A")
    MEL.connect_material_expressions(dust, "", col, "B")
    MEL.connect_material_expressions(noise, "", col, "Alpha")

    wet = _wetness_nodes(mat, mpc, -640, 240)
    mud = _expr(mat, unreal.MaterialExpressionMultiply, -420, 60)
    mudk = _expr(mat, unreal.MaterialExpressionConstant, -640, 140)
    mudk.set_editor_property("r", 0.45)
    MEL.connect_material_expressions(col, "", mud, "A")
    MEL.connect_material_expressions(mudk, "", mud, "B")
    colfinal = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -220, 0)
    MEL.connect_material_expressions(col, "", colfinal, "A")
    MEL.connect_material_expressions(mud, "", colfinal, "B")
    MEL.connect_material_expressions(wet, "", colfinal, "Alpha")
    MEL.connect_material_property(colfinal, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rdry = _expr(mat, unreal.MaterialExpressionConstant, -420, 320)
    rdry.set_editor_property("r", 0.95)
    rwet = _expr(mat, unreal.MaterialExpressionConstant, -420, 400)
    rwet.set_editor_property("r", 0.35)
    rough = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -220, 340)
    MEL.connect_material_expressions(rdry, "", rough, "A")
    MEL.connect_material_expressions(rwet, "", rough, "B")
    MEL.connect_material_expressions(wet, "", rough, "Alpha")
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("created M_VGDirtRoad2")
    return mat


def make_field_materials():
    """4 crop palettes x 2 row directions = 8 shared field materials."""
    palettes = [
        ("Wheat", (0.62, 0.52, 0.22), (0.50, 0.40, 0.17)),
        ("Green", (0.28, 0.44, 0.15), (0.20, 0.34, 0.11)),
        ("Deep", (0.18, 0.33, 0.11), (0.13, 0.26, 0.09)),
        ("Tilled", (0.40, 0.30, 0.19), (0.30, 0.22, 0.14)),
    ]
    directions = [("A", (0.010, 0.0017)), ("B", (0.0021, 0.011))]
    mats = []
    for pname, hi, lo in palettes:
        for dname, (dx, dy) in directions:
            path = "{}/M_VGField{}{}".format(MAT_DIR, pname, dname)
            if EAL.does_asset_exist(path):
                mats.append(EAL.load_asset(path))
                continue
            mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                "M_VGField{}{}".format(pname, dname), MAT_DIR,
                unreal.Material, unreal.MaterialFactoryNew())
            chi = _expr(mat, unreal.MaterialExpressionConstant3Vector, -900, -120)
            chi.set_editor_property("constant", unreal.LinearColor(hi[0], hi[1], hi[2], 1.0))
            clo = _expr(mat, unreal.MaterialExpressionConstant3Vector, -900, 40)
            clo.set_editor_property("constant", unreal.LinearColor(lo[0], lo[1], lo[2], 1.0))

            wp = _expr(mat, unreal.MaterialExpressionWorldPosition, -1200, 260)
            mask = _expr(mat, unreal.MaterialExpressionComponentMask, -1020, 260)
            mask.set_editor_property("r", True); mask.set_editor_property("g", True)
            mask.set_editor_property("b", False); mask.set_editor_property("a", False)
            MEL.connect_material_expressions(wp, "", mask, "")
            rowdir = _expr(mat, unreal.MaterialExpressionConstant2Vector, -1020, 380)
            rowdir.set_editor_property("r", dx); rowdir.set_editor_property("g", dy)
            dot = _expr(mat, unreal.MaterialExpressionDotProduct, -860, 300)
            MEL.connect_material_expressions(mask, "", dot, "A")
            MEL.connect_material_expressions(rowdir, "", dot, "B")
            s = _expr(mat, unreal.MaterialExpressionSine, -720, 300)
            MEL.connect_material_expressions(dot, "", s, "")
            half = _expr(mat, unreal.MaterialExpressionMultiply, -580, 300)
            hc = _expr(mat, unreal.MaterialExpressionConstant, -720, 400)
            hc.set_editor_property("r", 0.5)
            MEL.connect_material_expressions(s, "", half, "A")
            MEL.connect_material_expressions(hc, "", half, "B")
            rows = _expr(mat, unreal.MaterialExpressionAdd, -440, 300)
            MEL.connect_material_expressions(half, "", rows, "A")
            MEL.connect_material_expressions(hc, "", rows, "B")

            # large soft patchiness on top of the rows
            pnoise = _expr(mat, unreal.MaterialExpressionNoise, -580, 460)
            pnoise.set_editor_property("scale", 0.0006)
            pnoise.set_editor_property("output_min", 0.35)
            pnoise.set_editor_property("output_max", 1.0)
            mixa = _expr(mat, unreal.MaterialExpressionMultiply, -300, 340)
            MEL.connect_material_expressions(rows, "", mixa, "A")
            MEL.connect_material_expressions(pnoise, "", mixa, "B")

            col = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -160, 0)
            MEL.connect_material_expressions(clo, "", col, "A")
            MEL.connect_material_expressions(chi, "", col, "B")
            MEL.connect_material_expressions(mixa, "", col, "Alpha")
            MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)

            rough = _expr(mat, unreal.MaterialExpressionConstant, -160, 200)
            rough.set_editor_property("r", 0.9)
            MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
            MEL.recompile_material(mat)
            EAL.save_asset(path)
            mats.append(mat)
    log("field materials ready ({})".format(len(mats)))
    return mats


def make_bulb_material():
    path = MAT_DIR + "/M_VGBulb"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGBulb", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    warm = _expr(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    warm.set_editor_property("constant", unreal.LinearColor(1.0, 0.75, 0.42, 1.0))
    gain = _expr(mat, unreal.MaterialExpressionConstant, -400, 160)
    gain.set_editor_property("r", 14.0)
    emis = _expr(mat, unreal.MaterialExpressionMultiply, -220, 60)
    MEL.connect_material_expressions(warm, "", emis, "A")
    MEL.connect_material_expressions(gain, "", emis, "B")
    MEL.connect_material_property(emis, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    return mat


def build_wind_wpo(mat, mpc, amp_cm, height_range_cm, x0=-1400, y0=600):
    """Height-masked MPC-driven sway (same recipe as build_extras)."""
    wp = _expr(mat, unreal.MaterialExpressionWorldPosition, x0, y0)
    objpos = _expr(mat, unreal.MaterialExpressionObjectPositionWS, x0, y0 + 220)
    time = _expr(mat, unreal.MaterialExpressionTime, x0, y0 + 420)

    mask_x = _expr(mat, unreal.MaterialExpressionComponentMask, x0 + 180, y0)
    mask_x.set_editor_property("r", True); mask_x.set_editor_property("g", True)
    mask_x.set_editor_property("b", False); mask_x.set_editor_property("a", False)
    MEL.connect_material_expressions(wp, "", mask_x, "")
    dot1 = _expr(mat, unreal.MaterialExpressionDotProduct, x0 + 360, y0)
    ones = _expr(mat, unreal.MaterialExpressionConstant2Vector, x0 + 180, y0 + 90)
    ones.set_editor_property("r", 0.0012); ones.set_editor_property("g", 0.0009)
    MEL.connect_material_expressions(mask_x, "", dot1, "A")
    MEL.connect_material_expressions(ones, "", dot1, "B")
    tspeed = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 360, y0 + 420)
    tconst = _expr(mat, unreal.MaterialExpressionConstant, x0 + 180, y0 + 520)
    tconst.set_editor_property("r", 0.45)
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
    hrange.set_editor_property("r", height_range_cm)
    MEL.connect_material_expressions(hz, "", hdiv, "A")
    MEL.connect_material_expressions(hrange, "", hdiv, "B")
    hclamp = _expr(mat, unreal.MaterialExpressionClamp, x0 + 720, y0 + 640)
    MEL.connect_material_expressions(hdiv, "", hclamp, "")

    wind = _expr(mat, unreal.MaterialExpressionCollectionParameter, x0 + 720, y0 + 420)
    wind.set_editor_property("collection", mpc)
    wind.set_editor_property("parameter_name", "WindIntensity")
    amp = _expr(mat, unreal.MaterialExpressionConstant, x0 + 720, y0 + 520)
    amp.set_editor_property("r", amp_cm)
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


def make_canopy_parent(mpc):
    """Parameterised foliage: Color param + subsurface-ish depth + wind WPO."""
    path = MAT_DIR + "/M_VGCanopyP"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGCanopyP", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    colour = _expr(mat, unreal.MaterialExpressionVectorParameter, -700, -100)
    colour.set_editor_property("parameter_name", "Color")
    colour.set_editor_property("default_value", unreal.LinearColor(0.20, 0.35, 0.12, 1.0))
    # leaf clumping: high-frequency noise multiplies the base tone
    noise = _expr(mat, unreal.MaterialExpressionNoise, -700, 120)
    noise.set_editor_property("scale", 0.03)
    noise.set_editor_property("output_min", 0.55)
    noise.set_editor_property("output_max", 1.15)
    col = _expr(mat, unreal.MaterialExpressionMultiply, -420, 0)
    MEL.connect_material_expressions(colour, "", col, "A")
    MEL.connect_material_expressions(noise, "", col, "B")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = _expr(mat, unreal.MaterialExpressionConstant, -420, 200)
    rough.set_editor_property("r", 0.78)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    build_wind_wpo(mat, mpc, amp_cm=48.0, height_range_cm=450.0)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("created M_VGCanopyP")
    return mat


def canopy_mi(parent, name, rgb):
    key = "Canopy" + name
    if key in _MI_CACHE:
        return _MI_CACHE[key]
    path = "{}/MI_{}".format(MAT_DIR, key)
    if EAL.does_asset_exist(path):
        inst = EAL.load_asset(path)
    else:
        inst = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "MI_" + key, MAT_DIR, unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew())
        inst.set_editor_property("parent", parent)
        MEL.set_material_instance_vector_parameter_value(
            inst, "Color", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
        MEL.update_material_instance(inst)
        EAL.save_asset(path)
    _MI_CACHE[key] = inst
    return inst


def rewire_ground_wetness(mpc):
    """Rebuild M_VillageGround's colour/roughness chains with a Wetness mix.
    Modifies the asset in place (it's referenced by the landscape, so it can't
    be deleted); old orphaned nodes are left disconnected — harmless."""
    path = MAT_DIR + "/M_VillageGround"
    if not EAL.does_asset_exist(path):
        warn("M_VillageGround missing — wetness wiring skipped")
        return
    mat = EAL.load_asset(path)
    try:
        if EAL.get_metadata_tag(mat, "vg3_wet") == "1":
            return
    except Exception:
        pass

    grass = _expr(mat, unreal.MaterialExpressionConstant3Vector, -700, 1400)
    grass.set_editor_property("constant", unreal.LinearColor(0.30, 0.38, 0.14, 1.0))
    dirt = _expr(mat, unreal.MaterialExpressionConstant3Vector, -700, 1560)
    dirt.set_editor_property("constant", unreal.LinearColor(0.43, 0.33, 0.21, 1.0))
    cnoise = _expr(mat, unreal.MaterialExpressionNoise, -700, 1720)
    cnoise.set_editor_property("scale", 0.00035)
    cnoise.set_editor_property("turbulence", True)
    cnoise.set_editor_property("output_min", 0.0)
    cnoise.set_editor_property("output_max", 1.0)
    lerp = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -420, 1500)
    MEL.connect_material_expressions(grass, "", lerp, "A")
    MEL.connect_material_expressions(dirt, "", lerp, "B")
    MEL.connect_material_expressions(cnoise, "", lerp, "Alpha")

    wet = _wetness_nodes(mat, mpc, -420, 1700)
    darkm = _expr(mat, unreal.MaterialExpressionMultiply, -220, 1560)
    dk = _expr(mat, unreal.MaterialExpressionConstant, -420, 1620)
    dk.set_editor_property("r", 0.45)
    MEL.connect_material_expressions(lerp, "", darkm, "A")
    MEL.connect_material_expressions(dk, "", darkm, "B")
    colfinal = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -40, 1500)
    MEL.connect_material_expressions(lerp, "", colfinal, "A")
    MEL.connect_material_expressions(darkm, "", colfinal, "B")
    MEL.connect_material_expressions(wet, "", colfinal, "Alpha")
    MEL.connect_material_property(colfinal, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rlo = _expr(mat, unreal.MaterialExpressionConstant, -700, 1900)
    rlo.set_editor_property("r", 0.55)
    rhi = _expr(mat, unreal.MaterialExpressionConstant, -700, 1980)
    rhi.set_editor_property("r", 0.95)
    rnoise = _expr(mat, unreal.MaterialExpressionNoise, -700, 2080)
    rnoise.set_editor_property("scale", 0.0011)
    rnoise.set_editor_property("output_min", 0.0)
    rnoise.set_editor_property("output_max", 1.0)
    rlerp = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -420, 1960)
    MEL.connect_material_expressions(rlo, "", rlerp, "A")
    MEL.connect_material_expressions(rhi, "", rlerp, "B")
    MEL.connect_material_expressions(rnoise, "", rlerp, "Alpha")
    rwet = _expr(mat, unreal.MaterialExpressionConstant, -420, 2100)
    rwet.set_editor_property("r", 0.22)
    rfinal = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -40, 1980)
    MEL.connect_material_expressions(rlerp, "", rfinal, "A")
    MEL.connect_material_expressions(rwet, "", rfinal, "B")
    MEL.connect_material_expressions(wet, "", rfinal, "Alpha")
    MEL.connect_material_property(rfinal, "", unreal.MaterialProperty.MP_ROUGHNESS)

    try:
        EAL.set_metadata_tag(mat, "vg3_wet", "1")
    except Exception:
        pass
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("M_VillageGround: wetness wired in")


# ------------------------------- cleanup -----------------------------------

# VGX_Mountain_: every photogrammetry scan ring placement shredded or floated —
# the rolling landscape + height fog carry the horizon better on the plains.
# VGX_City_: the skyline hung in mid-air at the landscape edge (trace miss) and
# read as a hovering ship over a Punjabi village; removed rather than re-grounded.
REBUILD_PREFIXES = ("VG3_", "VG_Road_", "VG_DirtRoad_", "VG_Tree_", "VG_Field_",
                    "VGX_Mountain_", "VGX_City_")


PLOTS_SIDECAR = os.path.join(unreal.Paths.project_saved_dir(),
                             "village_house_plots.json")


def derive_original_plots():
    """Replay build_environment v2's exact RNG sequence (Random(11), same
    draw order) to recover the original house plots when neither house actors
    nor the sidecar file survive. Keeps NPC home spots aligned."""
    rng = random.Random(11)
    house_paths = [ROADS["ring"], ROADS["lane_ns"], ROADS["lane_ew"],
                   ROADS["in_h1"], ROADS["in_h2"], ROADS["in_h3"], ROADS["in_h4"],
                   ROADS["in_v1"], ROADS["in_v2"], ROADS["in_v3"], ROADS["in_v4"]]
    road_pts = []
    for pts in ROADS.values():
        road_pts.extend(road_samples(pts))
    plots_xy, gen, arch_n = [], [], 0
    for path in house_paths:
        for (x, y) in road_samples(path, step=2600.0):
            if len(plots_xy) >= 48:      # HOUSE_COUNT_CAP
                break
            side = 1 if rng.random() < 0.5 else -1
            hx = x + side * rng.uniform(950, 1500)
            hy = y + side * rng.uniform(950, 1500)
            if math.hypot(hx, hy) > CORE_RADIUS:
                continue
            if any(math.hypot(hx - px, hy - py) < 1700 for px, py in plots_xy):
                continue
            if any(math.hypot(hx - rx, hy - ry) < 950 for rx, ry in road_pts):
                continue
            plots_xy.append((hx, hy))
            yaw = math.degrees(math.atan2(y - hy, x - hx)) + 90.0
            idx = len(plots_xy)
            if rng.random() < 0.55:      # arch house branch (meshes existed)
                rng.uniform(800, 1150)   # consumed by spawn width
                arch_n += 1
            else:
                w = rng.uniform(650, 1200)
                d = rng.uniform(550, 950)
                storeys = 1 if rng.random() < 0.55 else 2
                gen.append((hx, hy, yaw, w, d, storeys, idx))
    log("replayed original plot RNG: {} generated + {} arch".format(
        len(gen), arch_n))
    return gen


def collect_house_plots():
    """(x, y, yaw, w, d, storeys, idx) for every generated house, plus arch
    house positions (kept as-is). Sources, in order: v2 VG_House_NN blocks ->
    VG3 hollow-house walls (re-runs) -> sidecar JSON -> RNG replay."""
    plots, arch = [], []
    pat = re.compile(r"^VG_House_(\d+)$")
    pat_arch = re.compile(r"^VG_House_(\d+)_arch")
    pat3b = re.compile(r"^VG3_House_(\d+)_back$")
    pat3r = re.compile(r"^VG3_House_(\d+)_right$")
    pat3u = re.compile(r"^VG3_House_(\d+)_up$")
    backs, rights, ups = {}, {}, set()
    for actor in EAS.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue
        m = pat.match(label)
        if m:
            loc = actor.get_actor_location()
            rot = actor.get_actor_rotation()
            scale = actor.get_actor_scale3d()
            storeys = 2 if scale.z * 100.0 > 350.0 else 1
            plots.append((loc.x, loc.y, rot.yaw, scale.x * 100.0, scale.y * 100.0,
                          storeys, int(m.group(1))))
        elif pat_arch.match(label):
            loc = actor.get_actor_location()
            arch.append((loc.x, loc.y))
        elif pat3b.match(label):
            backs[int(pat3b.match(label).group(1))] = actor
        elif pat3r.match(label):
            rights[int(pat3r.match(label).group(1))] = actor
        elif pat3u.match(label):
            ups.add(int(pat3u.match(label).group(1)))
    if not plots and backs:
        # reconstruct centre + dims from the back wall (offset d/2 - t/2
        # along local +Y) and the right wall (spans d - 2t)
        for idx, a in backs.items():
            loc = a.get_actor_location()
            yaw = a.get_actor_rotation().yaw
            w = a.get_actor_scale3d().x * 100.0
            d = rights[idx].get_actor_scale3d().y * 100.0 + 28.0 if idx in rights else 800.0
            off = d / 2.0 - 7.0
            r = math.radians(yaw)
            plots.append((loc.x + off * math.sin(r), loc.y - off * math.cos(r),
                          yaw, w, d, 2 if idx in ups else 1, idx))
        log("plots recovered from {} VG3 hollow houses".format(len(plots)))
    if not plots and os.path.exists(PLOTS_SIDECAR):
        try:
            with open(PLOTS_SIDECAR, "r") as f:
                plots = [tuple(p) for p in json.load(f)]
            log("plots loaded from sidecar ({})".format(len(plots)))
        except Exception as e:
            warn("sidecar load failed: {}".format(e))
    if not plots:
        plots = derive_original_plots()
    if plots:
        try:
            with open(PLOTS_SIDECAR, "w") as f:
                json.dump([list(p) for p in plots], f)
        except Exception as e:
            warn("sidecar write failed: {}".format(e))
    log("collected {} generated house plots, {} arch houses".format(
        len(plots), len(arch)))
    return plots, arch


def cleanup_previous():
    removed = 0
    for actor in EAS.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue
        if "_arch" in label:
            continue
        if any(label.startswith(p) for p in REBUILD_PREFIXES) or \
           (label.startswith("VG_House_")):
            EAS.destroy_actor(actor)
            removed += 1
    log("cleanup removed {} actors".format(removed))


# ------------------------------- roads v3 ----------------------------------

def road_class():
    cls = getattr(unreal, "RoadSpline", None)
    if cls is None:
        cls = unreal.load_class(None, "/Script/rural_pardeep.RoadSpline")
    return cls


def conformed_segment(mesh, mi, label, folder, x, y, yaw_deg, length, width,
                      thickness=0.05, lift=2.0):
    """Spawn one road slab pitched+rolled onto the terrain.

    Robust to bad traces (a sample that hits a tree canopy, river ribbon or
    nothing at all): outliers >450 cm from the median are discarded, and any
    axis that lost a sample goes flat instead of spiking into the sky."""
    r = math.radians(yaw_deg)
    fx, fy = math.cos(r), math.sin(r)
    px, py = -fy, fx
    half_l = length * 0.5
    half_w = width * 0.5
    gz_f = ground_z(x + fx * half_l, y + fy * half_l)
    gz_b = ground_z(x - fx * half_l, y - fy * half_l)
    gz_r = ground_z(x + px * half_w, y + py * half_w)
    gz_l = ground_z(x - px * half_w, y - py * half_w)
    gz_c = ground_z(x, y)
    samples = sorted((gz_f, gz_b, gz_r, gz_l, gz_c))
    med = samples[2]
    ok = lambda s: abs(s - med) <= 450.0
    pitch = math.degrees(math.atan2(gz_f - gz_b, length)) if ok(gz_f) and ok(gz_b) else 0.0
    roll = math.degrees(math.atan2(gz_r - gz_l, width)) if ok(gz_r) and ok(gz_l) else 0.0
    pitch = max(-10.0, min(10.0, pitch))
    roll = max(-7.0, min(7.0, roll))
    kept = [s for s in samples if ok(s)]
    z = sum(kept) / len(kept) + lift
    return spawn_mesh(mesh, mi, label, folder,
                      unreal.Vector(x, y, z),
                      (length / 100.0, width / 100.0, thickness),
                      (pitch, yaw_deg, roll)), pitch, roll, z


def build_road_v3(name, points_2d, is_highway, mi_asphalt, mi_dirt, mi_line):
    pts = [unreal.Vector(x, y, ground_z(x, y) + 10.0) for x, y in points_2d]
    road = EAS.spawn_actor_from_class(road_class(), pts[0], unreal.Rotator(0, 0, 0))
    road.set_actor_label("VG3_RoadSpline_" + name)
    road.set_folder_path("Village/Roads")
    spline = road.get_component_by_class(unreal.SplineComponent)
    spline.clear_spline_points(True)
    for p in pts:
        spline.add_spline_point(p, unreal.SplineCoordinateSpace.WORLD, True)

    seg_len = 900.0 if is_highway else 950.0
    spacing = 780.0 if is_highway else 840.0
    width = 640.0 if is_highway else 430.0
    mi = mi_asphalt if is_highway else mi_dirt
    folder = "Village/Roads/Segments"

    length = spline.get_spline_length()
    dist, count = 0.0, 0
    while dist <= length:
        loc = spline.get_location_at_distance_along_spline(
            dist, unreal.SplineCoordinateSpace.WORLD)
        rot = spline.get_rotation_at_distance_along_spline(
            dist, unreal.SplineCoordinateSpace.WORLD)
        seg, pitch, roll, z = conformed_segment(
            CUBE, mi, "VG3_Road_{}_{:03d}".format(name, count), folder,
            loc.x, loc.y, rot.yaw, seg_len * 1.16, width)
        if is_highway:
            # edge lines (continuous) + centre dashes (every other segment)
            r = math.radians(rot.yaw)
            px, py = -math.sin(r), math.cos(r)
            for side, tag in ((1.0, "R"), (-1.0, "L")):
                ex = loc.x + px * side * (width / 2.0 - 28.0)
                ey = loc.y + py * side * (width / 2.0 - 28.0)
                spawn_mesh(CUBE, mi_line,
                           "VG3_RoadLine_{}_{:03d}{}".format(name, count, tag),
                           folder, unreal.Vector(ex, ey, z + 2.5),
                           (seg_len * 1.16 / 100.0, 0.13, 0.015),
                           (pitch, rot.yaw, roll))
            if count % 2 == 0:
                spawn_mesh(CUBE, mi_line,
                           "VG3_RoadDash_{}_{:03d}".format(name, count),
                           folder, unreal.Vector(loc.x, loc.y, z + 2.5),
                           (3.2, 0.16, 0.015), (pitch, rot.yaw, roll))
        dist += spacing
        count += 1
    return count


def build_all_roads(mpc):
    mi_asphalt = make_asphalt_material(mpc)
    mi_dirt = make_dirtroad_material(mpc)
    mi_line = flat_mi("RoadLine", (0.85, 0.85, 0.80))
    total = 0
    for name, pts in ROADS.items():
        total += build_road_v3(name, pts, name in HIGHWAYS,
                               mi_asphalt, mi_dirt, mi_line)
    log("roads v3: {} segments ({} highways)".format(total, len(HIGHWAYS)))


def road_samples(points_2d, step=1000.0):
    samples = []
    for (x1, y1), (x2, y2) in zip(points_2d, points_2d[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        n = max(2, int(seg / step))
        for i in range(n):
            t = i / float(n)
            samples.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
    return samples


# ------------------------------- fields v3 ----------------------------------

def landscape_half_extent():
    proxies = [a for a in EAS.get_all_level_actors()
               if isinstance(a, unreal.LandscapeProxy)]
    if not proxies:
        return 60000.0, 60000.0
    boxes = [p.get_actor_bounds(False) for p in proxies]
    min_x = min(o.x - e.x for o, e in boxes)
    max_x = max(o.x + e.x for o, e in boxes)
    min_y = min(o.y - e.y for o, e in boxes)
    max_y = max(o.y + e.y for o, e in boxes)
    return (max_x - min_x) / 2.0, (max_y - min_y) / 2.0


def build_fields_v3(field_mats, road_pts, rng):
    mi_bund = flat_mi("Bund", (0.33, 0.25, 0.16))
    exclusions = [
        (CRICKET_CENTER, CRICKET_BOUNDARY + 3200.0),
        (PEN_CENTER, 3600.0),
        (POND_CENTER, 5200.0),
        ((19500.0, 11000.0), 2600.0),   # kancha playground
    ]
    ext_x, ext_y = landscape_half_extent()
    span_x = min(FIELD_OUTER, ext_x * FIELD_MAX_FRACTION)
    span_y = min(FIELD_OUTER, ext_y * FIELD_MAX_FRACTION)
    count, bunds = 0, 0
    idx = 0
    span = max(span_x, span_y)
    x = -span_x
    while x <= span_x:
        y = -span_y
        while y <= span_y:
            idx += 1
            dist_core = math.hypot(x, y)
            if dist_core <= FIELD_INNER or dist_core > span:
                y += FIELD_STEP[1]
                continue
            if any(math.hypot(px - x, py - y) < 2200 for px, py in road_pts):
                y += FIELD_STEP[1]
                continue
            if any(math.hypot(ex - x, ey - y) < er for (ex, ey), er in exclusions):
                y += FIELD_STEP[1]
                continue

            hw = FIELD_STEP[0] / 2.0 - 600.0
            hh = FIELD_STEP[1] / 2.0 - 500.0
            gz_c = ground_z(x, y)
            gz_e = ground_z(x + hw, y)
            gz_w = ground_z(x - hw, y)
            gz_n = ground_z(x, y - hh)
            gz_s = ground_z(x, y + hh)
            pitch = math.degrees(math.atan2(gz_e - gz_w, hw * 2.0))
            roll = math.degrees(math.atan2(gz_s - gz_n, hh * 2.0))
            if abs(pitch) > 16.0 or abs(roll) > 16.0:
                y += FIELD_STEP[1]   # too steep — let the hillside stay natural
                continue
            mat = field_mats[idx % len(field_mats)]
            spawn_mesh(PLANE, mat, "VG3_Field_{:03d}".format(idx), "Village/Fields",
                       unreal.Vector(x, y, gz_c + 4.0),
                       (hw * 2.0 / 100.0, hh * 2.0 / 100.0, 1.0),
                       (pitch, 0.0, roll))
            count += 1
            # dirt bunds on the two X edges of nearer fields
            if dist_core < 62000.0:
                for side in (-1.0, 1.0):
                    bx = x + side * hw
                    bz = ground_z(bx, y)
                    spawn_mesh(CUBE, mi_bund, "VG3_Bund_{:03d}{}".format(
                        idx, "E" if side > 0 else "W"), "Village/Fields",
                        unreal.Vector(bx, y, bz + 7.0),
                        (0.8, hh * 2.0 / 100.0, 0.14), (0.0, 0.0, roll))
                    bunds += 1
            y += FIELD_STEP[1]
        x += FIELD_STEP[0]
    log("fields v3: {} patches, {} bunds".format(count, bunds))


# ------------------------------- trees v3 ----------------------------------

TREE_SPECIES = {
    #            trunk_h  trunk_r  canopy_r  lobes  tone
    "Peepal": (620.0, 0.62, 5.6, 5, "PeepalGreen"),
    "Neem":   (480.0, 0.44, 4.1, 4, "NeemGreen"),
    "Mango":  (380.0, 0.55, 4.6, 5, "MangoGreen"),
    "Kikar":  (430.0, 0.36, 3.2, 3, "KikarOlive"),
}
TREE_TONES = {
    "PeepalGreen": (0.16, 0.30, 0.10),
    "NeemGreen": (0.20, 0.36, 0.12),
    "MangoGreen": (0.12, 0.25, 0.08),
    "KikarOlive": (0.27, 0.30, 0.11),
}


def build_tree(idx, x, y, species, canopy_parent, rng):
    trunk_h, trunk_r, canopy_r, lobes, tone = TREE_SPECIES[species]
    trunk_h *= rng.uniform(0.85, 1.2)
    canopy_r *= rng.uniform(0.85, 1.15)
    gz = ground_z(x, y)
    folder = "Village/Trees"
    label = "VG3_Tree_{:03d}".format(idx)
    bark = flat_mi("Bark", (0.30, 0.21, 0.12))
    leaf = canopy_mi(canopy_parent, tone, TREE_TONES[tone])

    # tapered trunk: broad base + narrower upper section
    spawn_mesh(CYLINDER, bark, label + "_T0", folder,
               unreal.Vector(x, y, gz + trunk_h * 0.28),
               (trunk_r, trunk_r, trunk_h * 0.56 / 100.0))
    spawn_mesh(CYLINDER, bark, label + "_T1", folder,
               unreal.Vector(x, y, gz + trunk_h * 0.74),
               (trunk_r * 0.64, trunk_r * 0.64, trunk_h * 0.52 / 100.0))
    # 2 angled branches into the crown
    for b in range(2):
        a = rng.uniform(0, 2 * math.pi)
        tilt = rng.uniform(28, 46)
        bx = x + math.cos(a) * trunk_r * 30
        by = y + math.sin(a) * trunk_r * 30
        spawn_mesh(CYLINDER, bark, "{}_B{}".format(label, b), folder,
                   unreal.Vector(bx, by, gz + trunk_h * 0.95),
                   (trunk_r * 0.34, trunk_r * 0.34, trunk_h * 0.42 / 100.0),
                   (tilt * math.cos(a), math.degrees(a), tilt * math.sin(a)))
    # canopy: one crown + offset lobes, squashed spheres
    base_z = gz + trunk_h + canopy_r * 42.0
    spawn_mesh(SPHERE, leaf, label + "_C0", folder,
               unreal.Vector(x, y, base_z),
               (canopy_r, canopy_r, canopy_r * 0.72))
    for l in range(lobes):
        a = rng.uniform(0, 2 * math.pi)
        rr = canopy_r * rng.uniform(28.0, 52.0)
        lz = base_z + rng.uniform(-canopy_r * 26.0, canopy_r * 30.0)
        s = canopy_r * rng.uniform(0.45, 0.7)
        spawn_mesh(SPHERE, leaf, "{}_C{}".format(label, l + 1), folder,
                   unreal.Vector(x + math.cos(a) * rr, y + math.sin(a) * rr, lz),
                   (s, s, s * 0.78))


def build_trees_v3(canopy_parent, road_pts, plots, rng):
    species_cycle = ["Neem", "Peepal", "Mango", "Kikar", "Neem", "Kikar", "Mango"]
    idx = 0
    placed = []

    def ok(x, y, min_d=1500.0):
        if math.hypot(x - CRICKET_CENTER[0], y - CRICKET_CENTER[1]) < CRICKET_BOUNDARY + 900:
            return False
        if math.hypot(x - PEN_CENTER[0], y - PEN_CENTER[1]) < 2900:
            return False
        if any(math.hypot(x - rx, y - ry) < 780 for rx, ry in road_pts):
            return False
        if any(math.hypot(x - tx, y - ty) < min_d for tx, ty in placed):
            return False
        return True

    # roadside avenue
    for i, (rx, ry) in enumerate(road_pts):
        if i % 6 != 0:
            continue
        side = 1 if (i // 6) % 2 == 0 else -1
        x = rx + side * rng.uniform(750, 1150)
        y = ry + side * rng.uniform(-420, 420)
        if not ok(x, y):
            continue
        build_tree(idx, x, y, species_cycle[idx % len(species_cycle)],
                   canopy_parent, rng)
        placed.append((x, y))
        idx += 1

    # courtyard trees near houses
    for (hx, hy, yaw, w, d, st, hidx) in plots[::3]:
        a = rng.uniform(0, 2 * math.pi)
        x = hx + math.cos(a) * rng.uniform(900, 1400)
        y = hy + math.sin(a) * rng.uniform(900, 1400)
        if not ok(x, y, min_d=1100.0):
            continue
        build_tree(idx, x, y, "Neem" if idx % 2 else "Mango", canopy_parent, rng)
        placed.append((x, y))
        idx += 1

    # pond bank cluster + school + cricket shade
    for (cx, cy, n, r0) in ((POND_CENTER[0], POND_CENTER[1], 5, 3600.0),
                            (22000.0, 8800.0, 3, 1800.0),
                            (CRICKET_CENTER[0], CRICKET_CENTER[1], 4,
                             CRICKET_BOUNDARY + 1500.0)):
        for _ in range(n):
            a = rng.uniform(0, 2 * math.pi)
            x = cx + math.cos(a) * r0 * rng.uniform(0.95, 1.25)
            y = cy + math.sin(a) * r0 * rng.uniform(0.95, 1.25)
            if not ok(x, y, min_d=900.0):
                continue
            build_tree(idx, x, y, "Peepal" if idx % 3 == 0 else "Neem",
                       canopy_parent, rng)
            placed.append((x, y))
            idx += 1

    # field-bund tree lines
    span = 56000.0
    fx = -span
    fi = 0
    while fx <= span:
        fy = -span
        while fy <= span:
            fi += 1
            if fi % 3 == 0 and math.hypot(fx, fy) > FIELD_INNER + 2500:
                ex = fx + FIELD_STEP[0] / 2.0 - 600.0
                for k in range(3):
                    y = fy + (k - 1) * 2600.0
                    if not ok(ex, y, min_d=1200.0):
                        continue
                    build_tree(idx, ex, y, "Kikar" if k % 2 else "Neem",
                               canopy_parent, rng)
                    placed.append((ex, y))
                    idx += 1
            fy += FIELD_STEP[1]
        fx += FIELD_STEP[0]

    log("trees v3: {} planted".format(idx))


# --------------------------- hollow houses v3 -------------------------------

def build_house_v3(plot, bulb_mat, rng):
    x, y, yaw, w, d, storeys, idx = plot
    w = max(w, 760.0)
    d = max(d, 640.0)
    h = storeys * 300.0
    t = 14.0
    gz = ground_z(x, y)
    name, rgb = PLASTER_COLORS[idx % len(PLASTER_COLORS)]
    mi = flat_mi("Plaster" + name, rgb)
    mi_in = flat_mi("PlasterInner", (0.90, 0.86, 0.76))
    dark = flat_mi("DarkWood", (0.16, 0.11, 0.08))
    steel = flat_mi("TankSteel", (0.55, 0.58, 0.62))
    jute = flat_mi("Jute", (0.72, 0.60, 0.38))
    clay = flat_mi("Clay", (0.55, 0.35, 0.22))
    terra = flat_mi("Terracotta", (0.62, 0.33, 0.18))
    folder = "Village/Houses"
    label = "VG3_House_{:02d}".format(idx)

    def local(lx, ly, lz):
        r = math.radians(yaw)
        return unreal.Vector(x + lx * math.cos(r) - ly * math.sin(r),
                             y + lx * math.sin(r) + ly * math.cos(r), gz + lz)

    def part(mesh, m, suffix, lx, ly, lz, scale, extra_yaw=0.0, pitch=0.0):
        return spawn_mesh(mesh, m, label + suffix, folder, local(lx, ly, lz),
                          scale, (pitch, yaw + extra_yaw, 0.0))

    fh = 300.0            # interior storey height
    # 150 cm doorway: twice the character capsule, so entry is effortless
    door_w, door_h = 150.0, 220.0

    # plinth apron (slim lip) + interior floor
    part(CUBE, mi, "_plinth", 0, 0, 15, ((w + 40) / 100, (d + 40) / 100, 0.3))
    part(CUBE, clay, "_floor", 0, 0, 32, ((w - 2 * t) / 100, (d - 2 * t) / 100, 0.06))

    z0 = 30.0             # top of plinth = interior floor level

    # FRONT (-Y): two columns + lintel leave a real doorway
    col_w = (w - door_w) / 2.0
    part(CUBE, mi, "_fL", -(door_w / 2 + col_w / 2), -d / 2 + t / 2, z0 + fh / 2,
         (col_w / 100, t / 100, fh / 100))
    part(CUBE, mi, "_fR", (door_w / 2 + col_w / 2), -d / 2 + t / 2, z0 + fh / 2,
         (col_w / 100, t / 100, fh / 100))
    part(CUBE, mi, "_fLintel", 0, -d / 2 + t / 2, z0 + door_h + (fh - door_h) / 2,
         (door_w / 100, t / 100, (fh - door_h) / 100))
    # door leaf parked fully open, flat against the inside face of the left
    # column — completely clear of the opening
    part(CUBE, dark, "_doorleaf", -door_w / 2 - 62, -d / 2 + t + 12, z0 + door_h / 2 - 2,
         (1.15, 0.05, (door_h - 8) / 100))

    # BACK + RIGHT solid; LEFT gets a real window
    part(CUBE, mi, "_back", 0, d / 2 - t / 2, z0 + fh / 2, (w / 100, t / 100, fh / 100))
    part(CUBE, mi, "_right", w / 2 - t / 2, 0, z0 + fh / 2, (t / 100, (d - 2 * t) / 100, fh / 100))
    win_w, win_z0, win_z1 = 96.0, 120.0, 218.0
    seg_d = (d - 2 * t - win_w) / 2.0
    part(CUBE, mi, "_lF", -w / 2 + t / 2, -(win_w / 2 + seg_d / 2), z0 + fh / 2,
         (t / 100, seg_d / 100, fh / 100))
    part(CUBE, mi, "_lB", -w / 2 + t / 2, (win_w / 2 + seg_d / 2), z0 + fh / 2,
         (t / 100, seg_d / 100, fh / 100))
    part(CUBE, mi, "_lSill", -w / 2 + t / 2, 0, z0 + win_z0 / 2,
         (t / 100, win_w / 100, win_z0 / 100))
    part(CUBE, mi, "_lTop", -w / 2 + t / 2, 0, z0 + win_z1 + (fh - win_z1) / 2,
         (t / 100, win_w / 100, (fh - win_z1) / 100))

    # fake shutter windows on the front columns (exterior dressing)
    part(CUBE, dark, "_wf1", -w / 4 - 12, -d / 2 - 2, z0 + 190, (0.62, 0.05, 0.74))
    part(CUBE, dark, "_wf2", w / 4 + 12, -d / 2 - 2, z0 + 190, (0.62, 0.05, 0.74))

    # partition wall -> two rooms, inner doorway toward the right end
    inner_gap = 132.0
    py = d * 0.16
    gap_x = w * 0.18                      # doorway centre
    left_a, left_b = -w / 2 + t, gap_x - inner_gap / 2
    right_a, right_b = gap_x + inner_gap / 2, w / 2 - t
    part(CUBE, mi_in, "_p1", (left_a + left_b) / 2, py, z0 + fh / 2,
         ((left_b - left_a) / 100, 0.12, fh / 100))
    part(CUBE, mi_in, "_p2", (right_a + right_b) / 2, py, z0 + fh / 2,
         ((right_b - right_a) / 100, 0.12, fh / 100))
    part(CUBE, mi_in, "_pLintel", gap_x, py,
         z0 + door_h + (fh - door_h) / 2, (inner_gap / 100, 0.12, (fh - door_h) / 100))

    # ceiling above the ground floor
    part(CUBE, mi_in, "_ceil", 0, 0, z0 + fh + 7, (w / 100, d / 100, 0.14))

    # second storey: solid block (facade only) with fake windows
    if storeys == 2:
        part(CUBE, mi, "_up", 0, 0, z0 + fh + 14 + fh / 2, (w / 100, d / 100, fh / 100))
        part(CUBE, dark, "_wu1", -w / 4, -d / 2 - 2, z0 + fh + 190, (0.62, 0.05, 0.74))
        part(CUBE, dark, "_wu2", w / 4, -d / 2 - 2, z0 + fh + 190, (0.62, 0.05, 0.74))
    top = z0 + h + 14 + (7 if storeys == 1 else 14)

    # parapet + tank
    part(CUBE, mi, "_pN", 0, d / 2 - 10, top + 40, (w / 100, 0.2, 0.8))
    part(CUBE, mi, "_pS", 0, -d / 2 + 10, top + 40, (w / 100, 0.2, 0.8))
    part(CUBE, mi, "_pE", w / 2 - 10, 0, top + 40, (0.2, d / 100 - 0.2, 0.8))
    part(CUBE, mi, "_pW", -w / 2 + 10, 0, top + 40, (0.2, d / 100 - 0.2, 0.8))
    if idx % 2 == 0:
        part(CYLINDER, steel, "_tank", w / 4, d / 4, top + 55, (1.1, 1.1, 1.1))

    # ----- furnishing (main room, y < py) -----
    cx, cy = -w * 0.22, py - d * 0.34          # charpai centre
    for i, (sx, sy) in enumerate(((-88, -40), (88, -40), (-88, 40), (88, 40))):
        part(CYLINDER, dark, "_chL{}".format(i), cx + sx, cy + sy, z0 + 21,
             (0.07, 0.07, 0.42))
    part(CUBE, jute, "_chTop", cx, cy, z0 + 46, (1.92, 0.95, 0.07))

    part(CUBE, clay, "_chulha", w * 0.30, -d / 2 + t + 46, z0 + 17, (0.52, 0.42, 0.34))
    part(SPHERE, dark, "_pot", w * 0.30, -d / 2 + t + 46, z0 + 44, (0.30, 0.30, 0.22))
    part(CUBE, dark, "_shelf", w / 2 - t - 16, d * 0.0, z0 + 152, (0.16, 1.2, 0.05))
    part(SPHERE, terra, "_matka", w * 0.34, py + d * 0.24, z0 + 22, (0.34, 0.34, 0.42))
    part(CUBE, bulb_mat, "_bulb", 0, py - d * 0.3, z0 + fh - 32, (0.09, 0.09, 0.16))


def build_houses_v3(plots, rng):
    bulb_mat = make_bulb_material()
    for plot in plots:
        try:
            build_house_v3(plot, bulb_mat, rng)
        except Exception as e:
            warn("house {} failed: {}".format(plot[6], e))
    log("houses v3: {} rebuilt hollow + furnished".format(len(plots)))


# --------------------------- landmark re-snap -------------------------------

LANDMARK_PREFIXES = ("VG_Gurdwara_", "VG_ShivMandir", "VG_School", "VG_Bank",
                     "VG_Farm_", "VG_Pond_")


def resnap_landmarks():
    """Group landmark parts by their root label and drop each group so the
    lowest corner of its footprint sits on the ground (fixes hillside float)."""
    groups = {}
    for actor in EAS.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue
        for prefix in LANDMARK_PREFIXES:
            if label.startswith(prefix):
                # group per building: prefix + first name token after it, so
                # each gurdwara / farm structure re-snaps independently
                rest = label[len(prefix):]
                key = prefix + rest.split("_")[0]
                groups.setdefault(key, []).append(actor)
                break
    fixed = 0
    for key, actors in groups.items():
        min_gap = None
        for a in actors:
            origin, extent = a.get_actor_bounds(False)
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                cx = origin.x + sx * extent.x * 0.9
                cy = origin.y + sy * extent.y * 0.9
                gz = ground_z(cx, cy)
                gap = (origin.z - extent.z) - gz
                if min_gap is None or gap < min_gap:
                    min_gap = gap
        if min_gap is not None and min_gap > 45.0:
            for a in actors:
                loc = a.get_actor_location()
                a.set_actor_location(
                    unreal.Vector(loc.x, loc.y, loc.z - (min_gap - 12.0)), False, False)
            fixed += 1
            log("re-snapped {} down {:.0f} cm".format(key, min_gap - 12.0))
    if not fixed:
        log("landmarks already grounded")


# ------------------------------ mountains v3 --------------------------------

def find_static_meshes(folder):
    meshes = []
    if not EAL.does_directory_exist(folder):
        return meshes
    for asset_path in EAL.list_assets(folder, recursive=True, include_folder=False):
        obj = EAL.load_asset(asset_path.split(".")[0])
        if isinstance(obj, unreal.StaticMesh):
            meshes.append(obj)
    return meshes


def combined_box(meshes):
    mn = [1e12, 1e12, 1e12]
    mx = [-1e12, -1e12, -1e12]
    for mesh in meshes:
        b = mesh.get_bounding_box()
        mn = [min(mn[0], b.min.x), min(mn[1], b.min.y), min(mn[2], b.min.z)]
        mx = [max(mx[0], b.max.x), max(mx[1], b.max.y), max(mx[2], b.max.z)]
    return mn, mx


def spawn_group(meshes, label, folder, x, y, yaw, target_width, sink_frac):
    if not meshes:
        return []
    mn, mx = combined_box(meshes)
    size_x = max(1.0, mx[0] - mn[0])
    size_y = max(1.0, mx[1] - mn[1])
    size_z = max(1.0, mx[2] - mn[2])
    scale = target_width / max(size_x, size_y)
    cx = (mn[0] + mx[0]) * 0.5 * scale
    cy = (mn[1] + mx[1]) * 0.5 * scale
    rad = math.radians(yaw)
    ox = cx * math.cos(rad) - cy * math.sin(rad)
    oy = cx * math.sin(rad) + cy * math.cos(rad)
    gz = ground_z(x, y)
    z = gz - mn[2] * scale - size_z * scale * sink_frac
    loc = unreal.Vector(x - ox, y - oy, z)
    rot = unreal.Rotator(0.0, 0.0, yaw)
    actors = []
    for i, mesh in enumerate(meshes):
        actor = EAS.spawn_actor_from_object(mesh, loc, rot)
        actor.set_actor_label("{}_P{:02d}".format(label, i) if len(meshes) > 1 else label)
        actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        actor.set_folder_path(folder)
        actors.append(actor)
    return actors


def dress_hero_trees(canopy_parent, rng):
    """The imported GLB hero trees came in leafless (their masked leaf
    textures never survived import) and read as dead wood. Group their parts,
    measure the crown, and graft generated canopy lobes on so they live."""
    groups = {}
    for actor in EAS.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue
        if label.startswith("VGX_HeroTree_"):
            key = label.split("_P")[0]
            groups.setdefault(key, []).append(actor)
    leaf_a = canopy_mi(canopy_parent, "PeepalGreen", TREE_TONES["PeepalGreen"])
    leaf_b = canopy_mi(canopy_parent, "MangoGreen", TREE_TONES["MangoGreen"])
    n = 0
    for key, actors in groups.items():
        mn = [1e12, 1e12, 1e12]
        mx = [-1e12, -1e12, -1e12]
        for a in actors:
            origin, extent = a.get_actor_bounds(False)
            mn = [min(mn[0], origin.x - extent.x), min(mn[1], origin.y - extent.y),
                  min(mn[2], origin.z - extent.z)]
            mx = [max(mx[0], origin.x + extent.x), max(mx[1], origin.y + extent.y),
                  max(mx[2], origin.z + extent.z)]
        cx, cy = (mn[0] + mx[0]) / 2.0, (mn[1] + mx[1]) / 2.0
        height = mx[2] - mn[2]
        crown_z = mn[2] + height * 0.72
        spread = max(mx[0] - mn[0], mx[1] - mn[1]) * 0.30
        leaf = leaf_a if n % 2 == 0 else leaf_b
        lobes = 6 if height > 3000 else 5
        for l in range(lobes):
            a2 = rng.uniform(0, 2 * math.pi)
            rr = spread * rng.uniform(0.25, 0.75)
            lz = crown_z + rng.uniform(-height * 0.08, height * 0.14)
            s = spread * rng.uniform(0.011, 0.017)  # sphere asset is 100 cm
            spawn_mesh(SPHERE, leaf, "VG3_HeroLeaf_{}_{}".format(n, l),
                       "Village/Trees",
                       unreal.Vector(cx + math.cos(a2) * rr,
                                     cy + math.sin(a2) * rr, lz),
                       (s, s, s * 0.75))
        n += 1
    log("hero trees dressed with canopies: {}".format(n))


# ------------------------------ playgrounds ---------------------------------

def build_cricket_ground():
    cx, cy = CRICKET_CENTER
    gz = ground_z(cx, cy)
    folder = "Village/Playgrounds/Cricket"
    maidan = flat_mi("Maidan", (0.44, 0.44, 0.24))
    pitchmi = flat_mi("PitchClay", (0.62, 0.52, 0.36))
    white = flat_mi("CreaseWhite", (0.92, 0.92, 0.88))
    wood = flat_mi("StumpWood", (0.72, 0.60, 0.40))
    rope = flat_mi("BoundaryRope", (0.80, 0.30, 0.15))
    dark = flat_mi("DarkWood", (0.16, 0.11, 0.08))

    # maidan disc + pitch strip (thick enough to swallow gentle terrain)
    spawn_mesh(CYLINDER, maidan, "VG3_Cricket_Maidan", folder,
               unreal.Vector(cx, cy, gz + 6.0),
               (CRICKET_BOUNDARY * 2 / 100.0, CRICKET_BOUNDARY * 2 / 100.0, 0.09))
    surface = gz + 6.0 + 4.5
    spawn_mesh(CUBE, pitchmi, "VG3_Cricket_Pitch", folder,
               unreal.Vector(cx, cy, surface + 1.5), (20.8, 3.1, 0.035))

    # stumps + creases at both ends (pitch runs along X, 20.12 m)
    for endx, tag in ((cx - 1006.0, "N"), (cx + 1006.0, "S")):
        for i, off in enumerate((-11.5, 0.0, 11.5)):
            spawn_mesh(CYLINDER, wood, "VG3_Cricket_Stump{}{}".format(tag, i),
                       folder, unreal.Vector(endx, cy + off, surface + 38.0),
                       (0.045, 0.045, 0.72))
        # popping + bowling crease lines
        spawn_mesh(CUBE, white, "VG3_Cricket_Crease{}a".format(tag), folder,
                   unreal.Vector(endx + (122.0 if endx < cx else -122.0), cy, surface + 3.6),
                   (0.06, 2.7, 0.015))
        spawn_mesh(CUBE, white, "VG3_Cricket_Crease{}b".format(tag), folder,
                   unreal.Vector(endx, cy, surface + 3.6), (0.06, 2.7, 0.015))

    # boundary: rope posts + connecting rope chords + corner flags
    n = 30
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        x0, y0 = cx + math.cos(a0) * CRICKET_BOUNDARY, cy + math.sin(a0) * CRICKET_BOUNDARY
        x1, y1 = cx + math.cos(a1) * CRICKET_BOUNDARY, cy + math.sin(a1) * CRICKET_BOUNDARY
        g0 = ground_z(x0, y0)
        spawn_mesh(CYLINDER, wood, "VG3_Cricket_Post_{:02d}".format(i), folder,
                   unreal.Vector(x0, y0, g0 + 38.0), (0.07, 0.07, 0.6))
        mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        seg = math.hypot(x1 - x0, y1 - y0)
        yawd = math.degrees(math.atan2(y1 - y0, x1 - x0))
        spawn_mesh(CUBE, rope, "VG3_Cricket_Rope_{:02d}".format(i), folder,
                   unreal.Vector(mx, my, ground_z(mx, my) + 52.0),
                   (seg / 100.0, 0.06, 0.06), (0.0, yawd, 0.0))
        if i % 5 == 0:
            spawn_mesh(CONE, rope, "VG3_Cricket_Flag_{:02d}".format(i), folder,
                       unreal.Vector(x0, y0, g0 + 78.0), (0.22, 0.22, 0.3))

    # scoreboard + benches on the north edge
    sx, sy = cx, cy - CRICKET_BOUNDARY - 350.0
    sgz = ground_z(sx, sy)
    spawn_mesh(CYLINDER, dark, "VG3_Cricket_SbPostL", folder,
               unreal.Vector(sx - 130, sy, sgz + 110), (0.1, 0.1, 2.2))
    spawn_mesh(CYLINDER, dark, "VG3_Cricket_SbPostR", folder,
               unreal.Vector(sx + 130, sy, sgz + 110), (0.1, 0.1, 2.2))
    spawn_mesh(CUBE, dark, "VG3_Cricket_Scoreboard", folder,
               unreal.Vector(sx, sy, sgz + 210), (3.1, 0.14, 1.7))
    for i, bx in enumerate((sx - 700, sx + 700)):
        bgz = ground_z(bx, sy + 120)
        spawn_mesh(CUBE, wood, "VG3_Cricket_Bench{}".format(i), folder,
                   unreal.Vector(bx, sy + 120, bgz + 25), (2.4, 0.45, 0.09))
        spawn_mesh(CUBE, dark, "VG3_Cricket_BenchL{}".format(i), folder,
                   unreal.Vector(bx, sy + 120, bgz + 11), (2.1, 0.35, 0.22))
    log("cricket maidan built at ({:.0f}, {:.0f})".format(cx, cy))


def find_actor_by_label(label):
    for actor in EAS.get_all_level_actors():
        try:
            if actor.get_actor_label() == label:
                return actor
        except Exception:
            pass
    return None


def dress_kancha_playground(canopy_parent, rng):
    zone = find_actor_by_label("MG_KanchaZone")
    if zone:
        loc = zone.get_actor_location()
        kx, ky = loc.x, loc.y
    else:
        kx, ky = 19500.0, 11000.0
        warn("MG_KanchaZone not found; dressing default spot")
    gz = ground_z(kx, ky)
    folder = "Village/Playgrounds/Kancha"
    stone = flat_mi("Stone", (0.52, 0.50, 0.46))
    jute = flat_mi("Jute", (0.72, 0.60, 0.38))
    dark = flat_mi("DarkWood", (0.16, 0.11, 0.08))
    dirt = flat_mi("KanchaDirt", (0.52, 0.42, 0.28))

    # widen the play dirt into a proper court
    spawn_mesh(CYLINDER, dirt, "VG3_Kancha_Court", folder,
               unreal.Vector(kx, ky, gz + 2.0), (13.0, 13.0, 0.03))
    for i in range(14):
        a = 2 * math.pi * i / 14
        sx = kx + math.cos(a) * 640.0
        sy = ky + math.sin(a) * 640.0
        s = rng.uniform(0.16, 0.26)
        spawn_mesh(CUBE, stone, "VG3_Kancha_Stone_{:02d}".format(i), folder,
                   unreal.Vector(sx, sy, ground_z(sx, sy) + s * 42),
                   (s, s, s * 0.8), (0.0, rng.uniform(0, 360), 0.0))
    # two charpais for spectators
    for j, (ox, oy, cyaw) in enumerate(((880, 240, 15), (-820, -380, -30))):
        bx, by = kx + ox, ky + oy
        bgz = ground_z(bx, by)
        for i, (sx, sy) in enumerate(((-88, -40), (88, -40), (-88, 40), (88, 40))):
            r = math.radians(cyaw)
            px = bx + sx * math.cos(r) - sy * math.sin(r)
            py = by + sx * math.sin(r) + sy * math.cos(r)
            spawn_mesh(CYLINDER, dark, "VG3_Kancha_Ch{}L{}".format(j, i), folder,
                       unreal.Vector(px, py, bgz + 21), (0.07, 0.07, 0.42))
        spawn_mesh(CUBE, jute, "VG3_Kancha_Ch{}Top".format(j), folder,
                   unreal.Vector(bx, by, bgz + 46), (1.92, 0.95, 0.07),
                   (0.0, cyaw, 0.0))
    build_tree(990, kx + 1300.0, ky - 900.0, "Neem", canopy_parent, rng)
    log("kancha playground dressed at ({:.0f}, {:.0f})".format(kx, ky))


# -------------------------------- animals -----------------------------------

def animal_class():
    cls = getattr(unreal, "GrazingAnimal", None)
    if cls is None:
        try:
            cls = unreal.load_class(None, "/Script/rural_pardeep.GrazingAnimal")
        except Exception:
            cls = None
    return cls


def spawn_animal(cls, species, label, x, y, coat, detail, wander=900.0):
    gz = ground_z(x, y)
    animal = EAS.spawn_actor_from_class(cls, unreal.Vector(x, y, gz + 2.0),
                                        unreal.Rotator(0, 0, 0))
    if animal is None:
        return None
    animal.set_actor_label(label)
    animal.set_folder_path("Village/Animals")
    try:
        animal.set_editor_property("species", species)
        animal.set_editor_property("wander_radius", wander)
        animal.set_editor_property("coat_material", coat)
        animal.set_editor_property("detail_material", detail)
    except Exception as e:
        warn("could not configure {}: {}".format(label, e))
    return animal


def build_animals(rng):
    cls = animal_class()
    if cls is None:
        warn("AGrazingAnimal missing — compile the module. Animals skipped.")
        return
    white = flat_mi("CoatWhite", (0.90, 0.88, 0.82))
    brown = flat_mi("CoatBrown", (0.45, 0.28, 0.16))
    black = flat_mi("CoatBlack", (0.09, 0.08, 0.08))
    bay = flat_mi("CoatBay", (0.38, 0.22, 0.11))
    grey = flat_mi("CoatGrey", (0.55, 0.53, 0.50))
    detail = flat_mi("HornDark", (0.20, 0.18, 0.16))

    S = unreal.GrazingSpecies

    # farm pen with fence
    px, py = PEN_CENTER
    folder = "Village/Animals/Pen"
    wood = flat_mi("StumpWood", (0.72, 0.60, 0.40))
    hw, hh = 1250.0, 950.0
    gate_from, gate_to = 0.35, 0.65   # gap on the south side
    edges = [((-hw, -hh), (hw, -hh)), ((hw, -hh), (hw, hh)),
             ((hw, hh), (-hw, hh)), ((-hw, hh), (-hw, -hh))]
    pi = 0
    for e, ((x0, y0), (x1, y1)) in enumerate(edges):
        n = 6
        for i in range(n + 1):
            t = i / float(n)
            if e == 0 and gate_from < t < gate_to:
                continue
            fx, fy = px + x0 + (x1 - x0) * t, py + y0 + (y1 - y0) * t
            fgz = ground_z(fx, fy)
            spawn_mesh(CYLINDER, wood, "VG3_Pen_Post_{:02d}".format(pi), folder,
                       unreal.Vector(fx, fy, fgz + 55), (0.09, 0.09, 1.1))
            pi += 1
        seg = math.hypot(x1 - x0, y1 - y0)
        yawd = math.degrees(math.atan2(y1 - y0, x1 - x0))
        for rail_z in (38.0, 86.0):
            if e == 0:
                for t0, t1 in ((0.0, gate_from), (gate_to, 1.0)):
                    mx = px + x0 + (x1 - x0) * (t0 + t1) / 2
                    my = py + y0 + (y1 - y0) * (t0 + t1) / 2
                    spawn_mesh(CUBE, wood, "VG3_Pen_Rail_{}_{}{}".format(e, rail_z, t0),
                               folder, unreal.Vector(mx, my, ground_z(mx, my) + rail_z),
                               (seg * (t1 - t0) / 100.0, 0.07, 0.07), (0.0, yawd, 0.0))
            else:
                mx, my = px + (x0 + x1) / 2, py + (y0 + y1) / 2
                spawn_mesh(CUBE, wood, "VG3_Pen_Rail_{}_{}".format(e, rail_z), folder,
                           unreal.Vector(mx, my, ground_z(mx, my) + rail_z),
                           (seg / 100.0, 0.07, 0.07), (0.0, yawd, 0.0))

    herd = [
        (S.COW, "VG3_Cow_Pen1", px - 500, py - 250, white, 620.0),
        (S.COW, "VG3_Cow_Pen2", px + 420, py + 180, brown, 620.0),
        (S.BUFFALO, "VG3_Buffalo_Pen", px - 100, py + 420, black, 560.0),
        (S.HORSE, "VG3_Horse_Pen", px + 620, py - 380, bay, 640.0),
        # pond wallowers
        (S.BUFFALO, "VG3_Buffalo_Pond1", POND_CENTER[0] - 3500, POND_CENTER[1] + 600, black, 520.0),
        (S.BUFFALO, "VG3_Buffalo_Pond2", POND_CENTER[0] - 2800, POND_CENTER[1] - 1500, black, 520.0),
        # free grazers on the field edges
        (S.COW, "VG3_Cow_Field1", -24000.0, 26000.0, white, 1250.0),
        (S.COW, "VG3_Cow_Field2", -36000.0, 4000.0, brown, 1250.0),
        (S.COW, "VG3_Cow_Field3", -21000.0, -18000.0, grey, 1250.0),
        (S.COW, "VG3_Cow_Field4", 6000.0, 26500.0, white, 1100.0),
        # horses near the gurdwara ground + school
        (S.HORSE, "VG3_Horse_Gurdwara", -4000.0, -11200.0, bay, 900.0),
        (S.HORSE, "VG3_Horse_School", 20800.0, 7300.0, brown, 900.0),
    ]
    count = 0
    for species, label, x, y, coat, wander in herd:
        if spawn_animal(cls, species, label, x, y, coat, detail, wander):
            count += 1
    log("animals: {} grazing (+ farm pen)".format(count))


# ----------------------------- ambient kites --------------------------------

def build_ambient_kites(plots, rng):
    cls = getattr(unreal, "KiteActor", None)
    if cls is None:
        try:
            cls = unreal.load_class(None, "/Script/rural_pardeep.KiteActor")
        except Exception:
            cls = None
    if cls is None:
        warn("KiteActor missing — ambient kites skipped")
        return

    kite_colors = [("KitePink", (0.92, 0.12, 0.35)), ("KiteOrange", (0.95, 0.45, 0.08)),
                   ("KiteGreen", (0.15, 0.70, 0.25))]
    anchors = []
    zone = find_actor_by_label("MG_KiteZone")
    if zone:
        loc = zone.get_actor_location()
        anchors.append((loc.x, loc.y, loc.z + 20.0))
    two_storey = [p for p in plots if p[5] == 2]
    rng.shuffle(two_storey)
    for p in two_storey[:2]:
        # houses are already rebuilt, so the trace lands ON the roof slab —
        # anchor just above it, where a flyer's hands would be
        roof_z = ground_z(p[0], p[1])
        anchors.append((p[0], p[1], roof_z + 40.0))

    for i, (ax, ay, az) in enumerate(anchors[:3]):
        kite = EAS.spawn_actor_from_class(cls, unreal.Vector(ax, ay, az),
                                          unreal.Rotator(0, 0, 0))
        if kite is None:
            continue
        kite.set_actor_label("VG3_AmbientKite_{}".format(i))
        kite.set_folder_path("Village/Kites")
        cname, rgb = kite_colors[i % len(kite_colors)]
        mi = flat_mi(cname, rgb)
        try:
            kite.set_editor_property("ambient_auto_fly", True)
            kite.set_editor_property("string_length", rng.uniform(1300.0, 2100.0))
            kite.kite_mesh.set_material(0, mi)
            for piece in kite.get_editor_property("tail_pieces"):
                piece.set_material(0, mi)
        except Exception as e:
            warn("kite {} config: {}".format(i, e))
    log("{} ambient kites launched".format(min(3, len(anchors))))


# ------------------------------ atmosphere ----------------------------------

def ensure_sky_motion():
    has_cloud = any(isinstance(a, unreal.VolumetricCloud)
                    for a in EAS.get_all_level_actors())
    if not has_cloud:
        cloud = EAS.spawn_actor_from_class(unreal.VolumetricCloud,
                                           unreal.Vector(0, 0, 0))
        cloud.set_actor_label("VG3_Clouds")
        cloud.set_folder_path("Village/Atmosphere")
        log("VolumetricCloud spawned")
    has_sky = any(isinstance(a, unreal.SkyAtmosphere)
                  for a in EAS.get_all_level_actors())
    if not has_sky:
        sky = EAS.spawn_actor_from_class(unreal.SkyAtmosphere,
                                         unreal.Vector(0, 0, 0))
        sky.set_actor_label("VG3_SkyAtmosphere")
        sky.set_folder_path("Village/Atmosphere")
        log("SkyAtmosphere spawned")


# --------------------------------- main --------------------------------------

def main():
    global _WORLD
    _WORLD = UES.get_editor_world()
    if _WORLD is None or "Lvl_Village" not in _WORLD.get_name():
        warn("Lvl_Village is not loaded — aborting.")
        return
    rng = random.Random(3062)

    plots, arch = collect_house_plots()
    cleanup_previous()

    mpc = EAL.load_asset(MPC_PATH)
    if mpc is None:
        warn("MPC_Weather missing — run build_extras first")
        return

    # materials that other stages depend on
    rewire_ground_wetness(mpc)
    canopy_parent = make_canopy_parent(mpc)
    field_mats = make_field_materials()

    build_all_roads(mpc)
    all_road_samples = []
    for pts in ROADS.values():
        all_road_samples.extend(road_samples(pts))

    build_fields_v3(field_mats, all_road_samples, rng)
    resnap_landmarks()
    build_houses_v3(plots, rng)
    build_trees_v3(canopy_parent, all_road_samples, plots, rng)
    dress_hero_trees(canopy_parent, rng)
    build_cricket_ground()
    dress_kancha_playground(canopy_parent, rng)
    build_animals(rng)
    build_ambient_kites(plots, rng)
    ensure_sky_motion()

    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("all dirty packages saved")
    except Exception as e:
        warn("save failed: {}".format(e))
    log("UPGRADE COMPLETE — VG3 actors: {}".format(
        sum(1 for a in EAS.get_all_level_actors()
            if a.get_actor_label().startswith("VG3_"))))


if __name__ == "__main__":
    main()
