"""Defer the character build until normal editor services have initialized."""
from pathlib import Path
import runpy
import time
import unreal

unreal.EditorPythonScripting.set_keep_python_script_alive(True)
started=time.monotonic()

def quit_tick(_dt):
    if time.monotonic()-finished<2:return
    unreal.unregister_slate_post_tick_callback(quit_handle)
    unreal.SystemLibrary.quit_editor()

def tick(_dt):
    global finished,quit_handle
    if time.monotonic()-started<5:return
    unreal.unregister_slate_post_tick_callback(handle)
    try:runpy.run_path(str(Path(unreal.Paths.project_dir())/'Scripts/build_pardeep_character.py'),run_name='__main__')
    except Exception as exc:unreal.log_error('PARDEEP_CHARACTER_BUILD: '+str(exc))
    finally:
        # Let pending asset notifications run before shutting down the editor.
        finished=time.monotonic()
        quit_handle=unreal.register_slate_post_tick_callback(quit_tick)
handle=unreal.register_slate_post_tick_callback(tick)
