"""
build_trees.py  (stage 8)
=========================
Replaces the stage-3 "lollipop" trees (a bark cylinder + squashed leaf spheres)
with real per-species tree meshes: a tapered trunk, several tapered branches,
and a crown built from hundreds of alpha-masked LEAF CARDS (quads sampling a
leaf-cluster texture) so the canopy reads leaf-by-leaf instead of as a blob.

Species tuned from Punjab-plains agroforestry (Jalandhar doaba):
  Pipal   — wide low dome, broad heart leaves, brick thara base
  Banyan  — huge dark spread + hanging prop-root columns
  Neem    — clean bole, dense rounded crown, fine olive leaflets
  Sheesham— crooked/leaning, open airy see-through crown, fine light leaves
  Eucalyptus — tall narrow columnar rows, pale peeling trunk, droopy grey-green
  Mango   — short stout trunk, dense dark hemispherical dome
  Kikar   — small flat-topped umbrella, feathery grey-green

Additive + idempotent: sweeps every VG3_Tree_* actor and re-plants along the
roads / field bunds / pond / school / cricket with the new meshes. Guarded by
its own marker so it runs once.

RUN (auto via init_unreal.py when Saved/village_trees_done.txt is missing):
  py "D:/rural_games/rural_pardeep/Scripts/build_trees.py"
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_upgrade as _bu
from build_upgrade import *                      # noqa: F401,F403
from build_upgrade import _expr                  # import * skips _-prefixed

import unreal


SRC_DIR = os.path.join(unreal.Paths.project_dir(), "Content", "Village", "Map", "src")
TEX_DIR = "/Game/Village/Map"
MESH_DIR2 = "/Game/Village/Meshes/Trees"
BROAD_SRC = os.path.join(SRC_DIR, "leaf_broad.png")
FINE_SRC = os.path.join(SRC_DIR, "leaf_fine.png")
BROAD_TEX = TEX_DIR + "/T_LeafBroad"
FINE_TEX = TEX_DIR + "/T_LeafFine"


def log(msg):
    unreal.log("[build_trees] {}".format(msg))


def warn(msg):
    unreal.log_warning("[build_trees] {}".format(msg))


# ============================ leaf textures ================================

def _import_tex(src, dest_name):
    if not os.path.exists(src):
        warn("leaf texture missing: {}".format(src))
        return None
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", src)
    task.set_editor_property("destination_path", TEX_DIR)
    task.set_editor_property("destination_name", dest_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = EAL.load_asset(TEX_DIR + "/" + dest_name)
    if tex:
        tex.set_editor_property("srgb", True)
        EAL.save_asset(TEX_DIR + "/" + dest_name)
    return tex


# ============================ materials ===================================

def _wind_wpo(mat, mpc, amp, x0=-1500, y0=700):
    """Compact height-masked sine WPO in world XY — a gentle leaf sway."""
    wp = _expr(mat, unreal.MaterialExpressionWorldPosition, x0, y0)
    objp = _expr(mat, unreal.MaterialExpressionObjectPositionWS, x0, y0 + 200)
    time = _expr(mat, unreal.MaterialExpressionTime, x0, y0 + 380)
    mxy = _expr(mat, unreal.MaterialExpressionComponentMask, x0 + 170, y0)
    mxy.set_editor_property("r", True); mxy.set_editor_property("g", True)
    mxy.set_editor_property("b", False); mxy.set_editor_property("a", False)
    MEL.connect_material_expressions(wp, "", mxy, "")
    dot = _expr(mat, unreal.MaterialExpressionDotProduct, x0 + 340, y0)
    freq = _expr(mat, unreal.MaterialExpressionConstant2Vector, x0 + 170, y0 + 90)
    freq.set_editor_property("r", 0.0025); freq.set_editor_property("g", 0.0019)
    MEL.connect_material_expressions(mxy, "", dot, "A")
    MEL.connect_material_expressions(freq, "", dot, "B")
    tsp = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 340, y0 + 380)
    tc = _expr(mat, unreal.MaterialExpressionConstant, x0 + 170, y0 + 470)
    tc.set_editor_property("r", 1.1)
    MEL.connect_material_expressions(time, "", tsp, "A")
    MEL.connect_material_expressions(tc, "", tsp, "B")
    ph = _expr(mat, unreal.MaterialExpressionAdd, x0 + 520, y0 + 180)
    MEL.connect_material_expressions(dot, "", ph, "A")
    MEL.connect_material_expressions(tsp, "", ph, "B")
    sn = _expr(mat, unreal.MaterialExpressionSine, x0 + 680, y0 + 180)
    MEL.connect_material_expressions(ph, "", sn, "")
    # vertical mask: (worldZ - objZ) so base ~0, crown full
    wpz = _expr(mat, unreal.MaterialExpressionComponentMask, x0 + 170, y0 + 560)
    wpz.set_editor_property("r", False); wpz.set_editor_property("g", False)
    wpz.set_editor_property("b", True); wpz.set_editor_property("a", False)
    opz = _expr(mat, unreal.MaterialExpressionComponentMask, x0 + 170, y0 + 650)
    opz.set_editor_property("r", False); opz.set_editor_property("g", False)
    opz.set_editor_property("b", True); opz.set_editor_property("a", False)
    MEL.connect_material_expressions(wp, "", wpz, "")
    MEL.connect_material_expressions(objp, "", opz, "")
    hsub = _expr(mat, unreal.MaterialExpressionSubtract, x0 + 340, y0 + 580)
    MEL.connect_material_expressions(wpz, "", hsub, "A")
    MEL.connect_material_expressions(opz, "", hsub, "B")
    hdiv = _expr(mat, unreal.MaterialExpressionDivide, x0 + 520, y0 + 580)
    hr = _expr(mat, unreal.MaterialExpressionConstant, x0 + 340, y0 + 680)
    hr.set_editor_property("r", 900.0)
    MEL.connect_material_expressions(hsub, "", hdiv, "A")
    MEL.connect_material_expressions(hr, "", hdiv, "B")
    hcl = _expr(mat, unreal.MaterialExpressionClamp, x0 + 680, y0 + 580)
    MEL.connect_material_expressions(hdiv, "", hcl, "")
    wind = _expr(mat, unreal.MaterialExpressionCollectionParameter, x0 + 680, y0 + 360)
    if mpc:
        wind.set_editor_property("collection", mpc)
        wind.set_editor_property("parameter_name", "WindIntensity")
    ampc = _expr(mat, unreal.MaterialExpressionConstant, x0 + 680, y0 + 460)
    ampc.set_editor_property("r", float(amp))
    m1 = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 860, y0 + 260)
    MEL.connect_material_expressions(sn, "", m1, "A")
    MEL.connect_material_expressions(wind, "", m1, "B")
    m2 = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 1020, y0 + 320)
    MEL.connect_material_expressions(m1, "", m2, "A")
    MEL.connect_material_expressions(ampc, "", m2, "B")
    m3 = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 1180, y0 + 380)
    MEL.connect_material_expressions(m2, "", m3, "A")
    MEL.connect_material_expressions(hcl, "", m3, "B")
    wd = _expr(mat, unreal.MaterialExpressionConstant3Vector, x0 + 1180, y0 + 520)
    wd.set_editor_property("constant", unreal.LinearColor(1.0, 0.4, 0.0, 0.0))
    out = _expr(mat, unreal.MaterialExpressionMultiply, x0 + 1360, y0 + 430)
    MEL.connect_material_expressions(m3, "", out, "A")
    MEL.connect_material_expressions(wd, "", out, "B")
    MEL.connect_material_property(out, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)


def make_leaf_material(name, tex, tint, mpc, amp):
    path = MAT_DIR + "/" + name
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("opacity_mask_clip_value", 0.33)

    ts = _expr(mat, unreal.MaterialExpressionTextureSample, -640, -40)
    ts.set_editor_property("texture", tex)
    tintc = _expr(mat, unreal.MaterialExpressionConstant3Vector, -640, 200)
    tintc.set_editor_property("constant", unreal.LinearColor(tint[0], tint[1], tint[2], 1.0))
    mul = _expr(mat, unreal.MaterialExpressionMultiply, -380, 40)
    MEL.connect_material_expressions(ts, "RGB", mul, "A")
    MEL.connect_material_expressions(tintc, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(ts, "A", unreal.MaterialProperty.MP_OPACITY_MASK)

    rough = _expr(mat, unreal.MaterialExpressionConstant, -380, 300)
    rough.set_editor_property("r", 0.72)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    # a little translucency-ish: subsurface-like via low specular
    spec = _expr(mat, unreal.MaterialExpressionConstant, -380, 380)
    spec.set_editor_property("r", 0.15)
    MEL.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)

    try:
        _wind_wpo(mat, mpc, amp)
    except Exception as e:
        warn("leaf wind wiring failed ({}) — static leaves".format(e))

    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("leaf material {} built".format(name))
    return mat


def make_bark_material(name, rgb):
    path = MAT_DIR + "/" + name
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    lo = _expr(mat, unreal.MaterialExpressionConstant3Vector, -640, -40)
    lo.set_editor_property("constant", unreal.LinearColor(rgb[0] * 0.7, rgb[1] * 0.7, rgb[2] * 0.7, 1.0))
    hi = _expr(mat, unreal.MaterialExpressionConstant3Vector, -640, 120)
    hi.set_editor_property("constant", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    n = _expr(mat, unreal.MaterialExpressionNoise, -640, 280)
    n.set_editor_property("scale", 0.05)
    n.set_editor_property("output_min", 0.0)
    n.set_editor_property("output_max", 1.0)
    lp = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -380, 20)
    MEL.connect_material_expressions(lo, "", lp, "A")
    MEL.connect_material_expressions(hi, "", lp, "B")
    MEL.connect_material_expressions(n, "", lp, "Alpha")
    MEL.connect_material_property(lp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = _expr(mat, unreal.MaterialExpressionConstant, -380, 220)
    r.set_editor_property("r", 0.9)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    return mat


# ============================ mesh generation =============================

class ObjBuild(object):
    def __init__(self):
        self.v = []
        self.vt = ["vt 0 0"]      # index 1 = dummy for bark
        self.bark = []
        self.leaf = []

    def _add_v(self, x, y, z):
        self.v.append("v {:.2f} {:.2f} {:.2f}".format(x, y, z))
        return len(self.v)        # 1-based

    def _add_vt(self, u, w):
        self.vt.append("vt {:.4f} {:.4f}".format(u, w))
        return len(self.vt)

    def ring(self, cx, cy, cz, ax, ay, az, radius, sides):
        """Ring of `sides` verts around center, plane perpendicular to axis."""
        al = math.sqrt(ax * ax + ay * ay + az * az) or 1.0
        ax, ay, az = ax / al, ay / al, az / al
        # pick a helper not parallel to axis
        hx, hy, hz = (0.0, 0.0, 1.0) if abs(az) < 0.9 else (1.0, 0.0, 0.0)
        ux = ay * hz - az * hy
        uy = az * hx - ax * hz
        uz = ax * hy - ay * hx
        ul = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0
        ux, uy, uz = ux / ul, uy / ul, uz / ul
        vx = ay * uz - az * uy
        vy = az * ux - ax * uz
        vz = ax * uy - ay * ux
        start = None
        for i in range(sides):
            t = 2 * math.pi * i / sides
            c, s = math.cos(t) * radius, math.sin(t) * radius
            idx = self._add_v(cx + ux * c + vx * s,
                              cy + uy * c + vy * s,
                              cz + uz * c + vz * s)
            if start is None:
                start = idx
        return start, sides

    def tube(self, p0, p1, r0, r1, sides=6):
        ax, ay, az = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        s0, n = self.ring(p0[0], p0[1], p0[2], ax, ay, az, r0, sides)
        s1, _ = self.ring(p1[0], p1[1], p1[2], ax, ay, az, r1, sides)
        for i in range(sides):
            a = s0 + i
            b = s0 + (i + 1) % sides
            c = s1 + i
            d = s1 + (i + 1) % sides
            self.bark.append("f {}/1 {}/1 {}/1".format(a, b, d))
            self.bark.append("f {}/1 {}/1 {}/1".format(a, d, c))

    def card(self, cx, cy, cz, hw, hh, yaw, tilt):
        rx, ry = math.cos(yaw), math.sin(yaw)
        st = math.sin(tilt)
        ux, uy, uz = -math.sin(yaw) * st, math.cos(yaw) * st, math.cos(tilt)
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        uvs = [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
        vi, ti = [], []
        for (a, b), (u, w) in zip(corners, uvs):
            vi.append(self._add_v(cx + rx * a + ux * b,
                                  cy + ry * a + uy * b,
                                  cz + uz * b))
            ti.append(self._add_vt(u, w))
        self.leaf.append("f {}/{} {}/{} {}/{}".format(vi[0], ti[0], vi[1], ti[1], vi[2], ti[2]))
        self.leaf.append("f {}/{} {}/{} {}/{}".format(vi[0], ti[0], vi[2], ti[2], vi[3], ti[3]))

    def write(self, path):
        mtl_path = os.path.splitext(path)[0] + ".mtl"
        mtl_name = os.path.basename(mtl_path)
        with open(mtl_path, "w") as m:
            m.write("newmtl bark\nKd 0.30 0.21 0.12\n\n"
                    "newmtl leaf\nKd 0.35 0.55 0.20\nd 1.0\n")
        with open(path, "w") as f:
            f.write("mtllib {}\n".format(mtl_name))
            f.write("o Tree\n")
            f.write("\n".join(self.v))
            f.write("\n")
            f.write("\n".join(self.vt))
            # NB: no `g` group lines — the Interchange OBJ translator makes one
            # StaticMesh per `o`/`g`, so grouped OBJs get split into meshes named
            # 'bark'/'leaf' (ignoring destination_name) which then collide with the
            # auto-imported material instances of the same name. A single object
            # with two `usemtl` sections imports as ONE mesh (honouring
            # destination_name) with two material slots named after the usemtl.
            f.write("\nusemtl bark\n")
            f.write("\n".join(self.bark))
            f.write("\nusemtl leaf\n")
            f.write("\n".join(self.leaf))
            f.write("\n")


# species: trunk_h, trunk_r, lean, n_branch, crown_cz, crown_rx, crown_rz,
#          n_card, card_sz, leaf_kind, prop_roots
SPECIES = {
    "Pipal":     dict(h=1750, r=140, lean=0.05, nb=6, ccz=1550, crx=1250, crz=750,
                      nc=230, cs=150, leaf="broad", roots=0),
    "Banyan":    dict(h=1700, r=190, lean=0.04, nb=7, ccz=1500, crx=1700, crz=850,
                      nc=300, cs=150, leaf="broad", roots=7),
    "Neem":      dict(h=1500, r=95,  lean=0.06, nb=5, ccz=1450, crx=780,  crz=680,
                      nc=200, cs=120, leaf="fine",  roots=0),
    "Sheesham":  dict(h=1950, r=90,  lean=0.22, nb=5, ccz=1650, crx=820,  crz=760,
                      nc=140, cs=120, leaf="fine",  roots=0),
    "Eucalyptus":dict(h=2850, r=80,  lean=0.03, nb=4, ccz=2100, crx=430,  crz=950,
                      nc=150, cs=110, leaf="fine",  roots=0, bark="pale"),
    "Mango":     dict(h=1350, r=130, lean=0.05, nb=6, ccz=1150, crx=950,  crz=720,
                      nc=240, cs=140, leaf="broad", roots=0),
    "Kikar":     dict(h=1150, r=70,  lean=0.14, nb=6, ccz=1180, crx=880,  crz=340,
                      nc=90,  cs=105, leaf="fine",  roots=0),
}


def build_species_obj(name, sp, seed):
    rng = random.Random(seed)
    ob = ObjBuild()
    lean = sp["lean"]
    lx = math.cos(rng.uniform(0, 6.28)) * sp["h"] * lean
    ly = math.sin(rng.uniform(0, 6.28)) * sp["h"] * lean
    top = (lx, ly, sp["h"])
    # trunk (2 segments for a slight taper break)
    mid = (lx * 0.45, ly * 0.45, sp["h"] * 0.5)
    ob.tube((0, 0, 0), mid, sp["r"], sp["r"] * 0.7, 8)
    ob.tube(mid, top, sp["r"] * 0.7, sp["r"] * 0.4, 8)
    # branches out of the upper trunk
    branch_tops = []
    for b in range(sp["nb"]):
        a = 2 * math.pi * b / sp["nb"] + rng.uniform(-0.4, 0.4)
        start_z = sp["h"] * rng.uniform(0.55, 0.82)
        sx = lx * (start_z / sp["h"])
        sy = ly * (start_z / sp["h"])
        blen = sp["crx"] * rng.uniform(0.75, 1.1)
        up = rng.uniform(0.55, 1.15)      # radians above horizon
        ex = sx + math.cos(a) * blen * math.cos(up)
        ey = sy + math.sin(a) * blen * math.cos(up)
        ez = start_z + blen * math.sin(up)
        ob.tube((sx, sy, start_z), (ex, ey, ez), sp["r"] * 0.4, sp["r"] * 0.16, 6)
        branch_tops.append((ex, ey, ez))
    # prop roots (banyan): thin verticals from crown edge to ground
    for _ in range(sp["roots"]):
        a = rng.uniform(0, 6.28)
        rr = sp["crx"] * rng.uniform(0.55, 0.95)
        px, py = math.cos(a) * rr, math.sin(a) * rr
        drop_top = sp["ccz"] - sp["crz"] * 0.2
        ob.tube((px, py, drop_top), (px * 1.02, py * 1.02, 0), 26, 40, 6)
    # crown leaf cards in an ellipsoid, biased toward branch tops
    cx0, cy0, cz0 = lx * (sp["ccz"] / sp["h"]), ly * (sp["ccz"] / sp["h"]), sp["ccz"]
    for _ in range(sp["nc"]):
        if branch_tops and rng.random() < 0.5:
            bt = branch_tops[rng.randrange(len(branch_tops))]
            jx = sp["crx"] * 0.4
            cx = bt[0] + rng.uniform(-jx, jx)
            cy = bt[1] + rng.uniform(-jx, jx)
            cz = bt[2] + rng.uniform(-sp["crz"] * 0.4, sp["crz"] * 0.4)
        else:
            # random point in ellipsoid
            while True:
                ux, uy, uz = (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))
                if ux * ux + uy * uy + uz * uz <= 1.0:
                    break
            cx = cx0 + ux * sp["crx"]
            cy = cy0 + uy * sp["crx"]
            cz = cz0 + uz * sp["crz"]
        sz = sp["cs"] * rng.uniform(0.7, 1.3)
        ob.card(cx, cy, cz, sz, sz,
                rng.uniform(0, 6.28), rng.uniform(-0.5, 1.4))
    path = os.path.join(SRC_DIR, "tree_{}.obj".format(name.lower()))
    ob.write(path)
    return path


def import_species_mesh(name, path, bark_mat, leaf_mat):
    dest = MESH_DIR2 + "/SM_Tree_" + name
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", MESH_DIR2)
    task.set_editor_property("destination_name", "SM_Tree_" + name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = EAL.load_asset(dest)
    # Fallback: Interchange may name the asset after the OBJ object rather than
    # destination_name — recover it from the task's reported import paths and
    # rename it to the canonical SM_Tree_<name>.
    if mesh is None:
        try:
            for p in (task.get_editor_property("imported_object_paths") or []):
                obj = EAL.load_asset(p)
                if isinstance(obj, unreal.StaticMesh):
                    if EAL.does_asset_exist(dest):
                        EAL.delete_asset(dest)
                    EAL.rename_asset(p.split(".")[0], dest)
                    mesh = EAL.load_asset(dest)
                    break
        except Exception as e:
            warn("SM_Tree_{} fallback load failed: {}".format(name, e))
    if mesh is None:
        return None
    # slot order follows usemtl order in the OBJ: bark then leaf
    mats = []
    slots = mesh.get_editor_property("static_materials")
    for s in slots:
        nm = str(s.get_editor_property("material_slot_name")).lower()
        mats.append(leaf_mat if "leaf" in nm else bark_mat)
    if len(mats) == len(slots) and slots:
        new_slots = []
        for s, m in zip(slots, mats):
            new_slots.append(unreal.StaticMaterial(
                material_interface=m,
                material_slot_name=s.get_editor_property("material_slot_name")))
        mesh.set_editor_property("static_materials", new_slots)
    else:
        for i in range(mesh.get_num_sections(0) if hasattr(mesh, "get_num_sections") else 2):
            try:
                mesh.set_material(i, leaf_mat if i == 1 else bark_mat)
            except Exception:
                pass
    EAL.save_asset(MESH_DIR2 + "/SM_Tree_" + name)
    return mesh


# ============================ placement ===================================

def sweep_old_trees():
    n = 0
    for actor in list(EAS.get_all_level_actors()):
        try:
            lbl = actor.get_actor_label()
        except Exception:
            continue
        if lbl.startswith("VG3_Tree_") or lbl.startswith("VG_Tree_"):
            EAS.destroy_actor(actor)
            n += 1
    log("swept {} old tree actors".format(n))


def plant(meshes, name, x, y, rng, idx):
    mesh = meshes.get(name)
    if mesh is None:
        return
    gz = ground_z(x, y)
    actor = EAS.spawn_actor_from_object(mesh, unreal.Vector(x, y, gz - 8.0),
                                        unreal.Rotator(0, rng.uniform(0, 360), 0))
    s = rng.uniform(0.85, 1.2)
    actor.set_actor_scale3d(unreal.Vector(s, s, s * rng.uniform(0.95, 1.12)))
    actor.set_actor_label("VG8_Tree_{:03d}".format(idx))
    actor.set_folder_path("Village/Trees")
    try:
        actor.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    except Exception:
        pass


def replant(meshes, rng):
    # road samples
    road_pts = []
    for pts in ROADS.values():
        try:
            road_pts.extend(road_samples(pts))
        except Exception:
            pass
    placed = []
    idx = 0

    def ok(x, y, min_d=1400.0):
        if math.hypot(x - CRICKET_CENTER[0], y - CRICKET_CENTER[1]) < CRICKET_BOUNDARY + 900:
            return False
        if any(math.hypot(x - rx, y - ry) < 760 for rx, ry in road_pts):
            return False
        if any(math.hypot(x - tx, y - ty) < min_d for tx, ty in placed):
            return False
        return True

    # 1) roadside avenues — eucalyptus rows + sheesham/neem
    avenue = ["Eucalyptus", "Eucalyptus", "Sheesham", "Neem"]
    for i, (rx, ry) in enumerate(road_pts):
        if i % 5 != 0:
            continue
        side = 1 if (i // 5) % 2 == 0 else -1
        x = rx + side * rng.uniform(760, 1150)
        y = ry + side * rng.uniform(-360, 360)
        if not ok(x, y, min_d=900.0):
            continue
        plant(meshes, avenue[idx % len(avenue)], x, y, rng, idx)
        placed.append((x, y)); idx += 1

    # 2) big shade trees at pond / school / cricket / gurdwara grounds
    clusters = [
        (POND_CENTER[0], POND_CENTER[1], 5, 3400.0, ["Banyan", "Pipal", "Neem"]),
        (22000.0, 8800.0, 3, 1800.0, ["Neem", "Mango"]),
        (CRICKET_CENTER[0], CRICKET_CENTER[1], 4, CRICKET_BOUNDARY + 1500.0, ["Pipal", "Neem"]),
        (-4000.0, -11200.0, 3, 2200.0, ["Pipal", "Mango"]),
    ]
    for (cx, cy, cnt, r0, spset) in clusters:
        for k in range(cnt):
            a = rng.uniform(0, 6.28)
            x = cx + math.cos(a) * r0 * rng.uniform(0.9, 1.25)
            y = cy + math.sin(a) * r0 * rng.uniform(0.9, 1.25)
            if not ok(x, y, min_d=1100.0):
                continue
            plant(meshes, spset[k % len(spset)], x, y, rng, idx)
            placed.append((x, y)); idx += 1

    # 3) field-bund lines — kikar / sheesham / mango orchard blocks
    span = 56000.0
    fx = -span
    fi = 0
    field = ["Kikar", "Sheesham", "Mango", "Kikar", "Neem"]
    while fx <= span:
        fy = -span
        while fy <= span:
            fi += 1
            if fi % 3 == 0 and math.hypot(fx, fy) > FIELD_INNER + 2500:
                ex = fx + FIELD_STEP[0] / 2.0 - 600.0
                for k in range(3):
                    y = fy + (k - 1) * 2600.0
                    if not ok(ex, y, min_d=1150.0):
                        continue
                    plant(meshes, field[(fi + k) % len(field)], ex, y, rng, idx)
                    placed.append((ex, y)); idx += 1
            fy += FIELD_STEP[1]
        fx += FIELD_STEP[0]

    log("replanted {} trees".format(idx))


# ============================ verification captures =======================

SCRATCH = ("C:/Users/Evolet/AppData/Local/Temp/claude/d--rural-games-rural-pardeep/"
           "50b8e605-1607-4c91-a702-60eaa5ff3d19/scratchpad")
_cap = {"i": 0, "t": 0.0, "phase": "move", "handle": None, "shots": [], "reqd": set()}


def _rot(p, y):
    r = unreal.Rotator(); r.pitch = p; r.yaw = y; r.roll = 0.0
    return r


def _cap_tick(dt):
    st = _cap
    if st["i"] >= len(st["shots"]):
        return
    name, cam, look = st["shots"][st["i"]]
    if st["phase"] == "move":
        try:
            UES.set_level_viewport_camera_info(cam, look)
        except Exception as e:
            unreal.log_warning("[build_trees] cam move {} failed: {}".format(name, e))
        st["phase"] = "settle"; st["t"] = 0.0
        return
    st["t"] += dt
    if st["phase"] == "settle" and st["t"] > 6.0:
        if st["i"] not in st["reqd"]:
            st["reqd"].add(st["i"])
            try:
                unreal.AutomationLibrary.take_high_res_screenshot(1760, 990, SCRATCH + "/" + name)
                unreal.log("[build_trees] capture requested: {}".format(name))
            except Exception as e:
                unreal.log_warning("[build_trees] capture {} failed: {}".format(name, e))
        st["phase"] = "cool"; st["t"] = 0.0
    elif st["phase"] == "cool" and st["t"] > 30.0:
        st["i"] += 1; st["phase"] = "move"; st["t"] = 0.0
        if st["i"] >= len(st["shots"]):
            try:
                with open(os.path.join(SCRATCH.replace("/", os.sep), "trees_caps_done.txt"), "w") as f:
                    f.write("done")
            except Exception:
                pass
            unreal.log("[build_trees] ALL TREE CAPTURES DONE")
            if st["handle"] is not None:
                unreal.unregister_slate_post_tick_callback(st["handle"])


def schedule_captures():
    _cap["shots"] = [
        ("t8_overview.png", unreal.Vector(-9000.0, 20000.0, 5200.0), _rot(-24.0, -70.0)),
        ("t8_roadside.png", unreal.Vector(0.0, 17800.0, 650.0), _rot(-8.0, -90.0)),
        ("t8_field.png",    unreal.Vector(-30000.0, -26000.0, 1400.0), _rot(-12.0, -120.0)),
    ]
    _cap["handle"] = unreal.register_slate_post_tick_callback(_cap_tick)
    log("tree captures scheduled ({} shots)".format(len(_cap["shots"])))


# ============================ driver ======================================

def main():
    _bu._WORLD = _bu.UES.get_editor_world()
    if _bu._WORLD is None or "Lvl_Village" not in _bu._WORLD.get_name():
        warn("Lvl_Village not loaded — trees aborted")
        return
    mpc = EAL.load_asset(MPC_PATH)

    broad = _import_tex(BROAD_SRC, "T_LeafBroad")
    fine = _import_tex(FINE_SRC, "T_LeafFine")
    if broad is None or fine is None:
        warn("leaf textures missing — aborting tree build")
        return

    bark = make_bark_material("M_VGBark", (0.30, 0.21, 0.12))
    bark_pale = make_bark_material("M_VGBarkPale", (0.72, 0.70, 0.63))
    leaf_broad = make_leaf_material("M_VGLeafBroad", broad, (0.55, 0.72, 0.42), mpc, 16.0)
    leaf_fine = make_leaf_material("M_VGLeafFine", fine, (0.62, 0.70, 0.48), mpc, 20.0)

    # Clear stray auto-imported 'bark'/'leaf' material-instance assets left in the
    # Trees folder by earlier grouped-OBJ imports; their names collide with the
    # per-group StaticMesh names and abort every subsequent import.
    for stray in ("bark", "leaf"):
        ap = MESH_DIR2 + "/" + stray
        try:
            if EAL.does_asset_exist(ap):
                EAL.delete_asset(ap)
                log("removed stray asset {}".format(ap))
        except Exception as e:
            warn("could not remove stray {}: {}".format(ap, e))

    meshes = {}
    for i, (name, sp) in enumerate(SPECIES.items()):
        try:
            path = build_species_obj(name, sp, 4200 + i)
            lm = leaf_broad if sp["leaf"] == "broad" else leaf_fine
            bm = bark_pale if sp.get("bark") == "pale" else bark
            mesh = import_species_mesh(name, path, bm, lm)
            if mesh:
                meshes[name] = mesh
                log("SM_Tree_{} built".format(name))
            else:
                warn("SM_Tree_{} import failed".format(name))
        except Exception as e:
            warn("species {} failed: {}".format(name, e))

    if not meshes:
        warn("no tree meshes built — leaving old trees")
        return

    try:
        sweep_old_trees()
        replant(meshes, random.Random(818))
    except Exception as e:
        warn("replant failed: {}".format(e))

    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("trees: all dirty packages saved")
    except Exception as e:
        warn("save failed: {}".format(e))
    log("TREES COMPLETE")

    try:
        schedule_captures()
    except Exception as e:
        warn("schedule_captures failed: {}".format(e))


if __name__ == "__main__":
    main()
