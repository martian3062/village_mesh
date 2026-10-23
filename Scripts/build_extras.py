"""
build_extras.py
===============
Second-stage world content for the village (idempotent — safe to re-run).
Runs after build_environment.py; everything it spawns is labelled VGX_*.

Adds:
  1. Imports the remaining user GLBs: two hero trees, the low-poly forest
     pack, the NY highway and the London skyscraper.
  2. MPC_Weather (WindIntensity / Wetness / WindDirection) — the C++
     AWeatherManager writes it every frame, foliage materials read it.
  3. M_VGFoliageWind — canopy material with height-masked World Position
     Offset gusts driven by MPC_Weather; swapped onto every generated
     VG_Tree_*_C canopy and injected into the imported tree materials.
  4. A river: spline-sampled water ribbon flowing from the eastern
     mountains down past the fields into the village pond, with an
     animated flowing-water material (moving ripple bands + WPO waves).
  5. A distant city skyline beyond the northern mountains (skyscraper
     cluster + elevated highway) so the rural core stays rural.
  6. VGX_Weather — the AWeatherManager actor wired to the MPC, with the
     rain-shell streak material for visible rainfall.

RUN:  py "D:/rural_games/rural_pardeep/Scripts/build_extras.py"
"""

import math
import os
import random

import unreal

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
MEL = unreal.MaterialEditingLibrary

MODEL_ROOT = r"D:\rural game archotectuere"
ARCH_DIR = "/Game/Village/Arch"
MAT_DIR = "/Game/Village/Materials"
MPC_PATH = "/Game/Village/MPC_Weather"

EXTRA_SOURCES = {
    "HeroTreeRoot": os.path.join(MODEL_ROOT, "rootbound_majesty_tree_free.glb"),
    "HeroTree": os.path.join(MODEL_ROOT, "tree_3d_model_free.glb"),
    "ForestPack": os.path.join(MODEL_ROOT, "low_poly_forest_tree_pack.glb"),
    "CityHighway": os.path.join(MODEL_ROOT, "fixed_new_york_highway_interstate_95.glb"),
    "CitySkyscraper": os.path.join(MODEL_ROOT, "free_london_skyscraper.glb"),
}

PLANE = EAL.load_asset("/Engine/BasicShapes/Plane.Plane")
CYLINDER = EAL.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")

_WORLD = None
_ZTOP = 100000.0
_ZBOT = -100000.0


def log(msg):
    unreal.log("[build_extras] {}".format(msg))


def warn(msg):
    unreal.log_warning("[build_extras] {}".format(msg))


def ground_z(x, y, default_z=0.0):
    hit = unreal.SystemLibrary.line_trace_single(
        _WORLD, unreal.Vector(x, y, _ZTOP), unreal.Vector(x, y, _ZBOT),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
        unreal.DrawDebugTrace.NONE, True)
    if hit:
        return hit.to_dict()["location"].z
    return default_z


def cleanup_previous():
    removed = 0
    for actor in EAS.get_all_level_actors():
        try:
            if actor.get_actor_label().startswith("VGX_"):
                EAS.destroy_actor(actor)
                removed += 1
        except Exception:
            pass
    if removed:
        log("cleaned up {} VGX_ actors".format(removed))


# --------------------------- import helpers --------------------------------

def find_static_meshes(folder):
    meshes = []
    if not EAL.does_directory_exist(folder):
        return meshes
    for asset_path in EAL.list_assets(folder, recursive=True, include_folder=False):
        obj = EAL.load_asset(asset_path.split(".")[0])
        if isinstance(obj, unreal.StaticMesh):
            meshes.append(obj)
    return meshes


def enable_nanite(mesh):
    try:
        settings = mesh.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", True)
        mesh.set_editor_property("nanite_settings", settings)
    except Exception as e:
        warn("nanite enable failed on {}: {}".format(mesh.get_name(), e))


def import_extra_models():
    imported = {}
    for key, src in EXTRA_SOURCES.items():
        dest = "{}/{}".format(ARCH_DIR, key)
        meshes = find_static_meshes(dest)
        if meshes:
            imported[key] = meshes
            continue
        if not os.path.exists(src):
            warn("model source missing, skipped: " + src)
            continue
        log("importing {} ...".format(os.path.basename(src)))
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", src)
        task.set_editor_property("destination_path", dest)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        task.set_editor_property("replace_existing", True)
        try:
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        except Exception as e:
            warn("import failed for {}: {}".format(src, e))
            continue
        meshes = find_static_meshes(dest)
        if meshes:
            # Nanite everything except foliage that will use WPO wind
            # (Nanite + WPO costs more than it saves on low-poly trees).
            if key in ("CityHighway", "CitySkyscraper"):
                for mesh in meshes:
                    enable_nanite(mesh)
            imported[key] = meshes
            log("  -> {} static mesh(es)".format(len(meshes)))
        else:
            warn("  -> no static mesh produced from " + src)
    return imported


def combined_box(meshes):
    """Union bounding box across every part of a multi-mesh GLB import."""
    mn = [1e12, 1e12, 1e12]
    mx = [-1e12, -1e12, -1e12]
    for mesh in meshes:
        b = mesh.get_bounding_box()
        mn = [min(mn[0], b.min.x), min(mn[1], b.min.y), min(mn[2], b.min.z)]
        mx = [max(mx[0], b.max.x), max(mx[1], b.max.y), max(mx[2], b.max.z)]
    return mn, mx


def spawn_group(meshes, label, folder, x, y, yaw=0.0, target_width=None,
                target_height=None, sink_frac=0.0):
    """Spawn ALL parts of an imported model with one shared transform so the
    model reassembles, scaled by combined bounds and recentred so the
    geometry's footprint centre lands on (x, y)."""
    if not meshes:
        return []
    mn, mx = combined_box(meshes)
    size_x = max(1.0, mx[0] - mn[0])
    size_y = max(1.0, mx[1] - mn[1])
    size_z = max(1.0, mx[2] - mn[2])
    scales = []
    if target_width:
        scales.append(target_width / max(size_x, size_y))
    if target_height:
        scales.append(target_height / size_z)
    scale = min(scales) if scales else 1.0

    # pivot -> geometry-centre offset, rotated into world space
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


# ------------------------------ MPC ----------------------------------------

def make_weather_mpc():
    if EAL.does_asset_exist(MPC_PATH):
        return EAL.load_asset(MPC_PATH)
    mpc = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "MPC_Weather", "/Game/Village", unreal.MaterialParameterCollection,
        unreal.MaterialParameterCollectionFactoryNew())
    wind = unreal.CollectionScalarParameter()
    wind.set_editor_property("parameter_name", "WindIntensity")
    wind.set_editor_property("default_value", 0.15)
    wet = unreal.CollectionScalarParameter()
    wet.set_editor_property("parameter_name", "Wetness")
    wet.set_editor_property("default_value", 0.0)
    mpc.set_editor_property("scalar_parameters", [wind, wet])
    wdir = unreal.CollectionVectorParameter()
    wdir.set_editor_property("parameter_name", "WindDirection")
    wdir.set_editor_property("default_value", unreal.LinearColor(1.0, 0.35, 0.0, 0.0))
    mpc.set_editor_property("vector_parameters", [wdir])
    EAL.save_asset(MPC_PATH)
    log("created MPC_Weather")
    return mpc


# --------------------------- wind materials --------------------------------

def _expr(mat, cls, x, y):
    return MEL.create_material_expression(mat, cls, x, y)


def build_wind_wpo(mat, mpc, amp_cm, height_range_cm, x0=-1400, y0=600):
    """Wire a height-masked sway into MP_WORLD_POSITION_OFFSET.

    offset = dir * sin(time*speed + (wp.x+wp.y)*phase) * WindIntensity(MPC)
             * amp * saturate((wp.z - objpos.z) / height_range)
    """
    wp = _expr(mat, unreal.MaterialExpressionWorldPosition, x0, y0)
    objpos = _expr(mat, unreal.MaterialExpressionObjectPositionWS, x0, y0 + 220)
    time = _expr(mat, unreal.MaterialExpressionTime, x0, y0 + 420)

    mask_x = _expr(mat, unreal.MaterialExpressionComponentMask, x0 + 180, y0)
    mask_x.set_editor_property("r", True); mask_x.set_editor_property("g", True)
    mask_x.set_editor_property("b", False); mask_x.set_editor_property("a", False)
    MEL.connect_material_expressions(wp, "", mask_x, "")

    # (wp.x + wp.y) * 0.0012 — spatial phase so trees don't sway in unison
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

    # height mask: 0 at the trunk base, 1 at height_range_cm above the pivot
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

    # MPC wind intensity * amplitude
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


def make_foliage_wind_material(mpc):
    path = MAT_DIR + "/M_VGFoliageWind"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGFoliageWind", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    colour = _expr(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    colour.set_editor_property("constant", unreal.LinearColor(0.20, 0.35, 0.12, 1.0))
    MEL.connect_material_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = _expr(mat, unreal.MaterialExpressionConstant, -400, 200)
    rough.set_editor_property("r", 0.85)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    build_wind_wpo(mat, mpc, amp_cm=55.0, height_range_cm=500.0)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("created M_VGFoliageWind")
    return mat


def swap_generated_canopies(foliage_mat):
    count = 0
    for actor in EAS.get_all_level_actors():
        try:
            label = actor.get_actor_label()
            if label.startswith("VG_Tree_") and label.endswith("_C"):
                actor.static_mesh_component.set_material(0, foliage_mat)
                count += 1
        except Exception:
            pass
    log("wind canopy material on {} generated trees".format(count))


def inject_wind_into_imported(imported, mpc):
    """Give the imported tree meshes' materials the same MPC-driven sway."""
    done = set()
    for key, height_range in (("HeroTreeRoot", 1400.0), ("HeroTree", 900.0),
                              ("ForestPack", 600.0)):
        for mesh in imported.get(key, []):
            try:
                mats = mesh.get_editor_property("static_materials")
            except Exception:
                continue
            for slot in mats:
                mi = slot.get_editor_property("material_interface")
                if mi is None:
                    continue
                path = mi.get_path_name()
                if path in done:
                    continue
                done.add(path)
                try:
                    target = mi
                    if isinstance(mi, unreal.MaterialInstanceConstant):
                        parent = mi.get_editor_property("parent")
                        if parent is None:
                            continue
                        ppath = parent.get_path_name()
                        if not ppath.startswith("/Game/"):
                            # engine/Interchange parent: duplicate into the
                            # project so we can edit it, then re-parent the MI
                            dup_name = "M_Wind_{}".format(parent.get_name())
                            dup_path = "{}/{}".format(MAT_DIR, dup_name)
                            if not EAL.does_asset_exist(dup_path):
                                EAL.duplicate_asset(ppath.split(".")[0], dup_path)
                            dup = EAL.load_asset(dup_path)
                            if ppath in done:
                                target = None
                            else:
                                done.add(ppath)
                                target = dup
                            mi.set_editor_property("parent", dup)
                            EAL.save_asset(mi.get_path_name().split(".")[0])
                        else:
                            target = parent
                            if ppath in done:
                                target = None
                            done.add(ppath)
                    if isinstance(target, unreal.Material):
                        tpath = target.get_path_name().split(".")[0]
                        if EAL.get_metadata_tag(target, "vgx_wind") == "1":
                            continue  # already injected on a previous run
                        build_wind_wpo(target, mpc, amp_cm=40.0,
                                       height_range_cm=height_range)
                        EAL.set_metadata_tag(target, "vgx_wind", "1")
                        MEL.recompile_material(target)
                        EAL.save_asset(tpath)
                        log("wind injected: " + target.get_name())
                except Exception as e:
                    warn("wind injection failed on {}: {}".format(path, e))


# ------------------------------ rain shell ---------------------------------

def make_rain_streak_material():
    path = MAT_DIR + "/M_VGRainStreaks"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGRainStreaks", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)

    wp = _expr(mat, unreal.MaterialExpressionWorldPosition, -1500, 0)
    time = _expr(mat, unreal.MaterialExpressionTime, -1500, 260)

    wpz = _expr(mat, unreal.MaterialExpressionComponentMask, -1320, 0)
    wpz.set_editor_property("r", False); wpz.set_editor_property("g", False)
    wpz.set_editor_property("b", True); wpz.set_editor_property("a", False)
    MEL.connect_material_expressions(wp, "", wpz, "")

    zscale = _expr(mat, unreal.MaterialExpressionMultiply, -1140, 40)
    zc = _expr(mat, unreal.MaterialExpressionConstant, -1320, 130)
    zc.set_editor_property("r", 0.004)
    MEL.connect_material_expressions(wpz, "", zscale, "A")
    MEL.connect_material_expressions(zc, "", zscale, "B")

    tfall = _expr(mat, unreal.MaterialExpressionMultiply, -1140, 260)
    tc = _expr(mat, unreal.MaterialExpressionConstant, -1320, 340)
    tc.set_editor_property("r", 3.2)
    MEL.connect_material_expressions(time, "", tfall, "A")
    MEL.connect_material_expressions(tc, "", tfall, "B")

    drop = _expr(mat, unreal.MaterialExpressionSubtract, -960, 140)
    MEL.connect_material_expressions(zscale, "", drop, "A")
    MEL.connect_material_expressions(tfall, "", drop, "B")

    frac = _expr(mat, unreal.MaterialExpressionFrac, -800, 140)
    MEL.connect_material_expressions(drop, "", frac, "")

    band = _expr(mat, unreal.MaterialExpressionPower, -640, 140)
    pw = _expr(mat, unreal.MaterialExpressionConstant, -800, 240)
    pw.set_editor_property("r", 24.0)
    MEL.connect_material_expressions(frac, "", band, "Base")
    MEL.connect_material_expressions(pw, "", band, "Exp")

    # horizontal variation so streaks are not a uniform sheet
    wpx = _expr(mat, unreal.MaterialExpressionComponentMask, -1320, 480)
    wpx.set_editor_property("r", True); wpx.set_editor_property("g", True)
    wpx.set_editor_property("b", False); wpx.set_editor_property("a", False)
    MEL.connect_material_expressions(wp, "", wpx, "")
    vdot = _expr(mat, unreal.MaterialExpressionDotProduct, -1140, 480)
    vscale = _expr(mat, unreal.MaterialExpressionConstant2Vector, -1320, 580)
    vscale.set_editor_property("r", 0.017); vscale.set_editor_property("g", 0.013)
    MEL.connect_material_expressions(wpx, "", vdot, "A")
    MEL.connect_material_expressions(vscale, "", vdot, "B")
    vsin = _expr(mat, unreal.MaterialExpressionSine, -960, 480)
    MEL.connect_material_expressions(vdot, "", vsin, "")
    vabs = _expr(mat, unreal.MaterialExpressionAbs, -800, 480)
    MEL.connect_material_expressions(vsin, "", vabs, "")

    cells = _expr(mat, unreal.MaterialExpressionMultiply, -480, 300)
    MEL.connect_material_expressions(band, "", cells, "A")
    MEL.connect_material_expressions(vabs, "", cells, "B")

    rain_amt = _expr(mat, unreal.MaterialExpressionScalarParameter, -640, 560)
    rain_amt.set_editor_property("parameter_name", "RainAmount")
    rain_amt.set_editor_property("default_value", 1.0)
    gain = _expr(mat, unreal.MaterialExpressionConstant, -640, 660)
    gain.set_editor_property("r", 0.28)
    g1 = _expr(mat, unreal.MaterialExpressionMultiply, -320, 420)
    MEL.connect_material_expressions(rain_amt, "", g1, "A")
    MEL.connect_material_expressions(gain, "", g1, "B")
    opacity = _expr(mat, unreal.MaterialExpressionMultiply, -160, 340)
    MEL.connect_material_expressions(cells, "", opacity, "A")
    MEL.connect_material_expressions(g1, "", opacity, "B")
    MEL.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)

    tint = _expr(mat, unreal.MaterialExpressionConstant3Vector, -320, 60)
    tint.set_editor_property("constant", unreal.LinearColor(0.65, 0.72, 0.85, 1.0))
    emis = _expr(mat, unreal.MaterialExpressionMultiply, -160, 120)
    MEL.connect_material_expressions(tint, "", emis, "A")
    MEL.connect_material_expressions(cells, "", emis, "B")
    MEL.connect_material_property(emis, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("created M_VGRainStreaks")
    return mat


# -------------------------------- river ------------------------------------

RIVER_POINTS = [
    (99000.0, 44000.0),   # source: in the eastern mountain ring
    (76000.0, 37000.0),
    (54000.0, 31500.0),
    (36000.0, 27000.0),
    (25000.0, 23200.0),
    (18500.0, 20500.0),   # mouth: the village pond
]


def _catmull_rom(pts, samples_per_seg=8):
    """Smooth polyline through pts."""
    out = []
    ext = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(samples_per_seg):
            t = s / float(samples_per_seg)
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(pts[-1])
    return out


def make_river_material(mpc):
    path = MAT_DIR + "/M_VGRiverWater"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGRiverWater", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())

    wp = _expr(mat, unreal.MaterialExpressionWorldPosition, -1500, 0)
    time = _expr(mat, unreal.MaterialExpressionTime, -1500, 240)

    wpxy = _expr(mat, unreal.MaterialExpressionComponentMask, -1320, 0)
    wpxy.set_editor_property("r", True); wpxy.set_editor_property("g", True)
    wpxy.set_editor_property("b", False); wpxy.set_editor_property("a", False)
    MEL.connect_material_expressions(wp, "", wpxy, "")

    flow = _expr(mat, unreal.MaterialExpressionDotProduct, -1140, 0)
    fdir = _expr(mat, unreal.MaterialExpressionConstant2Vector, -1320, 100)
    fdir.set_editor_property("r", 0.0009); fdir.set_editor_property("g", 0.0007)
    MEL.connect_material_expressions(wpxy, "", flow, "A")
    MEL.connect_material_expressions(fdir, "", flow, "B")

    tflow = _expr(mat, unreal.MaterialExpressionMultiply, -1140, 240)
    tf = _expr(mat, unreal.MaterialExpressionConstant, -1320, 320)
    tf.set_editor_property("r", 0.55)
    MEL.connect_material_expressions(time, "", tflow, "A")
    MEL.connect_material_expressions(tf, "", tflow, "B")

    phase = _expr(mat, unreal.MaterialExpressionSubtract, -960, 120)
    MEL.connect_material_expressions(flow, "", phase, "A")
    MEL.connect_material_expressions(tflow, "", phase, "B")

    freq = _expr(mat, unreal.MaterialExpressionMultiply, -800, 120)
    fq = _expr(mat, unreal.MaterialExpressionConstant, -960, 220)
    fq.set_editor_property("r", 40.0)
    MEL.connect_material_expressions(phase, "", freq, "A")
    MEL.connect_material_expressions(fq, "", freq, "B")

    ripple = _expr(mat, unreal.MaterialExpressionSine, -640, 120)
    MEL.connect_material_expressions(freq, "", ripple, "")

    half = _expr(mat, unreal.MaterialExpressionMultiply, -480, 120)
    hc = _expr(mat, unreal.MaterialExpressionConstant, -640, 220)
    hc.set_editor_property("r", 0.5)
    MEL.connect_material_expressions(ripple, "", half, "A")
    MEL.connect_material_expressions(hc, "", half, "B")
    band = _expr(mat, unreal.MaterialExpressionAdd, -320, 120)
    MEL.connect_material_expressions(half, "", band, "A")
    MEL.connect_material_expressions(hc, "", band, "B")

    deep = _expr(mat, unreal.MaterialExpressionConstant3Vector, -480, -140)
    deep.set_editor_property("constant", unreal.LinearColor(0.015, 0.055, 0.070, 1.0))
    light = _expr(mat, unreal.MaterialExpressionConstant3Vector, -480, -280)
    light.set_editor_property("constant", unreal.LinearColor(0.055, 0.115, 0.125, 1.0))
    col = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -160, -140)
    MEL.connect_material_expressions(deep, "", col, "A")
    MEL.connect_material_expressions(light, "", col, "B")
    MEL.connect_material_expressions(band, "", col, "Alpha")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rough = _expr(mat, unreal.MaterialExpressionConstant, -160, 60)
    rough.set_editor_property("r", 0.04)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    spec = _expr(mat, unreal.MaterialExpressionConstant, -160, 140)
    spec.set_editor_property("r", 1.0)
    MEL.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)

    # gentle vertical waves so the surface visibly undulates
    wz = _expr(mat, unreal.MaterialExpressionMultiply, -480, 340)
    wamp = _expr(mat, unreal.MaterialExpressionConstant, -640, 420)
    wamp.set_editor_property("r", 4.0)
    MEL.connect_material_expressions(ripple, "", wz, "A")
    MEL.connect_material_expressions(wamp, "", wz, "B")
    up = _expr(mat, unreal.MaterialExpressionConstant3Vector, -480, 480)
    up.set_editor_property("constant", unreal.LinearColor(0.0, 0.0, 1.0, 0.0))
    wpo = _expr(mat, unreal.MaterialExpressionMultiply, -320, 400)
    MEL.connect_material_expressions(wz, "", wpo, "A")
    MEL.connect_material_expressions(up, "", wpo, "B")
    MEL.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("created M_VGRiverWater")
    return mat


def build_river(river_mat):
    pts = _catmull_rom(RIVER_POINTS, samples_per_seg=8)
    folder = "Village/River"
    total = len(pts) - 1
    count = 0
    for i in range(total):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        dx, dy = x1 - x0, y1 - y0
        seg = math.hypot(dx, dy)
        if seg < 1.0:
            continue
        cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        yaw = math.degrees(math.atan2(dy, dx))
        # taper: broad at the mountains, narrow at the pond
        t = i / float(total)
        width = 2400.0 * (1.0 - t) + 1200.0 * t
        gz = ground_z(cx, cy)
        actor = EAS.spawn_actor_from_object(
            PLANE, unreal.Vector(cx, cy, gz + 6.0), unreal.Rotator(0.0, 0.0, yaw))
        actor.set_actor_label("VGX_River_{:03d}".format(i))
        actor.set_actor_scale3d(unreal.Vector(seg * 1.12 / 100.0, width / 100.0, 1.0))
        actor.set_folder_path(folder)
        actor.static_mesh_component.set_material(0, river_mat)
        count += 1
    log("river: {} segments from the mountains to the pond".format(count))


# ---------------------------- placements -----------------------------------

def place_hero_trees(imported, rng):
    roots = imported.get("HeroTreeRoot", [])
    if roots:
        # landmark tree on the pond bank — the village bohar (banyan)
        spawn_group(roots, "VGX_HeroTree_Pond", "Village/Trees",
                    22800.0, 24600.0, rng.uniform(0, 360),
                    target_height=5200.0, sink_frac=0.02)
        log("rootbound majesty tree at the pond")
    heroes = imported.get("HeroTree", [])
    if heroes:
        spots = [(-3400.0, 15200.0), (10500.0, -10500.0), (-15500.0, -4200.0)]
        for i, (x, y) in enumerate(spots):
            spawn_group(heroes, "VGX_HeroTree_{:02d}".format(i),
                        "Village/Trees", x, y, rng.uniform(0, 360),
                        target_height=2600.0, sink_frac=0.02)
        log("{} hero trees in the core".format(len(spots)))


def place_forest_belt(imported, rng):
    pack = imported.get("ForestPack", [])
    if not pack:
        return
    count = 0
    for i in range(40):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(46000.0, 82000.0)
        x, y = r * math.cos(a), r * math.sin(a)
        mesh = pack[i % len(pack)]
        # one tree per spot, recentred on its own bounds (pack meshes carry
        # grid-arrangement pivots)
        spawn_group([mesh], "VGX_Forest_{:03d}".format(i), "Village/Forest",
                    x, y, rng.uniform(0, 360),
                    target_height=rng.uniform(1300.0, 2400.0), sink_frac=0.02)
        count += 1
    log("{} forest-pack trees in the outer belt".format(count))


def place_distant_city(imported, rng):
    """The user's urban models, staged as a far skyline NORTH beyond the
    mountain ring (-Y), still on the landscape so nothing floats. The
    village stays rural; the city reads as 'the city across the hills'.
    Move/delete VGX_City_* freely."""
    highway = imported.get("CityHighway", [])
    if highway:
        spawn_group(highway, "VGX_City_Highway", "Village/DistantCity",
                    0.0, -95500.0, 0.0, target_width=70000.0)
        log("elevated highway on the northern horizon")
    towers = imported.get("CitySkyscraper", [])
    if towers:
        spots = [(-30000.0, -98500.0, 40000.0), (-4000.0, -99500.0, 46000.0),
                 (23000.0, -97500.0, 36000.0)]
        for i, (x, y, h) in enumerate(spots):
            spawn_group(towers, "VGX_City_Tower_{:02d}".format(i),
                        "Village/DistantCity", x, y, rng.uniform(0, 360),
                        target_height=h)
        log("{} skyline towers".format(len(spots)))


def rebuild_mountains(rng):
    """Replace the fragmented single-part mountain placements (VG_Mountain_*)
    with properly assembled scans — the old ones read as shredded crust
    floating in the sky."""
    removed = 0
    for actor in EAS.get_all_level_actors():
        try:
            if actor.get_actor_label().startswith("VG_Mountain_"):
                EAS.destroy_actor(actor)
                removed += 1
        except Exception:
            pass
    log("removed {} old mountain fragments".format(removed))

    keys = ("MountainHill", "MountainKula", "MountainGlacier",
            "MountainMer", "MountainTremorgio", "MountainLake")
    models = []
    for key in keys:
        meshes = find_static_meshes("{}/{}".format(ARCH_DIR, key))
        if meshes:
            models.append((key, meshes))
    if not models:
        warn("no mountain meshes found — ring left empty")
        return
    count = 0
    for i, angle_deg in enumerate(range(0, 360, 30)):
        a = math.radians(angle_deg + rng.uniform(-6, 6))
        r = 92000.0 + rng.uniform(-4000, 6000)
        x, y = r * math.cos(a), r * math.sin(a)
        key, meshes = models[i % len(models)]
        spawn_group(meshes, "VGX_Mountain_{:02d}".format(i), "Village/Mountains",
                    x, y, rng.uniform(0, 360),
                    target_width=rng.uniform(52000.0, 78000.0), sink_frac=0.12)
        count += 1
    log("{} assembled mountains in the ring".format(count))


def place_far_ground():
    """A huge sand-coloured plane under everything so the horizon beyond the
    landscape reads as hazy plains instead of white void."""
    path = MAT_DIR + "/M_VGFarGround"
    if EAL.does_asset_exist(path):
        mat = EAL.load_asset(path)
    else:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_VGFarGround", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
        colour = _expr(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
        colour.set_editor_property("constant", unreal.LinearColor(0.42, 0.36, 0.26, 1.0))
        MEL.connect_material_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
        rough = _expr(mat, unreal.MaterialExpressionConstant, -400, 200)
        rough.set_editor_property("r", 1.0)
        MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
        MEL.recompile_material(mat)
        EAL.save_asset(path)
    actor = EAS.spawn_actor_from_object(PLANE, unreal.Vector(0, 0, -400.0),
                                        unreal.Rotator(0, 0, 0))
    actor.set_actor_label("VGX_FarGround")
    actor.set_actor_scale3d(unreal.Vector(9000.0, 9000.0, 1.0))
    actor.set_folder_path("Village/Atmosphere")
    actor.static_mesh_component.set_material(0, mat)
    log("far-ground plane placed")


def place_weather_manager(mpc, rain_mat):
    cls = getattr(unreal, "WeatherManager", None)
    if cls is None:
        warn("WeatherManager C++ class missing — weather skipped (compile the module).")
        return
    actor = EAS.spawn_actor_from_class(cls, unreal.Vector(0, 0, 2000))
    actor.set_actor_label("VGX_Weather")
    actor.set_folder_path("Village/Atmosphere")
    try:
        actor.set_editor_property("weather_mpc", mpc)
        actor.set_editor_property("rain_shell_mesh", CYLINDER)
        actor.set_editor_property("rain_shell_material", rain_mat)
    except Exception as e:
        warn("weather manager wiring failed: {}".format(e))
    log("VGX_Weather placed (auto-cycling Clear/Overcast/Rain/Storm)")


# --------------------------------- main -------------------------------------

def main():
    global _WORLD
    _WORLD = UES.get_editor_world()
    if _WORLD is None or "Lvl_Village" not in _WORLD.get_name():
        warn("Lvl_Village is not the loaded level — aborting.")
        return

    rng = random.Random(20260716)
    cleanup_previous()

    imported = import_extra_models()
    mpc = make_weather_mpc()

    foliage = make_foliage_wind_material(mpc)
    swap_generated_canopies(foliage)
    inject_wind_into_imported(imported, mpc)

    river_mat = make_river_material(mpc)
    build_river(river_mat)

    rebuild_mountains(rng)
    place_far_ground()
    place_hero_trees(imported, rng)
    place_forest_belt(imported, rng)
    place_distant_city(imported, rng)

    rain_mat = make_rain_streak_material()
    place_weather_manager(mpc, rain_mat)

    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("all dirty packages saved")
    except Exception as e:
        warn("save failed: {}".format(e))
    log("DONE")


if __name__ == "__main__":
    main()
