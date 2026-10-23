"""
build_homes.py  (stage 9)
=========================
Turns the flat-coloured box houses into realistic Punjab-doaba homes:

  * TEXTURED walls — tiling red-brick (older havelis) or mottled painted
    plaster (newer kothis), world-projected so brick size is consistent.
  * GLASS windows — translucent panes with frames, steel grilles and sills,
    replacing the old flat dark-cube "fake" windows.
  * Fine architectural detail — stone plinth course, corner pilasters, a
    cornice string-course, a front veranda (pillars + slab), parapet coping,
    a rooftop mumty + water tank + DTH dish, and a paneled wood door.

It KEEPS the carefully tuned hollow interiors / doorways / furniture from the
stage-3 (v3) houses: it re-skins the existing wall parts and ADDS detail actors
(prefixed VG9_) rather than rebuilding the shells. Idempotent + marker-guarded.

RUN (auto via init_unreal.py when Saved/village_homes_done.txt is missing).
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_upgrade as _bu
from build_upgrade import *                      # noqa: F401,F403
from build_upgrade import _expr

import unreal


SRC_DIR = os.path.join(unreal.Paths.project_dir(), "Content", "Village", "Map", "src")
TEX_DIR = "/Game/Village/Map"
HMAT = "/Game/Village/Materials"


def log(m):
    unreal.log("[build_homes] {}".format(m))


def warn(m):
    unreal.log_warning("[build_homes] {}".format(m))


# ============================== textures ==================================

def imp_tex(fname, dest_name, srgb=True):
    dst = TEX_DIR + "/" + dest_name
    src = os.path.join(SRC_DIR, fname)
    if not os.path.exists(src):
        warn("texture missing: {}".format(src))
        return EAL.load_asset(dst) if EAL.does_asset_exist(dst) else None
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", src)
    task.set_editor_property("destination_path", TEX_DIR)
    task.set_editor_property("destination_name", dest_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = EAL.load_asset(dst)
    if tex:
        try:
            tex.set_editor_property("srgb", srgb)
            EAL.save_asset(dst)
        except Exception:
            pass
    return tex


# ============================== materials =================================

def _mat(name):
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, HMAT, unreal.Material, unreal.MaterialFactoryNew())


def _world_planar_uv(mat, kx, ky, x=-1100, y=260):
    """UV = ((worldX+worldY)*kx, worldZ*ky) — consistent texel size on any
    axis-aligned vertical wall regardless of the cube's non-uniform scale."""
    wp = _expr(mat, unreal.MaterialExpressionWorldPosition, x, y)
    ones = _expr(mat, unreal.MaterialExpressionConstant3Vector, x, y + 140)
    ones.set_editor_property("constant", unreal.LinearColor(1.0, 1.0, 0.0, 0.0))
    dot = _expr(mat, unreal.MaterialExpressionDotProduct, x + 200, y)
    MEL.connect_material_expressions(wp, "", dot, "A")
    MEL.connect_material_expressions(ones, "", dot, "B")
    ku = _expr(mat, unreal.MaterialExpressionConstant, x + 200, y + 140)
    ku.set_editor_property("r", kx)
    mu = _expr(mat, unreal.MaterialExpressionMultiply, x + 380, y)
    MEL.connect_material_expressions(dot, "", mu, "A")
    MEL.connect_material_expressions(ku, "", mu, "B")
    zc = _expr(mat, unreal.MaterialExpressionComponentMask, x + 200, y + 240)
    zc.set_editor_property("r", False); zc.set_editor_property("g", False)
    zc.set_editor_property("b", True); zc.set_editor_property("a", False)
    MEL.connect_material_expressions(wp, "", zc, "")
    kv = _expr(mat, unreal.MaterialExpressionConstant, x + 200, y + 340)
    kv.set_editor_property("r", ky)
    mv = _expr(mat, unreal.MaterialExpressionMultiply, x + 380, y + 240)
    MEL.connect_material_expressions(zc, "", mv, "A")
    MEL.connect_material_expressions(kv, "", mv, "B")
    app = _expr(mat, unreal.MaterialExpressionAppendVector, x + 560, y + 120)
    MEL.connect_material_expressions(mu, "", app, "A")
    MEL.connect_material_expressions(mv, "", app, "B")
    return app


def mat_plaster_parent():
    """Textured plaster with a Color VectorParameter so MIs can recolour it."""
    path = HMAT + "/M_VGPlasterTex"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = _mat("M_VGPlasterTex")
    tex = EAL.load_asset(TEX_DIR + "/T_Plaster")
    ts = _expr(mat, unreal.MaterialExpressionTextureSample, -700, -40)
    if tex:
        ts.set_editor_property("texture", tex)
    col = _expr(mat, unreal.MaterialExpressionVectorParameter, -700, 220)
    col.set_editor_property("parameter_name", "Color")
    col.set_editor_property("default_value", unreal.LinearColor(0.9, 0.87, 0.78, 1.0))
    mul = _expr(mat, unreal.MaterialExpressionMultiply, -420, 40)
    MEL.connect_material_expressions(ts, "RGB", mul, "A")
    MEL.connect_material_expressions(col, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = _expr(mat, unreal.MaterialExpressionConstant, -420, 260)
    r.set_editor_property("r", 0.86)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("built M_VGPlasterTex")
    return mat


def plaster_mi(name, rgb):
    parent = mat_plaster_parent()
    path = HMAT + "/MI_PT_" + name
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    inst = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "MI_PT_" + name, HMAT, unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew())
    inst.set_editor_property("parent", parent)
    MEL.set_material_instance_vector_parameter_value(
        inst, "Color", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    MEL.update_material_instance(inst)
    EAL.save_asset(path)
    return inst


def mat_brick():
    path = HMAT + "/M_VGBrickTex"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = _mat("M_VGBrickTex")
    tex = EAL.load_asset(TEX_DIR + "/T_Brick")
    ts = _expr(mat, unreal.MaterialExpressionTextureSample, -420, -40)
    if tex:
        ts.set_editor_property("texture", tex)
    uv = _world_planar_uv(mat, 1.0 / 210.0, 1.0 / 150.0)
    MEL.connect_material_expressions(uv, "", ts, "UVs")
    MEL.connect_material_property(ts, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    r = _expr(mat, unreal.MaterialExpressionConstant, -420, 300)
    r.set_editor_property("r", 0.92)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("built M_VGBrickTex")
    return mat


def mat_wood():
    path = HMAT + "/M_VGWoodTex"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = _mat("M_VGWoodTex")
    tex = EAL.load_asset(TEX_DIR + "/T_Wood")
    ts = _expr(mat, unreal.MaterialExpressionTextureSample, -420, -40)
    if tex:
        ts.set_editor_property("texture", tex)
    tc = _expr(mat, unreal.MaterialExpressionTextureCoordinate, -640, -40)
    tc.set_editor_property("u_tiling", 1.0); tc.set_editor_property("v_tiling", 1.0)
    MEL.connect_material_expressions(tc, "", ts, "UVs")
    MEL.connect_material_property(ts, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    r = _expr(mat, unreal.MaterialExpressionConstant, -420, 300)
    r.set_editor_property("r", 0.55)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("built M_VGWoodTex")
    return mat


def mat_glass():
    path = HMAT + "/M_VGGlass"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = _mat("M_VGGlass")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    try:
        mat.set_editor_property(
            "translucency_lighting_mode",
            unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    except Exception:
        pass
    tint = _expr(mat, unreal.MaterialExpressionConstant3Vector, -560, -40)
    tint.set_editor_property("constant", unreal.LinearColor(0.42, 0.55, 0.58, 1.0))
    MEL.connect_material_property(tint, "", unreal.MaterialProperty.MP_BASE_COLOR)
    spec = _expr(mat, unreal.MaterialExpressionConstant, -560, 120)
    spec.set_editor_property("r", 1.0)
    MEL.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)
    rough = _expr(mat, unreal.MaterialExpressionConstant, -560, 200)
    rough.set_editor_property("r", 0.05)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    # fresnel-driven opacity: glassy centre, brighter reflective edges
    fr = _expr(mat, unreal.MaterialExpressionFresnel, -560, 300)
    fr.set_editor_property("exponent", 2.5)
    fr.set_editor_property("base_reflect_fraction", 0.08)
    lo = _expr(mat, unreal.MaterialExpressionConstant, -560, 420)
    lo.set_editor_property("r", 0.16)
    hi = _expr(mat, unreal.MaterialExpressionConstant, -560, 500)
    hi.set_editor_property("r", 0.6)
    op = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -340, 360)
    MEL.connect_material_expressions(lo, "", op, "A")
    MEL.connect_material_expressions(hi, "", op, "B")
    MEL.connect_material_expressions(fr, "", op, "Alpha")
    MEL.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("built M_VGGlass")
    return mat


def mat_noise(name, lo_rgb, hi_rgb, rough, scale=0.03):
    path = HMAT + "/" + name
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = _mat(name)
    lo = _expr(mat, unreal.MaterialExpressionConstant3Vector, -640, -40)
    lo.set_editor_property("constant", unreal.LinearColor(lo_rgb[0], lo_rgb[1], lo_rgb[2], 1.0))
    hi = _expr(mat, unreal.MaterialExpressionConstant3Vector, -640, 120)
    hi.set_editor_property("constant", unreal.LinearColor(hi_rgb[0], hi_rgb[1], hi_rgb[2], 1.0))
    n = _expr(mat, unreal.MaterialExpressionNoise, -640, 280)
    n.set_editor_property("scale", scale)
    n.set_editor_property("output_min", 0.0); n.set_editor_property("output_max", 1.0)
    lp = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -400, 20)
    MEL.connect_material_expressions(lo, "", lp, "A")
    MEL.connect_material_expressions(hi, "", lp, "B")
    MEL.connect_material_expressions(n, "", lp, "Alpha")
    MEL.connect_material_property(lp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = _expr(mat, unreal.MaterialExpressionConstant, -400, 240)
    r.set_editor_property("r", rough)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("built " + name)
    return mat


def mat_metal(name, rgb, rough):
    path = HMAT + "/" + name
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = _mat(name)
    c = _expr(mat, unreal.MaterialExpressionConstant3Vector, -560, -40)
    c.set_editor_property("constant", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    m = _expr(mat, unreal.MaterialExpressionConstant, -560, 120)
    m.set_editor_property("r", 1.0)
    MEL.connect_material_property(m, "", unreal.MaterialProperty.MP_METALLIC)
    r = _expr(mat, unreal.MaterialExpressionConstant, -560, 200)
    r.set_editor_property("r", rough)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("built " + name)
    return mat


# ============================== geometry ==================================

T = 14.0
FH = 300.0
FOLDER = "Village/Houses"


def build_mats():
    imp_tex("tex_brick.png", "T_Brick", True)
    imp_tex("tex_wood.png", "T_Wood", True)
    imp_tex("tex_plaster.png", "T_Plaster", True)
    m = {}
    m["brick"] = mat_brick()
    m["wood"] = mat_wood()
    m["glass"] = mat_glass()
    m["stone"] = mat_noise("M_VGStonePlinth", (0.42, 0.41, 0.40), (0.58, 0.57, 0.55), 0.82, 0.05)
    m["steel"] = mat_metal("M_VGSteel", (0.60, 0.62, 0.66), 0.34)
    m["iron"] = mat_metal("M_VGIron", (0.09, 0.09, 0.11), 0.42)
    m["tank"] = mat_metal("M_VGTankBlue", (0.10, 0.16, 0.30), 0.5)
    # trim + plaster colour instances
    trims = [("Ivory", (0.95, 0.93, 0.86)), ("Cream", (0.93, 0.89, 0.79)),
             ("PaleBlue", (0.72, 0.80, 0.88)), ("Sage", (0.80, 0.85, 0.74)),
             ("Peach", (0.93, 0.82, 0.70)), ("Grey", (0.78, 0.78, 0.76))]
    m["plaster"] = [plaster_mi(n, c) for n, c in trims]
    m["trim"] = plaster_mi("TrimWhite", (0.97, 0.96, 0.92))
    m["accent"] = plaster_mi("AccentMaroon", (0.42, 0.16, 0.14))
    return m


WALL = set(["_fL", "_fR", "_fLintel", "_back", "_right", "_lF", "_lB",
            "_lSill", "_lTop", "_up"])
PARAPET = set(["_pN", "_pS", "_pE", "_pW"])
FAKEWIN = set(["_wf1", "_wf2", "_wu1", "_wu2"])


def spawn(mesh, mi, label, loc, scale, rot):
    return spawn_mesh(mesh, mi, label, FOLDER, loc, scale, rot)


def reskin_and_augment(plot, parts, m, rng):
    x, y, yaw, w, d, storeys, idx = plot
    w = max(w, 760.0); d = max(d, 640.0)
    h = storeys * FH
    gz = ground_z(x, y)
    r = math.radians(yaw)

    def local(lx, ly, lz):
        return unreal.Vector(x + lx * math.cos(r) - ly * math.sin(r),
                             y + lx * math.sin(r) + ly * math.cos(r), gz + lz)

    def add(mesh, mi, suffix, lx, ly, lz, scale, eyaw=0.0, pitch=0.0):
        return spawn(mesh, mi, "VG9_House_{:02d}{}".format(idx, suffix),
                     local(lx, ly, lz), scale, (pitch, yaw + eyaw, 0.0))

    # brick vs plaster house
    is_brick = (idx % 3 == 0)
    wall_mat = m["brick"] if is_brick else rng.choice(m["plaster"])
    trim = m["trim"] if not is_brick else m["accent"]

    # --- re-skin existing shell parts ---
    for suffix, actor in parts.items():
        try:
            comp = actor.static_mesh_component
        except Exception:
            continue
        if suffix in WALL:
            comp.set_material(0, wall_mat)
        elif suffix in PARAPET:
            comp.set_material(0, wall_mat)
        elif suffix == "_plinth":
            comp.set_material(0, m["stone"])
        elif suffix == "_doorleaf":
            comp.set_material(0, m["wood"])
        elif suffix == "_tank":
            comp.set_material(0, m["tank"])
        elif suffix in FAKEWIN:
            try:
                EAS.destroy_actor(actor)
            except Exception:
                pass

    z0 = 30.0
    top = z0 + h + 14 + (7 if storeys == 1 else 14)
    door_w, door_h = 150.0, 220.0

    # --- stone plinth skirt + coping lip ---
    add(CUBE, m["stone"], "_skirt", 0, 0, 22, ((w + 26) / 100, (d + 26) / 100, 0.44))
    add(CUBE, trim, "_skirtcap", 0, 0, 46, ((w + 34) / 100, (d + 34) / 100, 0.06))

    # --- corner pilasters (full height) ---
    ph = (top - z0) / 100.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            add(CUBE, trim, "_pil{}{}".format(sx, sy),
                sx * (w / 2 - 4), sy * (d / 2 - 4), z0 + (top - z0) / 2,
                (0.26, 0.26, ph))

    # --- cornice string-course just under the roof line ---
    add(CUBE, trim, "_cornice", 0, 0, top - 6, ((w + 30) / 100, (d + 30) / 100, 0.12))
    # mid string-course between storeys (2-storey only)
    if storeys == 2:
        add(CUBE, trim, "_band", 0, 0, z0 + FH + 10, ((w + 18) / 100, (d + 18) / 100, 0.07))

    # --- parapet coping cap ---
    for s, (lx, ly, sx, sy) in (
            ("N", (0, d / 2 - 10, w / 100 + 0.14, 0.28)),
            ("S", (0, -d / 2 + 10, w / 100 + 0.14, 0.28)),
            ("E", (w / 2 - 10, 0, 0.28, d / 100 - 0.1)),
            ("W", (-w / 2 + 10, 0, 0.28, d / 100 - 0.1))):
        add(CUBE, trim, "_cop" + s, lx, ly, top + 80, (sx, sy, 0.07))
    # parapet balusters along the front
    nb = max(4, int(w / 90))
    for i in range(nb + 1):
        bx = -w / 2 + 12 + i * (w - 24) / nb
        add(CYLINDER, trim, "_bal{}".format(i), bx, -d / 2 + 12, top + 55,
            (0.08, 0.08, 0.42))

    # --- front veranda: 2 pillars + flat slab over the entrance ---
    vy = -d / 2 - 150.0
    for sx in (-1, 1):
        add(CUBE, trim, "_vcol{}".format(sx), sx * (w / 2 - 46), vy, z0 + FH / 2,
            (0.3, 0.3, FH / 100))
        # simple capital
        add(CUBE, trim, "_vcap{}".format(sx), sx * (w / 2 - 46), vy, z0 + FH - 8,
            (0.42, 0.42, 0.1))
    add(CUBE, wall_mat, "_vslab", 0, -d / 2 - 78, z0 + FH + 12,
        (w / 100 + 0.1, 1.9, 0.14))
    add(CUBE, trim, "_vfascia", 0, vy - 70, z0 + FH + 4, (w / 100 + 0.14, 0.12, 0.2))
    # veranda floor step
    add(CUBE, m["stone"], "_vstep", 0, -d / 2 - 60, z0 - 8, (w / 100 - 0.2, 1.3, 0.16))

    # --- door frame around the (already open) doorway ---
    add(CUBE, m["wood"], "_dframeL", -door_w / 2 - 7, -d / 2 + 2, z0 + door_h / 2,
        (0.14, 0.16, door_h / 100))
    add(CUBE, m["wood"], "_dframeR", door_w / 2 + 7, -d / 2 + 2, z0 + door_h / 2,
        (0.14, 0.16, door_h / 100))
    add(CUBE, m["wood"], "_dframeT", 0, -d / 2 + 2, z0 + door_h + 8,
        (door_w / 100 + 0.28, 0.16, 0.16))
    # glazed transom above the door
    add(CUBE, m["glass"], "_dtransom", 0, -d / 2 + 4, z0 + door_h + 22,
        (door_w / 100, 0.04, 0.2))

    # --- glazed windows on the front face (replacing the fake shutters) ---
    def front_window(px, pz, ww=64.0, wh=92.0, tag=""):
        fy = -d / 2 - 1.0
        # frame
        add(CUBE, trim, "_wfr" + tag, px, fy + 2, pz, (ww / 100 + 0.2, 0.14, wh / 100 + 0.2))
        # recessed glass
        add(CUBE, m["glass"], "_wgl" + tag, px, fy + 6, pz, (ww / 100, 0.04, wh / 100))
        # sill
        add(CUBE, m["stone"], "_wsl" + tag, px, fy + 1, pz - wh / 2 - 6,
            (ww / 100 + 0.28, 0.2, 0.1))
        # grille: 2 vertical + 1 horizontal iron bars
        for k, gx in enumerate((-ww / 4, ww / 4)):
            add(CUBE, m["iron"], "_wgv{}{}".format(tag, k), px + gx, fy + 4, pz,
                (0.03, 0.03, wh / 100))
        add(CUBE, m["iron"], "_wgh" + tag, px, fy + 4, pz, (ww / 100, 0.03, 0.03))

    front_window(-w / 4 - 12, z0 + 190, tag="g1")
    front_window(w / 4 + 12, z0 + 190, tag="g2")
    if storeys == 2:
        front_window(-w / 4, z0 + FH + 190, tag="u1")
        front_window(w / 4, z0 + FH + 190, tag="u2")

    # --- glaze the real left-wall window opening (v3 leaves it empty) ---
    lx = -w / 2 + T / 2
    add(CUBE, m["glass"], "_lglass", lx, 0, z0 + 169, (0.04, 0.92, 0.94))
    for k, gz2 in enumerate((140, 170, 200)):
        add(CUBE, m["iron"], "_lgh{}".format(k), lx + 2, 0, z0 + gz2, (0.03, 0.9, 0.02))
    add(CUBE, m["stone"], "_lsill", lx - 2, 0, z0 + 118, (0.22, 1.06, 0.08))

    # --- rooftop: mumty (stair head) + tank on stand + DTH dish ---
    mx, my = w / 2 - 150, d / 2 - 150
    add(CUBE, wall_mat, "_mumty", mx, my, top + 130, (2.4, 2.6, 1.3))
    add(CUBE, trim, "_mumtycap", mx, my, top + 200, (2.7, 2.9, 0.08))
    add(CUBE, m["wood"], "_mumtydoor", mx - 118, my, top + 90, (0.06, 0.7, 1.0))
    # water tank on a short steel stand
    tx, ty = -w / 2 + 150, d / 2 - 150
    for c, (sx, sy) in enumerate(((-40, -40), (40, -40), (-40, 40), (40, 40))):
        add(CUBE, m["steel"], "_tst{}".format(c), tx + sx, ty + sy, top + 40, (0.05, 0.05, 0.8))
    add(CYLINDER, m["tank"], "_wtank", tx, ty, top + 96, (1.15, 1.15, 0.62))
    # DTH dish near the front parapet
    dish = add(CYLINDER, m["steel"], "_dish", w / 4, -d / 2 + 40, top + 70,
               (0.7, 0.7, 0.04), pitch=54.0)


# ============================ verification ================================

SCRATCH = ("C:/Users/Evolet/AppData/Local/Temp/claude/d--rural-games-rural-pardeep/"
           "50b8e605-1607-4c91-a702-60eaa5ff3d19/scratchpad")
_cap = {"i": 0, "t": 0.0, "phase": "move", "handle": None, "shots": []}


def _rot(p, yv):
    rr = unreal.Rotator(); rr.pitch = p; rr.yaw = yv; rr.roll = 0.0
    return rr


def _cap_tick(dt):
    st = _cap
    if st["i"] >= len(st["shots"]):
        return
    name, cam, look = st["shots"][st["i"]]
    if st["phase"] == "move":
        try:
            UES.set_level_viewport_camera_info(cam, look)
        except Exception as e:
            warn("cam {} failed: {}".format(name, e))
        st["phase"] = "settle"; st["t"] = 0.0
        return
    st["t"] += dt
    if st["phase"] == "settle" and st["t"] > 6.0:
        try:
            unreal.AutomationLibrary.take_high_res_screenshot(1760, 990, SCRATCH + "/" + name)
            log("capture requested: {}".format(name))
        except Exception as e:
            warn("capture {} failed: {}".format(name, e))
        st["phase"] = "cool"; st["t"] = 0.0
    elif st["phase"] == "cool" and st["t"] > 26.0:
        st["i"] += 1; st["phase"] = "move"; st["t"] = 0.0
        if st["i"] >= len(st["shots"]):
            try:
                with open(os.path.join(SCRATCH.replace("/", os.sep), "homes_caps_done.txt"), "w") as f:
                    f.write("done")
            except Exception:
                pass
            log("ALL HOME CAPTURES DONE")
            if st["handle"] is not None:
                unreal.unregister_slate_post_tick_callback(st["handle"])


def schedule_captures(plots):
    if not plots:
        return
    plots = sorted(plots, key=lambda p: (p[0], p[1]))
    picks = [plots[len(plots) // 2], plots[len(plots) // 3]]
    shots = []
    for j, p in enumerate(picks):
        x, y, yaw, w, d, st_, idx = p
        gz = ground_z(x, y)
        r = math.radians(yaw)
        # camera in front (-Y local) of the house
        fx = -math.sin(r); fy = math.cos(r)   # local +Y in world
        cam = unreal.Vector(x - fx * 620, y - fy * 620, gz + 250)
        look = _rot(-10.0, math.degrees(math.atan2((y) - cam.y, (x) - cam.x)))
        shots.append(("t9_house{}.png".format(j), cam, look))
    # wide street shot
    xs = [p[0] for p in plots]; ys = [p[1] for p in plots]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    shots.append(("t9_street.png",
                  unreal.Vector(cx - 1400, cy + 1400, ground_z(cx, cy) + 700),
                  _rot(-18.0, -45.0)))
    _cap["shots"] = shots
    _cap["handle"] = unreal.register_slate_post_tick_callback(_cap_tick)
    log("home captures scheduled ({})".format(len(shots)))


# ============================== driver ====================================

def main():
    _bu._WORLD = _bu.UES.get_editor_world()
    if _bu._WORLD is None or "Lvl_Village" not in _bu._WORLD.get_name():
        warn("Lvl_Village not loaded — homes aborted")
        return

    plots, arch = collect_house_plots()
    if not plots:
        warn("no house plots — aborting")
        return

    # index existing shell parts by house idx + suffix
    import re
    pat = re.compile(r"^VG3_House_(\d+)(_.+)$")
    houses = {}
    for actor in EAS.get_all_level_actors():
        try:
            lbl = actor.get_actor_label()
        except Exception:
            continue
        mo = pat.match(lbl)
        if mo:
            houses.setdefault(int(mo.group(1)), {})[mo.group(2)] = actor
        elif lbl.startswith("VG9_House_"):
            try:
                EAS.destroy_actor(actor)     # idempotent re-run
            except Exception:
                pass

    m = build_mats()
    rng = random.Random(9001)
    n = 0
    for plot in plots:
        idx = plot[6]
        try:
            reskin_and_augment(plot, houses.get(idx, {}), m, rng)
            n += 1
        except Exception as e:
            warn("house {} failed: {}".format(idx, e))
    log("upgraded {} homes".format(n))

    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("homes: all dirty packages saved")
    except Exception as e:
        warn("save failed: {}".format(e))
    log("HOMES COMPLETE")

    try:
        schedule_captures(plots)
    except Exception as e:
        warn("schedule_captures failed: {}".format(e))


if __name__ == "__main__":
    main()
