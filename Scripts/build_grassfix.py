"""
build_grassfix.py  (stage 7)
============================
Grass placement + variety fix, and a villager-look refresh. Additive; does NOT
re-run earlier stages.

  1. T_GrassMask: imports Content/Village/Map/src/grass_mask.png (drawn from the
     real road splines / house footprints / landmarks / pond / cricket / kancha)
     as a clamped, linear 2048 mask. White = grass, gray = thin, black = none.
  2. Grass varieties: generates + imports SM_GrassShort (dense low tuft) and
     SM_GrassReed (tall golden reed) and points GT_VillageGrass at THREE mixed
     varieties (stage-6 SM_GrassClump + the two new ones).
  3. M_VillageGround rebuild: the grass density constant (1.0 everywhere — the
     reason grass grew on roads and inside buildings) is replaced by a
     world-aligned sample of T_GrassMask. The whole graph is rebuilt from the
     stage-5 recipe since UE Python cannot enumerate existing expressions.
  4. Villager refresh: re-sets Appearance on every VillagerNPC so construction
     re-runs VillagerLookUtil::Apply with the CURRENT C++ (clears overlay
     components baked by older code revisions).
  5. Verification captures: after the bootstrap finishes, a slate-tick state
     machine flies the viewport to road/lane/gurdwara/field/villager spots and
     saves screenshots to the session scratchpad.

RUN (auto via init_unreal.py when Saved/village_grassfix_done.txt is missing):
  py "D:/rural_games/rural_pardeep/Scripts/build_grassfix.py"
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_upgrade as _bu
from build_upgrade import *                      # noqa: F401,F403
from build_upgrade import _expr, _wetness_nodes  # import * skips _-prefixed names
import build_polish as _bp

import unreal


SRC_DIR = os.path.join(unreal.Paths.project_dir(), "Content", "Village", "Map", "src")
MASK_SRC = os.path.join(SRC_DIR, "grass_mask.png")
SHORT_OBJ = os.path.join(SRC_DIR, "grass_short.obj")
REED_OBJ = os.path.join(SRC_DIR, "grass_reed.obj")
MAP_DIR = "/Game/Village/Map"
MESH_DIR = "/Game/Village/Meshes"
MASK_TEX = MAP_DIR + "/T_GrassMask"
GROUND_MAT = MAT_DIR + "/M_VillageGround"
REED_MAT = MAT_DIR + "/M_VGGrassReed"
GT_PATH = "/Game/Village/GT_VillageGrass"
MASK_HALF = 70000.0        # must match make_grass_mask.ps1
SCRATCH = ("C:/Users/Evolet/AppData/Local/Temp/claude/d--rural-games-rural-pardeep/"
           "50b8e605-1607-4c91-a702-60eaa5ff3d19/scratchpad")


def log(msg):
    unreal.log("[build_grassfix] {}".format(msg))


def warn(msg):
    unreal.log_warning("[build_grassfix] {}".format(msg))


# --------------------------- grass mask texture -----------------------------

def import_mask():
    if not os.path.exists(MASK_SRC):
        warn("grass_mask.png missing at {} — mask skipped".format(MASK_SRC))
        return None
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", MASK_SRC)
    task.set_editor_property("destination_path", MAP_DIR)
    task.set_editor_property("destination_name", "T_GrassMask")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = EAL.load_asset(MASK_TEX)
    if tex is None:
        warn("T_GrassMask import failed")
        return None
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
    tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
    try:
        tex.set_editor_property("compression_settings",
                                unreal.TextureCompressionSettings.TC_GRAYSCALE)
    except Exception:
        pass
    try:
        tex.set_editor_property("mip_gen_settings",
                                unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property("never_stream", True)
    except Exception:
        pass
    EAL.save_asset(MASK_TEX)
    log("T_GrassMask imported (2048, linear, clamped)")
    return tex


# --------------------------- grass variety meshes ---------------------------

def write_variant_obj(path, z_up, seed, blades, hmin, hmax, leanmax,
                      w0min, w0max, disc_r, seg, bend):
    """Ribbon-strip grass clump like stage 6, parameterized per variety."""
    rng = random.Random(seed)
    verts, faces = [], []
    vi = 0
    for _b in range(blades):
        ba = rng.random() * 2 * math.pi
        br = math.sqrt(rng.random()) * disc_r
        bx, by = math.cos(ba) * br, math.sin(ba) * br
        la = ba + (rng.random() - 0.5) * 1.1
        dx, dy = math.cos(la), math.sin(la)
        px, py = -dy, dx
        H = hmin + rng.random() * (hmax - hmin)
        LEAN = leanmax * (0.4 + rng.random() * 0.6)
        W0 = w0min + rng.random() * (w0max - w0min)
        base = vi
        for s in range(seg + 1):
            t = s / float(seg)
            z = H * t
            drift = LEAN * (t ** bend)
            cx, cy = bx + dx * drift, by + dy * drift
            w = W0 * (1.0 - t * 0.92)
            for sx, sy in ((cx + px * w, cy + py * w), (cx - px * w, cy - py * w)):
                if z_up:
                    verts.append("v {:.2f} {:.2f} {:.2f}".format(sx, sy, z))
                else:
                    verts.append("v {:.2f} {:.2f} {:.2f}".format(sx, z, -sy))
                vi += 1
        for s in range(seg):
            a = base + s * 2 + 1
            faces.append("f {} {} {}".format(a, a + 1, a + 3))
            faces.append("f {} {} {}".format(a, a + 3, a + 2))
    with open(path, "w") as f:
        f.write("o GrassClump\n")
        f.write("\n".join(verts))
        f.write("\nusemtl grass\n")
        f.write("\n".join(faces))
        f.write("\n")


def _import_variant(path, name):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", MESH_DIR)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return EAL.load_asset(MESH_DIR + "/" + name)


def _variant_mesh(name, gen_params, min_z):
    """Write+import one variant OBJ with the stage-6 flat-import self-heal."""
    path = gen_params[0]
    write_variant_obj(path, True, *gen_params[1:])
    mesh = _import_variant(path, name)
    if mesh is None:
        return None
    try:
        bb = mesh.get_bounding_box()
        if (bb.max.z - bb.min.z) < min_z:
            log("{} imported flat — regenerating with swapped axes".format(name))
            write_variant_obj(path, False, *gen_params[1:])
            mesh = _import_variant(path, name)
    except Exception as e:
        warn("{} bounds probe failed ({}) — keeping import".format(name, e))
    return mesh


def make_reed_material(mpc):
    """Golden dry-grass version of the stage-6 leaf material."""
    if EAL.does_asset_exist(REED_MAT):
        return EAL.load_asset(REED_MAT)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGGrassReed", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("two_sided", True)

    lo = _expr(mat, unreal.MaterialExpressionConstant3Vector, -700, -100)
    lo.set_editor_property("constant", unreal.LinearColor(0.28, 0.24, 0.08, 1.0))
    hi = _expr(mat, unreal.MaterialExpressionConstant3Vector, -700, 80)
    hi.set_editor_property("constant", unreal.LinearColor(0.55, 0.46, 0.15, 1.0))
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
    rough.set_editor_property("r", 0.85)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    # taller stalks sway more: same MPC recipe, bigger amplitude + height range
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
    tconst.set_editor_property("r", 1.3)
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
    hrange.set_editor_property("r", 110.0)
    MEL.connect_material_expressions(hz, "", hdiv, "A")
    MEL.connect_material_expressions(hrange, "", hdiv, "B")
    hclamp = _expr(mat, unreal.MaterialExpressionClamp, x0 + 720, y0 + 640)
    MEL.connect_material_expressions(hdiv, "", hclamp, "")
    wind = _expr(mat, unreal.MaterialExpressionCollectionParameter, x0 + 720, y0 + 420)
    wind.set_editor_property("collection", mpc)
    wind.set_editor_property("parameter_name", "WindIntensity")
    amp = _expr(mat, unreal.MaterialExpressionConstant, x0 + 720, y0 + 520)
    amp.set_editor_property("r", 22.0)
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
    EAL.save_asset(REED_MAT)
    log("created M_VGGrassReed (golden, tall sway)")
    return mat


def _set_mesh_material(mesh, mi, name):
    try:
        mesh.set_editor_property("static_materials", [
            unreal.StaticMaterial(material_interface=mi,
                                  material_slot_name="grass")])
    except Exception:
        try:
            unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_lod_material_slot(
                mesh, mi, 0, "grass")
        except Exception as e:
            warn("{} material assignment failed: {}".format(name, e))


def _variety(mesh, density, smin, smax):
    d = unreal.PerPlatformFloat()
    d.set_editor_property("default", float(density))
    s = unreal.FloatInterval()
    s.set_editor_property("min", smin)
    s.set_editor_property("max", smax)
    v = unreal.GrassVariety()
    v.set_editor_property("grass_mesh", mesh)
    v.set_editor_property("grass_density", d)
    try:
        v.set_editor_property("scaling", unreal.GrassScaling.UNIFORM)
    except Exception:
        pass
    v.set_editor_property("scale_x", s)
    v.set_editor_property("scale_y", s)
    v.set_editor_property("scale_z", s)
    v.set_editor_property("random_rotation", True)
    v.set_editor_property("align_to_surface", True)
    return v


def grass_varieties(mpc):
    clump = EAL.load_asset(MESH_DIR + "/SM_GrassClump")
    leaf_mat = _bp.make_grass_leaf_material(mpc)   # idempotent: returns existing
    reed_mat = make_reed_material(mpc)

    short = _variant_mesh("SM_GrassShort",
                          (SHORT_OBJ, 77, 18, 14.0, 30.0, 9.0, 2.8, 4.2, 24.0, 4, 2.0),
                          10.0)
    reed = _variant_mesh("SM_GrassReed",
                         (REED_OBJ, 91, 7, 78.0, 118.0, 14.0, 1.8, 2.8, 14.0, 6, 2.4),
                         40.0)
    if short:
        _set_mesh_material(short, leaf_mat, "SM_GrassShort")
        EAL.save_asset(MESH_DIR + "/SM_GrassShort")
    if reed:
        _set_mesh_material(reed, reed_mat, "SM_GrassReed")
        EAL.save_asset(MESH_DIR + "/SM_GrassReed")

    gt = EAL.load_asset(GT_PATH)
    if gt is None:
        warn("GT_VillageGrass missing — varieties skipped")
        return
    varieties = []
    if clump:
        varieties.append(_variety(clump, 55.0, 0.65, 1.1))    # tall leafy (stage 6)
    if short:
        varieties.append(_variety(short, 165.0, 0.8, 1.35))   # dense low fill
    if reed:
        varieties.append(_variety(reed, 10.0, 0.8, 1.4))      # sparse golden accents
    if not varieties:
        warn("no grass meshes available — GT left unchanged")
        return
    gt.set_editor_property("grass_varieties", varieties)
    EAL.save_asset(GT_PATH)
    log("GT_VillageGrass -> {} mixed varieties".format(len(varieties)))


# ------------------------- ground material rebuild --------------------------

def rebuild_ground(mpc, mask_tex):
    """delete_all + rebuild: stage-5 base colour/roughness/wetness recipe, with
    the grass output density driven by the world-aligned T_GrassMask sample."""
    if not EAL.does_asset_exist(GROUND_MAT):
        warn("M_VillageGround missing — rebuild skipped")
        return
    mat = EAL.load_asset(GROUND_MAT)
    MEL.delete_all_material_expressions(mat)

    # ---- base colour (green_ground recipe) ----
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

    # ---- roughness (green_ground recipe) ----
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

    # ---- grass output: density = world-aligned mask sample ----
    gt = EAL.load_asset(GT_PATH)
    grass_out = _expr(mat, unreal.MaterialExpressionLandscapeGrassOutput, 300, 2600)
    gi = unreal.GrassInput()
    gi.set_editor_property("name", "VillageGrass")
    gi.set_editor_property("grass_type", gt)
    grass_out.set_editor_property("grass_types", [gi])

    if mask_tex is not None:
        wpos = _expr(mat, unreal.MaterialExpressionWorldPosition, -700, 3300)
        wxy = _expr(mat, unreal.MaterialExpressionComponentMask, -520, 3300)
        wxy.set_editor_property("r", True); wxy.set_editor_property("g", True)
        wxy.set_editor_property("b", False); wxy.set_editor_property("a", False)
        MEL.connect_material_expressions(wpos, "", wxy, "")
        half2 = _expr(mat, unreal.MaterialExpressionConstant2Vector, -520, 3400)
        half2.set_editor_property("r", MASK_HALF)
        half2.set_editor_property("g", MASK_HALF)
        uadd = _expr(mat, unreal.MaterialExpressionAdd, -340, 3320)
        MEL.connect_material_expressions(wxy, "", uadd, "A")
        MEL.connect_material_expressions(half2, "", uadd, "B")
        usize = _expr(mat, unreal.MaterialExpressionConstant, -340, 3420)
        usize.set_editor_property("r", MASK_HALF * 2.0)
        udiv = _expr(mat, unreal.MaterialExpressionDivide, -160, 3340)
        MEL.connect_material_expressions(uadd, "", udiv, "A")
        MEL.connect_material_expressions(usize, "", udiv, "B")
        ts = _expr(mat, unreal.MaterialExpressionTextureSample, 40, 3320)
        ts.set_editor_property("texture", mask_tex)
        try:
            cs = mask_tex.get_editor_property("compression_settings")
            if cs == unreal.TextureCompressionSettings.TC_GRAYSCALE:
                ts.set_editor_property(
                    "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
            else:
                ts.set_editor_property(
                    "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        except Exception:
            pass
        MEL.connect_material_expressions(udiv, "", ts, "UVs")
        try:
            MEL.connect_material_expressions(ts, "R", grass_out, "VillageGrass")
        except Exception:
            MEL.connect_material_expressions(ts, "R", grass_out, "")
    else:
        dcon = _expr(mat, unreal.MaterialExpressionConstant, 40, 3320)
        dcon.set_editor_property("r", 1.0)
        try:
            MEL.connect_material_expressions(dcon, "", grass_out, "VillageGrass")
        except Exception:
            MEL.connect_material_expressions(dcon, "", grass_out, "")

    for tag in ("vg3_wet", "vg5_green", "vg5_grass", "vg7_mask"):
        try:
            EAL.set_metadata_tag(mat, tag, "1")
        except Exception:
            pass
    MEL.recompile_material(mat)
    EAL.save_asset(GROUND_MAT)
    try:
        unreal.SystemLibrary.execute_console_command(_bu._WORLD, "grass.FlushCache")
    except Exception:
        pass
    log("M_VillageGround rebuilt — grass density now mask-driven")


# ---------------------------- villager refresh ------------------------------

def refresh_villagers():
    if not hasattr(unreal, "VillagerNPC"):
        warn("VillagerNPC class not loaded — refresh skipped")
        return
    n = 0
    for actor in EAS.get_all_level_actors():
        if not isinstance(actor, unreal.VillagerNPC):
            continue
        try:
            app = actor.get_editor_property("appearance")
            actor.set_editor_property("appearance", app)   # forces construction re-run
            n += 1
        except Exception as e:
            warn("refresh {} failed: {}".format(actor.get_actor_label(), e))
    log("{} villagers re-applied their look with current C++".format(n))


# ------------------------- verification captures ----------------------------

_cap = {"i": 0, "t": 0.0, "phase": "move", "handle": None, "shots": []}


def _rot(pitch, yaw):
    r = unreal.Rotator()
    r.pitch = pitch
    r.yaw = yaw
    r.roll = 0.0
    return r


def _villager_shot():
    """Camera in front of the first villager whose label contains 'anpreet'
    (Manpreet), else any VillagerNPC."""
    target = None
    for actor in EAS.get_all_level_actors():
        try:
            if not isinstance(actor, unreal.VillagerNPC):
                continue
            if "anpreet" in actor.get_actor_label().lower():
                target = actor
                break
            if target is None:
                target = actor
        except Exception:
            continue
    if target is None:
        return None
    loc = target.get_actor_location()
    yaw = target.get_actor_rotation().yaw
    r = math.radians(yaw)
    cam = unreal.Vector(loc.x + math.cos(r) * 260.0,
                        loc.y + math.sin(r) * 260.0, loc.z + 55.0)
    return cam, _rot(-8.0, yaw + 180.0)


def _cap_tick(dt):
    st = _cap
    shots = st["shots"]
    if st["i"] >= len(shots):
        return
    name, cam = shots[st["i"]]
    if st["phase"] == "move":
        try:
            pos = cam() if callable(cam) else cam
            if pos is None:
                raise ValueError("no camera target")
            UES.set_level_viewport_camera_info(pos[0], pos[1])
            st["phase"] = "settle"
            st["t"] = 0.0
        except Exception as e:
            unreal.log_warning("[build_grassfix] capture {} skipped: {}".format(name, e))
            st["i"] += 1
        return
    st["t"] += dt
    if st["phase"] == "settle" and st["t"] > 5.0:
        path = SCRATCH + "/" + name
        try:
            unreal.AutomationLibrary.take_high_res_screenshot(1760, 990, path)
            unreal.log("[build_grassfix] capture requested: {}".format(name))
        except Exception as e:
            unreal.log_warning("[build_grassfix] capture {} failed: {}".format(name, e))
        st["phase"] = "wait"
        st["t"] = 0.0
    elif st["phase"] == "wait" and st["t"] > 3.0:
        st["i"] += 1
        st["phase"] = "move"
        st["t"] = 0.0
        if st["i"] >= len(shots):
            try:
                with open(os.path.join(SCRATCH.replace("/", os.sep),
                                       "s7_captures_done.txt"), "w") as f:
                    f.write("done")
            except Exception:
                pass
            unreal.log("[build_grassfix] ALL CAPTURES DONE")
            if st["handle"] is not None:
                unreal.unregister_slate_post_tick_callback(st["handle"])


def schedule_captures():
    _cap["shots"] = [
        ("s7_road.png",     (unreal.Vector(0.0, 17500.0, 800.0), _rot(-14.0, -90.0))),
        ("s7_lane.png",     (unreal.Vector(0.0, 6800.0, 520.0), _rot(-16.0, -90.0))),
        ("s7_gurdwara.png", (unreal.Vector(-1500.0, -11300.0, 700.0), _rot(-12.0, -90.0))),
        ("s7_field.png",    (unreal.Vector(-24000.0, -24000.0, 900.0), _rot(-18.0, -135.0))),
        ("s7_villager.png", _villager_shot),
    ]
    _cap["handle"] = unreal.register_slate_post_tick_callback(_cap_tick)
    log("verification captures scheduled ({} shots)".format(len(_cap["shots"])))


# --------------------------------- driver -----------------------------------

def main():
    _bu._WORLD = _bu.UES.get_editor_world()
    if _bu._WORLD is None or "Lvl_Village" not in _bu._WORLD.get_name():
        warn("Lvl_Village not loaded — grassfix aborted")
        return
    mpc = EAL.load_asset(MPC_PATH)

    mask_tex = None
    try:
        mask_tex = import_mask()
    except Exception as e:
        warn("import_mask failed: {}".format(e))
    for name, fn in (("grass_varieties", lambda: grass_varieties(mpc)),
                     ("rebuild_ground", lambda: rebuild_ground(mpc, mask_tex)),
                     ("refresh_villagers", refresh_villagers)):
        try:
            fn()
        except Exception as e:
            warn("{} failed: {}".format(name, e))

    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("grassfix: all dirty packages saved")
    except Exception as e:
        warn("save failed: {}".format(e))

    try:
        schedule_captures()
    except Exception as e:
        warn("capture scheduling failed: {}".format(e))
    log("GRASSFIX COMPLETE")


if __name__ == "__main__":
    main()
