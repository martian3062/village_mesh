"""Open an isolated PIE pilot without saving changes to the village map."""
import datetime
import json
from pathlib import Path
import unreal

unreal.EditorPythonScripting.set_keep_python_script_alive(True)
root = Path(unreal.Paths.project_dir())
output = root / 'Saved/MetaHumanPilot/pie_bootstrap.json'
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world = editor.get_editor_world()
settings = world.get_world_settings()
original_mode = settings.get_editor_property('default_game_mode')
pilot_mode = unreal.load_class(None, '/Script/rural_pardeep.MetaHumanPilotGameMode')
if not pilot_mode:
    raise RuntimeError('Build the native pilot before opening PIE')
settings.set_editor_property('default_game_mode', pilot_mode)
state = {'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'status': 'requested', 'map_saved': False, 'original_game_mode_restored': False}
output.write_text(json.dumps(state, indent=2) + '\n')
elapsed = 0.0


def tick(dt):
    global elapsed
    elapsed += dt
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    if worlds or elapsed > 90:
        settings.set_editor_property('default_game_mode', original_mode)
        state['original_game_mode_restored'] = True
        state['status'] = 'PIE_started' if worlds else 'failed_to_start'
        state['pie_worlds'] = [w.get_path_name() for w in worlds]
        output.write_text(json.dumps(state, indent=2) + '\n')
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
level.editor_request_begin_play()
