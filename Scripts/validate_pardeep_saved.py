"""Reload the saved appearance in a fresh commandlet, independent of assembly."""
import datetime
import json
from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir())
out=root/'Saved/PardeepPlayer';out.mkdir(parents=True,exist_ok=True)
report={'passed':False,'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
try:
    eal=unreal.EditorAssetLibrary
    assets=eal.list_assets('/Game/MetaHumanPilot/Pardeep',recursive=True,include_folder=False)
    if len(assets)<300:raise RuntimeError('Pardeep assembly is incomplete')
    for path in assets:
        if not eal.load_asset(path):raise RuntimeError('Saved asset could not be reloaded: '+path)
    actor_path='/Game/MetaHumanPilot/Pardeep/Assembled/BP_Pardeep'
    if not eal.load_blueprint_class(actor_path):raise RuntimeError('Runtime Blueprint class could not be loaded')
    if not eal.load_asset('/Game/VillageMeshV3/Player/Headwear/SM_PardeepTurban'):raise RuntimeError('Turban mesh is missing')
    report.update(passed=True,reloaded_assets=len(assets),runtime_blueprint=actor_path,
                  scope='Fresh-process asset reload; gameplay and likeness require separate checks')
    unreal.log('PARDEEP_SAVED_ASSETS_RELOADED')
except Exception as exc:
    report['error']=str(exc);raise
finally:
    (out/'saved_asset_check.json').write_text(json.dumps(report,indent=2)+'\n')
