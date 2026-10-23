"""
build_characters.py  (stage 4)
==============================
Punjabi looks for everyone. The project has no human skeletal meshes, so the
mannequins are dressed instead (C++ FVillagerLook + VillagerLookUtil::Apply):
cloth-replaced bodies (kurta/kameez), skin-toned face overlay with eyes+nose,
pagri + beard for the men, chunni for the women.

This script:
  1. creates M_VGClothBase (Color + Rough params) that the C++ MIDs use,
  2. gives the PLAYER (BP_VillageCharacter CDO) a Manny body, white kurta and
     navy pagri,
  3. gives BP_Villager sensible defaults,
  4. stamps each spawned VG_NPC_* instance with its own palette; the three
     women (Simran Kaur, Amrita, Nimrat Kaur) get the Quinn mesh + chunni.

Idempotent — re-running just re-stamps the same values.
RUN (auto via init_unreal.py when Saved/village_characters_done.txt missing):
  py "D:/rural_games/rural_pardeep/Scripts/build_characters.py"
"""

import unreal

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MEL = unreal.MaterialEditingLibrary

MAT_DIR = "/Game/Village/Materials"
CLOTH_BASE = MAT_DIR + "/M_VGClothBase"
BP_CHAR = "/Game/ThirdPerson/Blueprints/BP_VillageCharacter"
BP_VILLAGER = "/Game/ThirdPerson/Blueprints/BP_Villager"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
QUINN = "/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple"

FEMALES = {"SimranKaur", "Amrita", "NimratKaur"}

# (kurta/kameez, pagri/chunni, skin, beard_style) — beard ignored for women
MALE_PALETTES = [
    ((0.93, 0.90, 0.80), (0.90, 0.42, 0.06), (0.42, 0.25, 0.14), 1),  # white + kesri
    ((0.82, 0.66, 0.28), (0.10, 0.16, 0.40), (0.36, 0.21, 0.11), 1),  # mustard + navy
    ((0.55, 0.58, 0.36), (0.55, 0.08, 0.10), (0.46, 0.28, 0.16), 2),  # olive + maroon
    ((0.62, 0.74, 0.82), (0.92, 0.90, 0.86), (0.40, 0.24, 0.13), 1),  # sky + white
    ((0.88, 0.78, 0.66), (0.08, 0.32, 0.18), (0.33, 0.19, 0.10), 0),  # sand + green
    ((0.80, 0.52, 0.46), (0.28, 0.10, 0.34), (0.44, 0.26, 0.15), 2),  # clay + purple
]
FEMALE_PALETTES = [
    ((0.78, 0.24, 0.30), (0.95, 0.75, 0.20), (0.42, 0.25, 0.14)),     # red kameez + gold chunni
    ((0.30, 0.55, 0.45), (0.92, 0.88, 0.80), (0.37, 0.22, 0.12)),     # teal + white
    ((0.85, 0.55, 0.65), (0.45, 0.12, 0.30), (0.45, 0.27, 0.15)),     # pink + plum
]

# Head-bone -> overlay frame calibration shared by everyone (tuned visually).
FRAME_OFFSET = (0.0, 0.0, 0.0)
# Calibrated 2026-07-17 (live, via unreal-mcp CaptureViewport loop on VG_NPC_Manpreet):
# the UE5 Manny/Quinn "head" bone local frame is the component frame rolled -90 deg
# about the forward axis (bone X=fwd, Y=down, Z=right). A +90 roll maps the overlay's
# authored +X=face-forward / +Z=up back onto world fwd/up. Offset 0 seats it correctly.
FRAME_ROTATION = (0.0, 0.0, 90.0)  # (pitch, yaw, roll)


def log(msg):
    unreal.log("[build_characters] {}".format(msg))


def warn(msg):
    unreal.log_warning("[build_characters] {}".format(msg))


def make_cloth_base():
    if EAL.does_asset_exist(CLOTH_BASE):
        return EAL.load_asset(CLOTH_BASE)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_VGClothBase", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    colour = MEL.create_material_expression(
        mat, unreal.MaterialExpressionVectorParameter, -700, -80)
    colour.set_editor_property("parameter_name", "Color")
    colour.set_editor_property("default_value",
                               unreal.LinearColor(0.8, 0.8, 0.8, 1.0))
    # faint weave/wrinkle variation so cloth isn't dead flat
    noise = MEL.create_material_expression(
        mat, unreal.MaterialExpressionNoise, -700, 140)
    noise.set_editor_property("scale", 0.05)
    noise.set_editor_property("output_min", 0.82)
    noise.set_editor_property("output_max", 1.05)
    mul = MEL.create_material_expression(
        mat, unreal.MaterialExpressionMultiply, -420, 0)
    MEL.connect_material_expressions(colour, "", mul, "A")
    MEL.connect_material_expressions(noise, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rough = MEL.create_material_expression(
        mat, unreal.MaterialExpressionScalarParameter, -420, 220)
    rough.set_editor_property("parameter_name", "Rough")
    rough.set_editor_property("default_value", 0.85)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_asset(CLOTH_BASE)
    log("created M_VGClothBase")
    return mat


def make_look(cloth, headwear, skin, female=False, beard=1):
    look = unreal.VillagerLook()
    # UE python strips the 'b' prefix from bool UPROPERTYs: bFemale -> "female"
    look.set_editor_property("female", female)
    look.set_editor_property("cloth_color",
                             unreal.LinearColor(cloth[0], cloth[1], cloth[2], 1.0))
    look.set_editor_property("headwear_color",
                             unreal.LinearColor(headwear[0], headwear[1], headwear[2], 1.0))
    look.set_editor_property("skin_tone",
                             unreal.LinearColor(skin[0], skin[1], skin[2], 1.0))
    look.set_editor_property("beard_style", 0 if female else beard)
    look.set_editor_property("frame_offset", unreal.Vector(*FRAME_OFFSET))
    look.set_editor_property("frame_rotation", unreal.Rotator(
        FRAME_ROTATION[2], FRAME_ROTATION[0], FRAME_ROTATION[1]))
    return look


def set_mesh(target, mesh_path):
    comp = None
    try:
        comp = target.get_editor_property("mesh")
    except Exception:
        pass
    if comp is None:
        try:
            comp = target.get_component_by_class(unreal.SkeletalMeshComponent)
        except Exception:
            pass
    if comp is None:
        return False
    sk = EAL.load_asset(mesh_path)
    if sk is None:
        return False
    try:
        comp.set_editor_property("skeletal_mesh_asset", sk)
    except Exception:
        comp.set_editor_property("skeletal_mesh", sk)
    return True


def dress_player():
    bp = EAL.load_asset(BP_CHAR)
    if bp is None:
        warn("BP_VillageCharacter missing — player skipped")
        return
    cdo = unreal.get_default_object(bp.generated_class())
    if set_mesh(cdo, MANNY):
        log("player mesh -> SKM_Manny_Simple")
    look = make_look((0.93, 0.90, 0.82), (0.12, 0.20, 0.48), (0.42, 0.25, 0.14),
                     female=False, beard=1)
    try:
        cdo.set_editor_property("appearance", look)
    except Exception as e:
        warn("player look failed: {}".format(e))
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as e:
        warn("player BP compile: {}".format(e))
    EAL.save_asset(BP_CHAR)
    log("player dressed: white kurta, navy pagri")


def dress_villager_defaults():
    bp = EAL.load_asset(BP_VILLAGER)
    if bp is None:
        warn("BP_Villager missing — defaults skipped")
        return
    cdo = unreal.get_default_object(bp.generated_class())
    c, h, s, b = MALE_PALETTES[0]
    try:
        cdo.set_editor_property("appearance", make_look(c, h, s, beard=b))
    except Exception as e:
        warn("villager default look failed: {}".format(e))
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as e:
        warn("villager BP compile: {}".format(e))
    EAL.save_asset(BP_VILLAGER)


def dress_npcs():
    males = 0
    females = 0
    for actor in EAS.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue
        if not label.startswith("VG_NPC_"):
            continue
        name = label[len("VG_NPC_"):]
        if name in FEMALES:
            c, h, s = FEMALE_PALETTES[females % len(FEMALE_PALETTES)]
            look = make_look(c, h, s, female=True)
            if not set_mesh(actor, QUINN):
                warn("{}: Quinn mesh swap failed".format(name))
            females += 1
        else:
            c, h, s, b = MALE_PALETTES[males % len(MALE_PALETTES)]
            look = make_look(c, h, s, beard=b)
            males += 1
        try:
            actor.set_editor_property("appearance", look)
        except Exception as e:
            warn("{}: look failed: {}".format(name, e))
    log("NPCs dressed: {} men, {} women".format(males, females))


def main():
    make_cloth_base()
    dress_player()
    dress_villager_defaults()
    dress_npcs()
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("all dirty packages saved")
    except Exception as e:
        warn("save failed: {}".format(e))
    log("CHARACTERS DONE")


if __name__ == "__main__":
    main()
