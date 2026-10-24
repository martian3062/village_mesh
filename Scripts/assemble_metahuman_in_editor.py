"""Run Creator assembly after normal editor/renderer initialization."""
from pathlib import Path
import runpy
import time
import unreal

unreal.EditorPythonScripting.set_keep_python_script_alive(True)
started = time.monotonic()


def tick(_dt):
    if time.monotonic() - started < 5:
        return
    unreal.unregister_slate_post_tick_callback(handle)
    try:
        runpy.run_path(str(Path(unreal.Paths.project_dir()) / 'Scripts/build_metahuman_pilot.py'), run_name='__main__')
    except Exception as exc:
        unreal.log_error('MH_PILOT_EDITOR_ASSEMBLY: ' + str(exc))
    finally:
        unreal.SystemLibrary.quit_editor()


handle = unreal.register_slate_post_tick_callback(tick)
