"""
init_unreal.py — auto-run by the Python plugin on every editor start.

One-shot bootstrap for the rural_pardeep village game. The first time the
editor starts WITH the compiled rural_pardeep C++ module it runs, in order:
  Scripts/build_environment.py     (open-world level, landscape material,
                                    roads, houses, gurdwara/school, fields,
                                    trees, atmosphere)
  Scripts/setup_village_assets.py  (input assets, BP_VillageCharacter,
                                    HUD shell, GameMode default pawn)
  Scripts/place_minigame_zones.py  (darts/kancha/kite zones, kite building,
                                    PlayerStart, NavMesh volume)
then saves everything and writes a marker so it never runs again.

Delete Saved/village_bootstrap_done.txt to force a full re-run (environment
and placement are idempotent: VG_*/MG_* actors are rebuilt cleanly).
"""

import os
import traceback

import unreal

MARKER = os.path.join(unreal.Paths.project_saved_dir(), "village_bootstrap_done.txt")
EXTRAS_MARKER = os.path.join(unreal.Paths.project_saved_dir(), "village_extras_done.txt")
UPGRADE_MARKER = os.path.join(unreal.Paths.project_saved_dir(), "village_upgrade_done.txt")
CHAR_MARKER = os.path.join(unreal.Paths.project_saved_dir(), "village_characters_done.txt")
GREENWORLD_MARKER = os.path.join(unreal.Paths.project_saved_dir(), "village_greenworld_done.txt")
POLISH_MARKER = os.path.join(unreal.Paths.project_saved_dir(), "village_polish_done.txt")
GRASSFIX_MARKER = os.path.join(unreal.Paths.project_saved_dir(), "village_grassfix_done.txt")
TREES_MARKER = os.path.join(unreal.Paths.project_saved_dir(), "village_trees_done.txt")
HOMES_MARKER = os.path.join(unreal.Paths.project_saved_dir(), "village_homes_done.txt")
_state = {"elapsed": 0.0, "handle": None, "done": False}


def _run_script(path):
    unreal.log("[village bootstrap] running {}".format(path))
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, path, "exec"), {"__name__": "__main__", "__file__": path})


def _bootstrap():
    if not hasattr(unreal, "VillageCharacter"):
        unreal.log_warning(
            "[village bootstrap] rural_pardeep C++ module not loaded — compile "
            "it, then restart the editor. Skipping.")
        return

    scripts_dir = os.path.join(unreal.Paths.project_dir(), "Scripts")

    if not os.path.exists(MARKER):
        # Asset setup FIRST: build_environment spawns BP_Villager NPCs, which
        # setup_village_assets creates.
        for script in ("setup_village_assets.py",
                       "build_environment.py",
                       "place_minigame_zones.py"):
            _run_script(os.path.join(scripts_dir, script))

    # Stage 2: GLB extras, weather, tree wind, river. Own marker so it runs
    # once even on projects whose main bootstrap finished long ago.
    if not os.path.exists(EXTRAS_MARKER):
        _run_script(os.path.join(scripts_dir, "build_extras.py"))

    # Stage 3: the finish pass — highways + conformed roads, tilted fields,
    # hollow furnished houses, real trees, cricket/kancha playgrounds,
    # grazing animals, ambient kites, wetness-aware materials.
    if not os.path.exists(UPGRADE_MARKER):
        _run_script(os.path.join(scripts_dir, "build_upgrade.py"))

    # Stage 4: Punjabi looks for the player + every villager NPC.
    if not os.path.exists(CHAR_MARKER):
        _run_script(os.path.join(scripts_dir, "build_characters.py"))

    # Stage 5: greener ground + real grass, walk-in landmark/house interiors,
    # an animated bird flock, and the minimap map texture. Additive (targeted
    # cleanup) — does NOT re-run stages 1-4.
    if not os.path.exists(GREENWORLD_MARKER):
        _run_script(os.path.join(scripts_dir, "build_greenworld.py"))

    # Stage 6: polish — leafy wind-swayed grass, doors ajar, interior lights,
    # roadmap minimap texture, footstep-FX cleanup.
    if not os.path.exists(POLISH_MARKER):
        _run_script(os.path.join(scripts_dir, "build_polish.py"))

    # Stage 7: grass exclusion mask (no grass on roads / in buildings), mixed
    # grass varieties, villager-look refresh + verification captures.
    if not os.path.exists(GRASSFIX_MARKER):
        _run_script(os.path.join(scripts_dir, "build_grassfix.py"))

    # Stage 8: real trees — tapered trunks + branches + alpha leaf cards per
    # species, replacing the stage-3 sphere-canopy lollipops.
    if not os.path.exists(TREES_MARKER):
        _run_script(os.path.join(scripts_dir, "build_trees.py"))

    # Stage 9: realistic homes — textured brick/plaster walls, glass windows,
    # verandas, pilasters, cornices, rooftop mumty/tank, replacing flat boxes.
    if not os.path.exists(HOMES_MARKER):
        _run_script(os.path.join(scripts_dir, "build_homes.py"))

    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        unreal.log("[village bootstrap] all dirty packages saved")
    except Exception as e:
        unreal.log_warning("[village bootstrap] save failed: {}".format(e))

    with open(MARKER, "w") as f:
        f.write("bootstrap completed")
    with open(EXTRAS_MARKER, "w") as f:
        f.write("extras completed")
    with open(UPGRADE_MARKER, "w") as f:
        f.write("upgrade completed")
    with open(CHAR_MARKER, "w") as f:
        f.write("characters completed")
    with open(GREENWORLD_MARKER, "w") as f:
        f.write("greenworld completed")
    with open(POLISH_MARKER, "w") as f:
        f.write("polish completed")
    with open(GRASSFIX_MARKER, "w") as f:
        f.write("grassfix completed")
    with open(TREES_MARKER, "w") as f:
        f.write("trees completed")
    with open(HOMES_MARKER, "w") as f:
        f.write("homes completed")
    unreal.log("[village bootstrap] COMPLETE — markers written")


def _tick(delta_seconds):
    # init_unreal.py runs too early in editor boot; wait for the editor and
    # startup map to settle before building the world.
    _state["elapsed"] += delta_seconds
    if _state["done"] or _state["elapsed"] < 12.0:
        return
    _state["done"] = True
    unreal.unregister_slate_post_tick_callback(_state["handle"])
    try:
        _bootstrap()
    except Exception as e:
        unreal.log_error("[village bootstrap] FAILED: {}".format(e))
        unreal.log_error(traceback.format_exc())


if not unreal.SystemLibrary.parse_param(unreal.SystemLibrary.get_command_line(), "VillageLegacyBootstrap"):
    unreal.log("[village bootstrap] legacy rebuild disabled; run Scripts/build_open_world.py for the portable world")
elif (os.path.exists(MARKER) and os.path.exists(EXTRAS_MARKER)
        and os.path.exists(UPGRADE_MARKER) and os.path.exists(CHAR_MARKER)
        and os.path.exists(GREENWORLD_MARKER) and os.path.exists(POLISH_MARKER)
        and os.path.exists(GRASSFIX_MARKER) and os.path.exists(TREES_MARKER)
        and os.path.exists(HOMES_MARKER)):
    unreal.log("[village bootstrap] already completed; skipping (delete a marker in {} to re-run)".format(
        unreal.Paths.project_saved_dir()))
else:
    _state["handle"] = unreal.register_slate_post_tick_callback(_tick)
