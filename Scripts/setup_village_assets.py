"""
setup_village_assets.py
=======================
One-shot in-editor asset wiring for the village mini-games (idempotent —
safe to re-run). Requires the compiled rural_pardeep C++ module.

Creates / wires:
  1. IA_Sprint, IA_Interact, IA_Cancel   (duplicated from IA_Jump: Digital bool)
  2. IMC_Village                          (duplicated from IMC_Default) with
     Sprint=LShift, Interact=E/Gamepad X, Cancel=Esc/Q/Gamepad B
  3. BP_VillageCharacter                  (child of C++ VillageCharacter) with
     SKM_Quinn_Simple + ABP_Unarmed, all input assets, NS_JumpPad dust
     placeholder, DustSurfaceTypes emptied (puff on any surface until
     PM_Dirt physical materials are authored)
  4. WBP_GameHUD                          (empty child of GameHUDWidget — the
     C++ debug HUD stays active until you design this and assign it)
  5. BP_ThirdPersonGameMode.DefaultPawnClass -> BP_VillageCharacter

RUN:  py "D:/rural_games/rural_pardeep/Scripts/setup_village_assets.py"
"""

import unreal

EAL = unreal.EditorAssetLibrary

ACTIONS_DIR = "/Game/Input/Actions"
IMC_DEFAULT = "/Game/Input/IMC_Default"
IMC_VILLAGE = "/Game/Input/IMC_Village"
BP_DIR = "/Game/ThirdPerson/Blueprints"
BP_CHAR = BP_DIR + "/BP_VillageCharacter"
BP_GAMEMODE = BP_DIR + "/BP_ThirdPersonGameMode"
UI_DIR = "/Game/UI"
WBP_HUD = UI_DIR + "/WBP_GameHUD"
MESH = "/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple"
ABP = "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"
DUST_NS = "/Game/LevelPrototyping/Interactable/JumpPad/Assets/NS_JumpPad"

SAVE_LIST = []


def log(msg):
    unreal.log("[setup_village_assets] {}".format(msg))


def warn(msg):
    unreal.log_warning("[setup_village_assets] {}".format(msg))


def mark_save(path):
    if path not in SAVE_LIST:
        SAVE_LIST.append(path)


def make_key(key_name):
    try:
        return unreal.Key(key_name=key_name)
    except Exception:
        key = unreal.Key()
        key.set_editor_property("key_name", key_name)
        return key


# ---------- 1. Input Actions (duplicate IA_Jump: already Digital/bool) ----------

def ensure_input_action(name):
    path = "{}/{}".format(ACTIONS_DIR, name)
    if not EAL.does_asset_exist(path):
        if EAL.duplicate_asset(ACTIONS_DIR + "/IA_Jump", path) is None:
            raise RuntimeError("could not duplicate IA_Jump -> " + path)
        log("created " + path)
        mark_save(path)
    return EAL.load_asset(path)


# ---------- 2. IMC_Village ----------

def ensure_mapping(imc, action, key_name):
    mappings = list(imc.get_editor_property("mappings"))
    for m in mappings:
        existing = m.get_editor_property("action")
        key = m.get_editor_property("key")
        if (existing and existing.get_name() == action.get_name()
                and str(key.get_editor_property("key_name")) == key_name):
            return False
    mapping = unreal.EnhancedActionKeyMapping()
    mapping.set_editor_property("action", action)
    mapping.set_editor_property("key", make_key(key_name))
    mappings.append(mapping)
    imc.set_editor_property("mappings", mappings)
    return True


def setup_input():
    ia_sprint = ensure_input_action("IA_Sprint")
    ia_interact = ensure_input_action("IA_Interact")
    ia_cancel = ensure_input_action("IA_Cancel")

    if not EAL.does_asset_exist(IMC_VILLAGE):
        if EAL.duplicate_asset(IMC_DEFAULT, IMC_VILLAGE) is None:
            raise RuntimeError("could not duplicate IMC_Default -> IMC_Village")
        log("created " + IMC_VILLAGE + " (duplicate of IMC_Default: keeps WASD/mouse/jump)")
    imc = EAL.load_asset(IMC_VILLAGE)

    added = 0
    for action, keys in (
            (ia_sprint, ("LeftShift",)),
            (ia_interact, ("E", "Gamepad_FaceButton_Left")),
            # Esc also ends PIE, so Q is bound as a friendlier cancel in tests.
            (ia_cancel, ("Escape", "Q", "Gamepad_FaceButton_Right"))):
        for key_name in keys:
            if ensure_mapping(imc, action, key_name):
                added += 1
    if added:
        log("added {} key mappings to IMC_Village".format(added))
        mark_save(IMC_VILLAGE)
    return imc, ia_sprint, ia_interact, ia_cancel


# ---------- 3. BP_VillageCharacter ----------

def set_prop(obj, name, value, what):
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception as e:
        warn("could not set {} ({}): {}".format(what, name, e))
        return False


def setup_character(imc, ia_sprint, ia_interact, ia_cancel):
    if not hasattr(unreal, "VillageCharacter"):
        raise RuntimeError("C++ class VillageCharacter not found — compile the "
                           "rural_pardeep module and restart the editor first.")

    if not EAL.does_asset_exist(BP_CHAR):
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.VillageCharacter)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "BP_VillageCharacter", BP_DIR, unreal.Blueprint, factory)
        if bp is None:
            raise RuntimeError("failed to create BP_VillageCharacter")
        log("created " + BP_CHAR)
    else:
        bp = EAL.load_asset(BP_CHAR)

    cdo = unreal.get_default_object(bp.generated_class())

    # Input assets
    set_prop(cdo, "VillageMappingContext", imc, "mapping context")
    set_prop(cdo, "MoveAction", EAL.load_asset(ACTIONS_DIR + "/IA_Move"), "IA_Move")
    set_prop(cdo, "LookAction", EAL.load_asset(ACTIONS_DIR + "/IA_Look"), "IA_Look")
    set_prop(cdo, "JumpAction", EAL.load_asset(ACTIONS_DIR + "/IA_Jump"), "IA_Jump")
    set_prop(cdo, "SprintAction", ia_sprint, "IA_Sprint")
    set_prop(cdo, "InteractAction", ia_interact, "IA_Interact")
    set_prop(cdo, "CancelAction", ia_cancel, "IA_Cancel")

    # Footstep dust: intentionally NONE. The NS_JumpPad stand-in reads as
    # glowing rings chasing the player; better no FX than wrong FX. Assign a
    # real dust puff Niagara here when one is authored.
    set_prop(cdo, "FootstepDustSystem", None, "dust Niagara (cleared)")
    set_prop(cdo, "DustSurfaceTypes", [], "dust surface filter")

    # Mesh + anim (<PLAYER_MESH_PLACEHOLDER> stand-ins)
    try:
        mesh_comp = cdo.get_editor_property("mesh")
        sk = EAL.load_asset(MESH)
        if sk:
            try:
                mesh_comp.set_editor_property("skeletal_mesh_asset", sk)
            except Exception:
                mesh_comp.set_editor_property("skeletal_mesh", sk)
        abp = EAL.load_asset(ABP)
        if abp:
            mesh_comp.set_editor_property("animation_mode",
                                          unreal.AnimationMode.ANIMATION_BLUEPRINT)
            mesh_comp.set_editor_property("anim_class", abp.generated_class())
        log("assigned SKM_Quinn_Simple + ABP_Unarmed to the character mesh")
    except Exception as e:
        warn("mesh/anim assignment failed (assign manually in BP): {}".format(e))

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as e:
        warn("compile_blueprint failed: {}".format(e))
    mark_save(BP_CHAR)
    return bp


# ---------- 3b. BP_Villager (NPC) ----------

BP_VILLAGER = BP_DIR + "/BP_Villager"
NPC_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"


def setup_villager_bp():
    if not hasattr(unreal, "VillagerNPC"):
        warn("VillagerNPC C++ class not found — BP_Villager skipped.")
        return
    if not EAL.does_asset_exist(BP_VILLAGER):
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.VillagerNPC)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "BP_Villager", BP_DIR, unreal.Blueprint, factory)
        if bp is None:
            warn("failed to create BP_Villager")
            return
        log("created " + BP_VILLAGER)
    else:
        bp = EAL.load_asset(BP_VILLAGER)

    cdo = unreal.get_default_object(bp.generated_class())
    try:
        mesh_comp = cdo.get_editor_property("mesh")
        sk = EAL.load_asset(NPC_MESH)
        if sk:
            try:
                mesh_comp.set_editor_property("skeletal_mesh_asset", sk)
            except Exception:
                mesh_comp.set_editor_property("skeletal_mesh", sk)
        abp = EAL.load_asset(ABP)
        if abp:
            mesh_comp.set_editor_property("animation_mode",
                                          unreal.AnimationMode.ANIMATION_BLUEPRINT)
            mesh_comp.set_editor_property("anim_class", abp.generated_class())
        log("BP_Villager: SKM_Manny_Simple + ABP_Unarmed assigned")
    except Exception as e:
        warn("BP_Villager mesh/anim assignment failed: {}".format(e))

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as e:
        warn("BP_Villager compile failed: {}".format(e))
    mark_save(BP_VILLAGER)


# ---------- 4. WBP_GameHUD shell ----------

def setup_hud_widget():
    if EAL.does_asset_exist(WBP_HUD):
        return
    try:
        factory = unreal.WidgetBlueprintFactory()
        factory.set_editor_property("parent_class", unreal.GameHUDWidget)
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "WBP_GameHUD", UI_DIR, unreal.WidgetBlueprint, factory)
        log("created empty {} — design it, then set it as HUDWidgetClass on "
            "BP_VillageCharacter's InteractionComponent (the C++ debug HUD "
            "keeps the games playable until then)".format(WBP_HUD))
        mark_save(WBP_HUD)
    except Exception as e:
        warn("could not create WBP_GameHUD (create manually): {}".format(e))


# ---------- 5. GameMode default pawn ----------

def setup_gamemode(bp_char):
    gm = EAL.load_asset(BP_GAMEMODE)
    if gm is None:
        warn("BP_ThirdPersonGameMode not found; set Default Pawn manually.")
        return
    cdo = unreal.get_default_object(gm.generated_class())
    if set_prop(cdo, "DefaultPawnClass", bp_char.generated_class(), "default pawn"):
        log("GameMode default pawn -> BP_VillageCharacter")
        mark_save(BP_GAMEMODE)


def main():
    imc, ia_sprint, ia_interact, ia_cancel = setup_input()
    bp_char = setup_character(imc, ia_sprint, ia_interact, ia_cancel)
    setup_villager_bp()
    setup_hud_widget()
    setup_gamemode(bp_char)

    for path in SAVE_LIST:
        if not EAL.save_asset(path, only_if_is_dirty=True):
            warn("could not save " + path)
    log("done. PIE controls: WASD move, Shift sprint, Space jump, E interact, "
        "Q/Esc cancel.")


main()
