"""
build_environment.py (v2)
=========================
Builds the rural Punjabi village open world FROM SCRATCH — now with the
user's own 3D models, a road network matching the Pandori Nijjaran map,
detailed houses, villager NPCs, perimeter mountains and a reflective pond.
Idempotent: re-running removes all VG_* actors and rebuilds.

v2 additions over v1:
  - Imports models from "D:/rural game archotectuere" into /Game/Village/Arch
    (stylized house, Indian food-vendor cart, six photogrammetry terrain
    scans used as ring mountains; Nanite enabled on imports).
  - Denser, map-accurate road network: EW main road (Pandori Nijjaran Rd),
    NE side road, village ring, inner lane grid, radial exits NW/N/W.
  - Landmarks per the Google-Maps sample: THREE gurdwaras (Ravidass north,
    Nihang Singh centre-east, Guru Nanak Dev centre), Shiv Mandir on the
    west edge, sarkari school SE, bank west on the main road, farm NE.
  - Better generated houses: plinth, door, windows, parapet, roof water
    tank — mixed with the imported stylized house.
  - Ground material v2: noise colour blend + roughness variation for
    realistic sun response; village pond with a low-roughness water
    material (Lumen reflections).
  - 12 wandering villager NPCs (BP_Villager) with homes / work fields /
    gurdwara / vendor-cart points of interest stamped per instance.

RUN (also auto-run by Content/Python/init_unreal.py when the marker file
Saved/village_bootstrap_done.txt is missing):
  py "D:/rural_games/rural_pardeep/Scripts/build_environment.py"
"""

import math
import os
import random

import unreal

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
MEL = unreal.MaterialEditingLibrary

LEVEL_PATH = "/Game/Village/Lvl_Village"
LEVEL_TEMPLATE = "/Engine/Maps/Templates/OpenWorld"
MAT_DIR = "/Game/Village/Materials"
ARCH_DIR = "/Game/Village/Arch"

CUBE = EAL.load_asset("/Engine/BasicShapes/Cube.Cube")
CYLINDER = EAL.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
SPHERE = EAL.load_asset("/Engine/BasicShapes/Sphere.Sphere")
PLANE = EAL.load_asset("/Engine/BasicShapes/Plane.Plane")
CONE = EAL.load_asset("/Engine/BasicShapes/Cone.Cone")

# --------------------- user model sources (analysed 2026-07-16) -----------
MODEL_ROOT = r"D:\rural game archotectuere"
MODEL_SOURCES = {
    "House": os.path.join(MODEL_ROOT, "stylized-house-tier-i", "source",
                          "d06a47fb3084c73a23d9a0bff3c00716.glb"),
    "Vendor": os.path.join(MODEL_ROOT, "uploads_files_5553978_Indian_Food_Ventor",
                           "Indian_Food_Ventor", "source", "Food_Ventor_Polish.fbx"),
    "MountainHill": os.path.join(MODEL_ROOT, "textured-hill.glb"),
    "MountainKula": os.path.join(MODEL_ROOT, "kula_peri_bacalari.glb"),
    "MountainGlacier": os.path.join(MODEL_ROOT, "glacier_dargentiere_en_2012.glb"),
    "MountainMer": os.path.join(MODEL_ROOT, "mer_de_glace_1939.glb"),
    "MountainTremorgio": os.path.join(MODEL_ROOT, "tremorgio.glb"),
    "MountainLake": os.path.join(MODEL_ROOT, "glacial_lake.glb"),
    "Misc1": os.path.join(MODEL_ROOT, "uploads_files_4229865_FBX+File.Fbx"),
    "Misc2": os.path.join(MODEL_ROOT, "uploads_files_5184248_model.obj"),
}
# NOTE: the two Mahindra tractor .blend files cannot be imported directly —
# export them to FBX from Blender and drop them into MODEL_SOURCES.

# ---------------- layout (cm) — Pandori Nijjaran inspired -----------------
# +X = east, +Y = south. Main road runs along the SOUTH of the core.
VILLAGE_CENTER = (0.0, 0.0)
CORE_RADIUS = 16000.0
FIELD_INNER = 19000.0
FIELD_OUTER = 120000.0
FIELD_STEP = (14000.0, 10000.0)
FIELD_MAX_FRACTION = 0.85
ROAD_WIDTH = 350.0
ROAD_SEG_LEN = 950.0
ROAD_SEG_SPACING = 900.0
TREE_SPACING = 5500.0
HOUSE_COUNT_CAP = 48
NPC_COUNT = 12
MOUNTAIN_RING_RADIUS = 92000.0

RING_RADIUS = 10000.0
ROADS = {
    # Pandori Nijjaran Rd: east-west along the south of the core
    "main": [(-60000, 20000), (-30000, 17000), (0, 14500), (30000, 12000), (60000, 9500)],
    # Pandori Nijjaran Side Road curving off to the north-east
    "side_ne": [(16000, 13300), (28000, -4000), (42000, -18000), (55000, -30000)],
    # village ring + main cross lanes
    "ring": [(RING_RADIUS * math.cos(math.radians(a)),
              RING_RADIUS * math.sin(math.radians(a))) for a in range(0, 361, 45)],
    "lane_ns": [(0, 13800), (300, 4000), (-300, -4000), (0, -14000)],
    "lane_ew": [(-14000, 500), (-4000, 200), (4000, -200), (14000, -500)],
    # inner lane grid (irregular, like the map's alley cluster)
    "in_h1": [(-11000, -9000), (-2000, -8600), (9000, -9200)],
    "in_h2": [(-12000, -4500), (-3000, -4800), (11000, -4300)],
    "in_h3": [(-11500, 4500), (0, 4200), (11000, 4800)],
    "in_h4": [(-9000, 9000), (2000, 8700), (10000, 9300)],
    "in_v1": [(-9000, -11000), (-8600, -2000), (-9200, 9000)],
    "in_v2": [(-4500, -12000), (-4800, 0), (-4300, 11000)],
    "in_v3": [(4500, -11500), (4200, 2000), (4800, 11000)],
    "in_v4": [(9000, -10000), (8700, 2000), (9300, 10000)],
    # radial exits like the map (NW toward the bank side, N, W)
    "exit_nw": [(-7500, -7500), (-20000, -20000), (-38000, -33000)],
    "exit_n": [(500, -13800), (2000, -30000), (1000, -48000)],
    "exit_w": [(-13900, 600), (-30000, 2000), (-52000, 2500)],
}

FIELD_COLORS = [
    ("Wheat", (0.78, 0.65, 0.25)),
    ("YoungGreen", (0.36, 0.52, 0.18)),
    ("DeepGreen", (0.24, 0.42, 0.15)),
    ("Tilled", (0.45, 0.33, 0.20)),
]
PLASTER_COLORS = [
    ("Tan", (0.85, 0.78, 0.62)),
    ("Cream", (0.92, 0.88, 0.78)),
    ("PaleBlue", (0.65, 0.75, 0.85)),
    ("White", (0.95, 0.95, 0.92)),
]
NPC_NAMES = ["Gurpreet Singh", "Baldev", "Simran Kaur", "Harjit", "Amrita",
             "Jaswinder", "Manpreet", "Rajdeep", "Nimrat Kaur", "Sukhdev",
             "Paramjit", "Kirat"]


def log(msg):
    unreal.log("[build_environment] {}".format(msg))


def warn(msg):
    unreal.log_warning("[build_environment] {}".format(msg))


# ------------------------------ level ------------------------------------

def ensure_level():
    if EAL.does_asset_exist(LEVEL_PATH):
        LES.load_level(LEVEL_PATH)
        log("loaded existing " + LEVEL_PATH)
        return
    if not LES.new_level_from_template(LEVEL_PATH, LEVEL_TEMPLATE):
        raise RuntimeError("could not create level from template " + LEVEL_TEMPLATE)
    LES.save_current_level()
    log("created {} from OpenWorld template".format(LEVEL_PATH))


def cleanup_previous():
    stale = [a for a in EAS.get_all_level_actors()
             if a.get_actor_label().startswith("VG_")]
    for actor in stale:
        EAS.destroy_actor(actor)
    if stale:
        log("removed {} VG_ actors from a previous run".format(len(stale)))


def landscape_info():
    proxies = [a for a in EAS.get_all_level_actors()
               if isinstance(a, unreal.LandscapeProxy)]
    if not proxies:
        warn("no LandscapeProxy found in the level!")
        return None, unreal.Vector(0, 0, 0), unreal.Vector(60000, 60000, 1000)
    boxes = [p.get_actor_bounds(False) for p in proxies]
    min_v = unreal.Vector(min(o.x - e.x for o, e in boxes),
                          min(o.y - e.y for o, e in boxes),
                          min(o.z - e.z for o, e in boxes))
    max_v = unreal.Vector(max(o.x + e.x for o, e in boxes),
                          max(o.y + e.y for o, e in boxes),
                          max(o.z + e.z for o, e in boxes))
    center = unreal.Vector((min_v.x + max_v.x) / 2, (min_v.y + max_v.y) / 2,
                           (min_v.z + max_v.z) / 2)
    extent = unreal.Vector((max_v.x - min_v.x) / 2, (max_v.y - min_v.y) / 2,
                           (max_v.z - min_v.z) / 2)
    log("landscape: {} proxies, half-extent ({:.0f}, {:.0f})".format(
        len(proxies), extent.x, extent.y))
    return proxies, center, extent


_WORLD = None
_ZTOP = 100000.0
_ZBOT = -100000.0


def ground_z(x, y, default_z=0.0):
    hit = unreal.SystemLibrary.line_trace_single(
        _WORLD, unreal.Vector(x, y, _ZTOP), unreal.Vector(x, y, _ZBOT),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
        unreal.DrawDebugTrace.NONE, True)
    if hit:
        return hit.to_dict()["location"].z
    return default_z


# ------------------------- user model import -----------------------------

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


def import_arch_models():
    """Import the user's models once; returns {key: [StaticMesh, ...]}."""
    imported = {}
    for key, src in MODEL_SOURCES.items():
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
            for mesh in meshes:
                enable_nanite(mesh)
            imported[key] = meshes
            log("  -> {} static mesh(es)".format(len(meshes)))
        else:
            warn("  -> no static mesh produced from " + src)
    return imported


def mesh_box(mesh):
    box = mesh.get_bounding_box()
    return box


def spawn_model(mesh, label, folder, x, y, target_width, yaw=0.0, sink_frac=0.0):
    """Spawn an imported mesh scaled to target_width, feet on the ground."""
    box = mesh_box(mesh)
    size_x = max(1.0, box.max.x - box.min.x)
    size_y = max(1.0, box.max.y - box.min.y)
    size_z = max(1.0, box.max.z - box.min.z)
    scale = target_width / max(size_x, size_y)
    gz = ground_z(x, y)
    z = gz - box.min.z * scale - size_z * scale * sink_frac
    actor = EAS.spawn_actor_from_object(mesh, unreal.Vector(x, y, z),
                                        unreal.Rotator(0.0, 0.0, yaw))
    actor.set_actor_label(label)
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    actor.set_folder_path(folder)
    return actor


# ----------------------------- materials ----------------------------------

def make_phys_dirt():
    path = MAT_DIR + "/PM_Dirt"
    if not EAL.does_asset_exist(path):
        pm = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "PM_Dirt", MAT_DIR, unreal.PhysicalMaterial,
            unreal.PhysicalMaterialFactoryNew())
        pm.set_editor_property("surface_type", unreal.PhysicalSurface.SURFACE_TYPE1)
        EAL.save_asset(path)
        log("created PM_Dirt (SurfaceType1)")
    return EAL.load_asset(path)


def make_landscape_material(pm_dirt):
    """v2 ground: colour noise blend + roughness variation for sun response."""
    path = MAT_DIR + "/M_VillageGround"
    if EAL.does_asset_exist(path):
        # Recreate with the v2 graph; if the delete is refused (still
        # referenced), keep using the existing material rather than failing.
        try:
            EAL.delete_asset(path)
        except Exception as e:
            warn("could not replace M_VillageGround ({}), keeping v1".format(e))
        if EAL.does_asset_exist(path):
            return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VillageGround", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())

    grass = MEL.create_material_expression(
        mat, unreal.MaterialExpressionConstant3Vector, -700, -200)
    grass.set_editor_property("constant", unreal.LinearColor(0.30, 0.38, 0.14, 1.0))
    dirt = MEL.create_material_expression(
        mat, unreal.MaterialExpressionConstant3Vector, -700, 0)
    dirt.set_editor_property("constant", unreal.LinearColor(0.43, 0.33, 0.21, 1.0))

    colour_noise = MEL.create_material_expression(
        mat, unreal.MaterialExpressionNoise, -700, 220)
    colour_noise.set_editor_property("scale", 0.00035)
    colour_noise.set_editor_property("turbulence", True)
    colour_noise.set_editor_property("output_min", 0.0)
    colour_noise.set_editor_property("output_max", 1.0)

    lerp = MEL.create_material_expression(
        mat, unreal.MaterialExpressionLinearInterpolate, -380, 0)
    MEL.connect_material_expressions(grass, "", lerp, "A")
    MEL.connect_material_expressions(dirt, "", lerp, "B")
    MEL.connect_material_expressions(colour_noise, "", lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)

    # Roughness varies 0.55 (packed sun-baked mud, catches highlights) to
    # 0.95 (loose dust) at a different noise frequency.
    rough_lo = MEL.create_material_expression(
        mat, unreal.MaterialExpressionConstant, -700, 420)
    rough_lo.set_editor_property("r", 0.55)
    rough_hi = MEL.create_material_expression(
        mat, unreal.MaterialExpressionConstant, -700, 500)
    rough_hi.set_editor_property("r", 0.95)
    rough_noise = MEL.create_material_expression(
        mat, unreal.MaterialExpressionNoise, -700, 600)
    rough_noise.set_editor_property("scale", 0.0011)
    rough_noise.set_editor_property("output_min", 0.0)
    rough_noise.set_editor_property("output_max", 1.0)
    rough_lerp = MEL.create_material_expression(
        mat, unreal.MaterialExpressionLinearInterpolate, -380, 480)
    MEL.connect_material_expressions(rough_lo, "", rough_lerp, "A")
    MEL.connect_material_expressions(rough_hi, "", rough_lerp, "B")
    MEL.connect_material_expressions(rough_noise, "", rough_lerp, "Alpha")
    MEL.connect_material_property(rough_lerp, "", unreal.MaterialProperty.MP_ROUGHNESS)

    mat.set_editor_property("phys_material", pm_dirt)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    log("created M_VillageGround v2 (colour + roughness noise, PM_Dirt)")
    return mat


def make_water_material():
    path = MAT_DIR + "/M_VGWater"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGWater", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    colour = MEL.create_material_expression(
        mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    colour.set_editor_property("constant", unreal.LinearColor(0.03, 0.09, 0.10, 1.0))
    MEL.connect_material_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = MEL.create_material_expression(
        mat, unreal.MaterialExpressionConstant, -400, 200)
    rough.set_editor_property("r", 0.03)  # mirror-calm pond -> Lumen reflections
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    spec = MEL.create_material_expression(
        mat, unreal.MaterialExpressionConstant, -400, 280)
    spec.set_editor_property("r", 1.0)
    MEL.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    return mat


def make_flat_parent():
    path = MAT_DIR + "/M_VGFlat"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGFlat", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    colour = MEL.create_material_expression(
        mat, unreal.MaterialExpressionVectorParameter, -400, 0)
    colour.set_editor_property("parameter_name", "Color")
    colour.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1.0))
    MEL.connect_material_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = MEL.create_material_expression(
        mat, unreal.MaterialExpressionConstant, -400, 220)
    rough.set_editor_property("r", 0.9)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_asset(path)
    return mat


_MI_CACHE = {}


def flat_mi(parent, name, rgb):
    if name in _MI_CACHE:
        return _MI_CACHE[name]
    path = "{}/MI_{}".format(MAT_DIR, name)
    if EAL.does_asset_exist(path):
        inst = EAL.load_asset(path)
    else:
        inst = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "MI_" + name, MAT_DIR, unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew())
        inst.set_editor_property("parent", parent)
        MEL.set_material_instance_vector_parameter_value(
            inst, "Color", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
        MEL.update_material_instance(inst)
        EAL.save_asset(path)
    _MI_CACHE[name] = inst
    return inst


# ----------------------------- spawning -----------------------------------

def spawn_mesh(mesh, mi, label, folder, loc, scale, yaw=0.0):
    actor = EAS.spawn_actor_from_object(mesh, loc, unreal.Rotator(0.0, 0.0, yaw))
    actor.set_actor_label(label)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    actor.set_folder_path(folder)
    if mi:
        actor.static_mesh_component.set_material(0, mi)
    return actor


def road_class():
    cls = getattr(unreal, "RoadSpline", None)
    if cls is None:
        cls = unreal.load_class(None, "/Script/rural_pardeep.RoadSpline")
    return cls


def build_road(name, points_2d, mi_road):
    pts = [unreal.Vector(x, y, ground_z(x, y) + 10.0) for x, y in points_2d]
    road = EAS.spawn_actor_from_class(road_class(), pts[0], unreal.Rotator(0, 0, 0))
    road.set_actor_label("VG_DirtRoad_" + name)
    road.set_folder_path("Village/Roads")
    spline = road.get_component_by_class(unreal.SplineComponent)
    spline.clear_spline_points(True)
    for p in pts:
        spline.add_spline_point(p, unreal.SplineCoordinateSpace.WORLD, True)

    length = spline.get_spline_length()
    dist, count = 0.0, 0
    while dist <= length:
        loc = spline.get_location_at_distance_along_spline(
            dist, unreal.SplineCoordinateSpace.WORLD)
        rot = spline.get_rotation_at_distance_along_spline(
            dist, unreal.SplineCoordinateSpace.WORLD)
        gz = ground_z(loc.x, loc.y)
        spawn_mesh(CUBE, mi_road, "VG_Road_{}_{:03d}".format(name, count),
                   "Village/Roads/Segments",
                   unreal.Vector(loc.x, loc.y, gz + 3.0),
                   (ROAD_SEG_LEN / 100.0, ROAD_WIDTH / 100.0, 0.06),
                   rot.yaw)
        dist += ROAD_SEG_SPACING
        count += 1
    return count


def road_samples(points_2d, step=1000.0):
    samples = []
    for (x1, y1), (x2, y2) in zip(points_2d, points_2d[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        n = max(2, int(seg / step))
        for i in range(n):
            t = i / float(n)
            samples.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
    return samples


# ------------------------------ buildings ---------------------------------

def build_house_generated(idx, x, y, yaw, parent_mat, rng):
    """A detailed placeholder house: plinth, block, door, windows, parapet,
    rooftop water tank."""
    w = rng.uniform(650, 1200)
    d = rng.uniform(550, 950)
    storeys = 1 if rng.random() < 0.55 else 2
    h = storeys * 300.0
    gz = ground_z(x, y)
    name, rgb = PLASTER_COLORS[idx % len(PLASTER_COLORS)]
    mi = flat_mi(parent_mat, "Plaster" + name, rgb)
    dark = flat_mi(parent_mat, "DarkWood", (0.16, 0.11, 0.08))
    steel = flat_mi(parent_mat, "TankSteel", (0.55, 0.58, 0.62))
    folder = "Village/Houses"
    label = "VG_House_{:02d}".format(idx)

    def local(lx, ly, lz):
        r = math.radians(yaw)
        return unreal.Vector(x + lx * math.cos(r) - ly * math.sin(r),
                             y + lx * math.sin(r) + ly * math.cos(r), gz + lz)

    # plinth + main block
    spawn_mesh(CUBE, mi, label + "_plinth", folder, local(0, 0, 15),
               ((w + 60) / 100, (d + 60) / 100, 0.3), yaw)
    spawn_mesh(CUBE, mi, label, folder, local(0, 0, 30 + h / 2),
               (w / 100, d / 100, h / 100), yaw)
    # door (front = -Y side, facing the lane) + two windows per storey
    spawn_mesh(CUBE, dark, label + "_door", folder, local(0, -d / 2 - 3, 30 + 105),
               (0.9, 0.06, 2.1), yaw)
    for s in range(storeys):
        wz = 30 + s * 300 + 190
        spawn_mesh(CUBE, dark, label + "_w{}L".format(s), folder,
                   local(-w / 4, -d / 2 - 3, wz), (0.7, 0.06, 0.8), yaw)
        spawn_mesh(CUBE, dark, label + "_w{}R".format(s), folder,
                   local(w / 4, -d / 2 - 3, wz), (0.7, 0.06, 0.8), yaw)
    # parapet
    top = 30 + h
    spawn_mesh(CUBE, mi, label + "_pN", folder, local(0, d / 2 - 10, top + 40),
               (w / 100, 0.2, 0.8), yaw)
    spawn_mesh(CUBE, mi, label + "_pS", folder, local(0, -d / 2 + 10, top + 40),
               (w / 100, 0.2, 0.8), yaw)
    spawn_mesh(CUBE, mi, label + "_pE", folder, local(w / 2 - 10, 0, top + 40),
               (0.2, d / 100 - 0.2, 0.8), yaw)
    spawn_mesh(CUBE, mi, label + "_pW", folder, local(-w / 2 + 10, 0, top + 40),
               (0.2, d / 100 - 0.2, 0.8), yaw)
    # rooftop water tank (every second house)
    if idx % 2 == 0:
        spawn_mesh(CYLINDER, steel, label + "_tank", folder,
                   local(w / 4, d / 4, top + 55), (1.1, 1.1, 1.1), yaw)


def build_house(idx, x, y, yaw, parent_mat, rng, house_meshes):
    # Mix the user's stylized house with generated ones for variety.
    if house_meshes and rng.random() < 0.55:
        mesh = house_meshes[idx % len(house_meshes)]
        spawn_model(mesh, "VG_House_{:02d}_arch".format(idx), "Village/Houses",
                    x, y, rng.uniform(800, 1150), yaw)
    else:
        build_house_generated(idx, x, y, yaw, parent_mat, rng)


def build_gurdwara(label, x, y, size, parent_mat):
    gz = ground_z(x, y)
    white = flat_mi(parent_mat, "PlasterWhite", PLASTER_COLORS[3][1])
    gold = flat_mi(parent_mat, "DomeGold", (0.85, 0.68, 0.28))
    folder = "Village/Landmarks"
    s = size / 100.0
    h = size * 0.5
    spawn_mesh(CUBE, white, label, folder, unreal.Vector(x, y, gz + h / 2), (s, s, h / 100), 0)
    spawn_mesh(SPHERE, gold, label + "_Dome", folder,
               unreal.Vector(x, y, gz + h + size * 0.12), (s * 0.36, s * 0.36, s * 0.30), 0)
    corner = size / 2 - 60
    for i, (cx, cy) in enumerate(((-corner, -corner), (corner, -corner),
                                  (-corner, corner), (corner, corner))):
        spawn_mesh(CYLINDER, white, "{}_T{}".format(label, i), folder,
                   unreal.Vector(x + cx, y + cy, gz + h * 0.62), (0.9, 0.9, h / 100 * 1.24), 0)
    # nishan sahib (flag pole)
    spawn_mesh(CYLINDER, gold, label + "_Nishan", folder,
               unreal.Vector(x + size / 2 + 150, y, gz + 350), (0.15, 0.15, 7.0), 0)


def build_mandir(x, y, parent_mat):
    gz = ground_z(x, y)
    cream = flat_mi(parent_mat, "MandirStone", (0.88, 0.80, 0.66))
    orange = flat_mi(parent_mat, "MandirOrange", (0.85, 0.42, 0.12))
    folder = "Village/Landmarks"
    spawn_mesh(CUBE, cream, "VG_ShivMandir", folder, unreal.Vector(x, y, gz + 200), (8, 8, 4), 0)
    # shikhara: stacked shrinking tiers + cone tip
    spawn_mesh(CUBE, cream, "VG_ShivMandir_T1", folder, unreal.Vector(x, y, gz + 400 + 125), (5, 5, 2.5), 0)
    spawn_mesh(CUBE, cream, "VG_ShivMandir_T2", folder, unreal.Vector(x, y, gz + 650 + 100), (3.5, 3.5, 2.0), 0)
    spawn_mesh(CONE, orange, "VG_ShivMandir_Tip", folder, unreal.Vector(x, y, gz + 850 + 150), (2.5, 2.5, 3.0), 0)


def build_school(parent_mat):
    # x kept west of ~23000: the template landscape climbs a 150 m hill
    # beyond that (probed live 2026-07-16), and the school needs flat ground.
    x, y = 22000.0, 8800.0
    gz = ground_z(x, y)
    cream = flat_mi(parent_mat, "PlasterCream", PLASTER_COLORS[1][1])
    folder = "Village/Landmarks"
    spawn_mesh(CUBE, cream, "VG_School", folder, unreal.Vector(x, y, gz + 175), (20, 8, 3.5), 12)
    spawn_mesh(CUBE, cream, "VG_School_WallN", folder, unreal.Vector(x, y + 900, gz + 75), (24, 0.2, 1.5), 12)
    spawn_mesh(CUBE, cream, "VG_School_WallS", folder, unreal.Vector(x, y - 900, gz + 75), (24, 0.2, 1.5), 12)


def build_bank(parent_mat):
    x, y = -32000.0, 16800.0  # west, on the main road (Punjab National Bank)
    gz = ground_z(x, y)
    blue = flat_mi(parent_mat, "BankBlue", (0.35, 0.45, 0.62))
    folder = "Village/Landmarks"
    spawn_mesh(CUBE, blue, "VG_Bank", folder, unreal.Vector(x, y, gz + 175), (10, 7, 3.5), -5)


def build_farm(parent_mat):
    x, y = 40000.0, -26000.0  # north-east (Nijjar Farm)
    gz = ground_z(x, y)
    barn_red = flat_mi(parent_mat, "BarnBrown", (0.5, 0.3, 0.18))
    steel = flat_mi(parent_mat, "TankSteel", (0.55, 0.58, 0.62))
    folder = "Village/Landmarks"
    spawn_mesh(CUBE, barn_red, "VG_Farm_Barn", folder, unreal.Vector(x, y, gz + 250), (14, 9, 5), 20)
    spawn_mesh(CYLINDER, steel, "VG_Farm_Silo", folder, unreal.Vector(x + 900, y - 500, gz + 450), (2.6, 2.6, 9.0), 0)
    return (x, y)


def build_pond(parent_mat, water_mat):
    x, y = 18500.0, 20500.0  # south-east of the core, off the main road
    gz = ground_z(x, y)
    mud = flat_mi(parent_mat, "FieldTilled", FIELD_COLORS[3][1])
    folder = "Village/Landmarks"
    spawn_mesh(CYLINDER, mud, "VG_Pond_Rim", folder, unreal.Vector(x, y, gz + 1.0), (32, 32, 0.02))
    pond = spawn_mesh(CYLINDER, None, "VG_Pond_Water", folder,
                      unreal.Vector(x, y, gz + 4.0), (28, 28, 0.03))
    pond.static_mesh_component.set_material(0, water_mat)
    log("pond at ({:.0f}, {:.0f}) — calm water, Lumen reflections".format(x, y))
    return (x, y)


def build_fields(parent_mat, center, extent, road_pts):
    count = 0
    field_centres = []
    span_x = min(extent.x * FIELD_MAX_FRACTION, FIELD_OUTER)
    span_y = min(extent.y * FIELD_MAX_FRACTION, FIELD_OUTER)
    x = center.x - span_x
    idx = 0
    while x <= center.x + span_x:
        y = center.y - span_y
        while y <= center.y + span_y:
            idx += 1
            dist_core = math.hypot(x - VILLAGE_CENTER[0], y - VILLAGE_CENTER[1])
            near_road = any(math.hypot(px - x, py - y) < 2200 for px, py in road_pts)
            if dist_core > FIELD_INNER and not near_road:
                name, rgb = FIELD_COLORS[idx % len(FIELD_COLORS)]
                mi = flat_mi(parent_mat, "Field" + name, rgb)
                gz = ground_z(x, y)
                spawn_mesh(PLANE, mi, "VG_Field_{:03d}".format(idx), "Village/Fields",
                           unreal.Vector(x, y, gz + 3.0),
                           (FIELD_STEP[0] / 100 - 12, FIELD_STEP[1] / 100 - 10, 1))
                count += 1
                if dist_core < 45000:
                    field_centres.append((x, y))
            y += FIELD_STEP[1]
        x += FIELD_STEP[0]
    log("{} field patches".format(count))
    return field_centres


def build_trees(parent_mat, road_pts, rng):
    trunk_mi = flat_mi(parent_mat, "TreeTrunk", (0.32, 0.22, 0.13))
    canopy_mi = flat_mi(parent_mat, "TreeCanopy", (0.20, 0.35, 0.12))
    count = 0
    for i, (x, y) in enumerate(road_pts):
        if i % max(1, int(TREE_SPACING / 1000.0)) != 0:
            continue
        side = 1 if (i // 5) % 2 == 0 else -1
        ox = x + side * rng.uniform(600, 950)
        oy = y + side * rng.uniform(-300, 300)
        gz = ground_z(ox, oy)
        spawn_mesh(CYLINDER, trunk_mi, "VG_Tree_{:03d}_T".format(count), "Village/Trees",
                   unreal.Vector(ox, oy, gz + 160), (0.45, 0.45, 3.2))
        spawn_mesh(SPHERE, canopy_mi, "VG_Tree_{:03d}_C".format(count), "Village/Trees",
                   unreal.Vector(ox, oy, gz + 480), (4.2, 4.2, 3.4))
        count += 1
    log("{} roadside trees".format(count))


def build_mountains(imported, parent_mat, rng):
    """Ring of the user's photogrammetry terrain scans around the map edge."""
    mountain_meshes = []
    for key in ("MountainHill", "MountainKula", "MountainGlacier",
                "MountainMer", "MountainTremorgio", "MountainLake"):
        mountain_meshes.extend(imported.get(key, []))

    rock_mi = flat_mi(parent_mat, "Rock", (0.36, 0.31, 0.27))
    count = 0
    for i, angle_deg in enumerate(range(0, 360, 33)):
        a = math.radians(angle_deg + rng.uniform(-8, 8))
        r = MOUNTAIN_RING_RADIUS + rng.uniform(-6000, 9000)
        x, y = r * math.cos(a), r * math.sin(a)
        yaw = rng.uniform(0, 360)
        if mountain_meshes:
            mesh = mountain_meshes[i % len(mountain_meshes)]
            spawn_model(mesh, "VG_Mountain_{:02d}".format(i), "Village/Mountains",
                        x, y, rng.uniform(45000, 75000), yaw, sink_frac=0.06)
        else:
            # fallback: big rocky cones
            s = rng.uniform(140, 260)
            gz = ground_z(x, y)
            spawn_mesh(CONE, rock_mi, "VG_Mountain_{:02d}".format(i), "Village/Mountains",
                       unreal.Vector(x, y, gz + s * 50 * 0.45), (s, s, s * 0.9), yaw)
        count += 1
    log("{} perimeter mountains ({})".format(
        count, "photogrammetry scans" if mountain_meshes else "fallback cones"))


def build_vendor_carts(imported, positions):
    carts = imported.get("Vendor", [])
    spots = []
    for i, (x, y) in enumerate(positions):
        if carts:
            spawn_model(carts[0], "VG_VendorCart_{}".format(i), "Village/Landmarks",
                        x, y, 260.0, i * 70.0)
        spots.append((x, y))
    if carts:
        log("{} vendor carts placed".format(len(positions)))
    return spots


# ------------------------------- NPCs -------------------------------------

def spawn_villagers(plots, pray_spots, field_centres, social_spots, rng):
    if not plots:
        warn("no house plots — villagers skipped")
        return
    bp = EAL.load_asset("/Game/ThirdPerson/Blueprints/BP_Villager")
    if bp is not None:
        cls = bp.generated_class()
    else:
        cls = getattr(unreal, "VillagerNPC", None)
        if cls is None:
            warn("VillagerNPC class missing — NPCs skipped (compile the module).")
            return
        warn("BP_Villager not found; spawning C++ VillagerNPC (no mesh).")

    count = min(NPC_COUNT, len(NPC_NAMES))
    for i in range(count):
        px, py = plots[i % len(plots)]
        gz = ground_z(px, py)
        npc = EAS.spawn_actor_from_class(cls, unreal.Vector(px, py - 700, gz + 100),
                                         unreal.Rotator(0, 0, rng.uniform(0, 360)))
        if npc is None:
            warn("failed to spawn villager {}".format(i))
            continue
        name = NPC_NAMES[i]
        npc.set_actor_label("VG_NPC_" + name.replace(" ", ""))
        npc.set_folder_path("Village/NPCs")
        try:
            npc.set_editor_property("villager_name", name)
            npc.set_editor_property("home_spot", unreal.Vector(px, py, gz))
            work = field_centres[i % len(field_centres)] if field_centres else (px, py)
            npc.set_editor_property("work_spot", unreal.Vector(work[0], work[1], gz))
            pray = pray_spots[i % len(pray_spots)]
            npc.set_editor_property("pray_spot", unreal.Vector(pray[0], pray[1], gz))
            social = social_spots[i % len(social_spots)] if social_spots else (px, py)
            npc.set_editor_property("social_spot", unreal.Vector(social[0], social[1], gz))
            npc.set_editor_property("stroll_speed", rng.uniform(130.0, 200.0))
        except Exception as e:
            warn("could not stamp villager {}: {}".format(name, e))
    log("{} villagers spawned".format(count))


def tune_atmosphere():
    fog = None
    sun = None
    for actor in EAS.get_all_level_actors():
        if isinstance(actor, unreal.ExponentialHeightFog):
            fog = actor
        elif isinstance(actor, unreal.DirectionalLight):
            sun = actor
    if fog is None:
        fog = EAS.spawn_actor_from_class(unreal.ExponentialHeightFog,
                                         unreal.Vector(0, 0, 200))
        fog.set_actor_label("VG_HeightFog")
        fog.set_folder_path("Village/Atmosphere")
    try:
        comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
        comp.set_editor_property("fog_density", 0.012)
        comp.set_editor_property("fog_height_falloff", 0.35)
        comp.set_editor_property("start_distance", 2500.0)
        comp.set_editor_property("fog_inscattering_luminance",
                                 unreal.LinearColor(0.45, 0.40, 0.32, 1.0))
    except Exception as e:
        warn("fog tuning failed: {}".format(e))
    if sun:
        try:
            sun.set_actor_rotation(unreal.Rotator(0.0, -38.0, 35.0), False)
            comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
            comp.set_light_color(unreal.LinearColor(1.0, 0.93, 0.80, 1.0))
        except Exception as e:
            warn("sun tuning failed: {}".format(e))


# -------------------------------- main -------------------------------------

def main():
    global _WORLD, _ZTOP, _ZBOT
    rng = random.Random(11)

    ensure_level()
    _WORLD = UES.get_editor_world()
    cleanup_previous()

    proxies, center, extent = landscape_info()
    _ZTOP = center.z + extent.z + 50000.0
    _ZBOT = center.z - extent.z - 50000.0

    imported = import_arch_models()
    house_meshes = imported.get("House", [])

    pm_dirt = make_phys_dirt()
    ground_mat = make_landscape_material(pm_dirt)
    if proxies:
        for proxy in proxies:
            proxy.set_editor_property("landscape_material", ground_mat)
        log("landscape material assigned to {} proxies".format(len(proxies)))
    parent_mat = make_flat_parent()
    water_mat = make_water_material()
    mi_road = flat_mi(parent_mat, "DirtRoad", (0.36, 0.28, 0.19))

    # Roads first: everything else keeps clear of them.
    all_road_samples = []
    seg_total = 0
    for name, pts in ROADS.items():
        seg_total += build_road(name, pts, mi_road)
        all_road_samples.extend(road_samples(pts))
    log("road network: {} splines, {} segments".format(len(ROADS), seg_total))

    # Houses along the ring, cross lanes and inner grid.
    plots = []
    house_paths = [ROADS["ring"], ROADS["lane_ns"], ROADS["lane_ew"],
                   ROADS["in_h1"], ROADS["in_h2"], ROADS["in_h3"], ROADS["in_h4"],
                   ROADS["in_v1"], ROADS["in_v2"], ROADS["in_v3"], ROADS["in_v4"]]
    for path in house_paths:
        for (x, y) in road_samples(path, step=2600.0):
            if len(plots) >= HOUSE_COUNT_CAP:
                break
            side = 1 if rng.random() < 0.5 else -1
            hx = x + side * rng.uniform(950, 1500)
            hy = y + side * rng.uniform(950, 1500)
            if math.hypot(hx, hy) > CORE_RADIUS:
                continue
            if any(math.hypot(hx - px, hy - py) < 1700 for px, py in plots):
                continue
            if any(math.hypot(hx - rx, hy - ry) < 950 for rx, ry in all_road_samples):
                continue
            plots.append((hx, hy))
            yaw = math.degrees(math.atan2(y - hy, x - hx)) + 90.0  # door faces lane
            build_house(len(plots), hx, hy, yaw, parent_mat, rng, house_meshes)
    log("{} houses ({}including the imported stylized model)".format(
        len(plots), "" if house_meshes else "NOT "))

    # Landmarks per the Pandori Nijjaran map.
    build_gurdwara("VG_Gurdwara_Ravidass", -1500, -14000, 1500, parent_mat)   # north
    build_gurdwara("VG_Gurdwara_NihangSingh", 6000, -1500, 1200, parent_mat)  # centre-east
    build_gurdwara("VG_Gurdwara_NanakDev", -2500, 2200, 1300, parent_mat)     # centre
    build_mandir(-15500, 800, parent_mat)                                     # west edge
    build_school(parent_mat)
    build_bank(parent_mat)
    farm_pos = build_farm(parent_mat)
    pond_pos = build_pond(parent_mat, water_mat)
    social_spots = build_vendor_carts(imported, [(-1200, 3300), (22600, 7400)])

    field_centres = build_fields(parent_mat, center, extent, all_road_samples)
    build_trees(parent_mat, all_road_samples, rng)
    build_mountains(imported, parent_mat, rng)
    tune_atmosphere()

    pray_spots = [(-1500, -14000), (6000, -1500), (-2500, 2200), (-15500, 800)]
    if not field_centres:
        field_centres = [farm_pos, pond_pos]
    spawn_villagers(plots, pray_spots, field_centres, social_spots or plots[:2], rng)

    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log("ENVIRONMENT v2 COMPLETE — {} total VG_ actors".format(
        sum(1 for a in EAS.get_all_level_actors()
            if a.get_actor_label().startswith("VG_"))))


main()
