"""Refine headwear and assembled materials without repeating cloud rigging."""
import json
from pathlib import Path
import runpy
import sys
import unreal
root=Path(unreal.Paths.project_dir());sys.path.insert(0,str(root/'Scripts'))
from pardeep_character_finish import finish_materials
path=root/'Saved/PardeepPlayer/character_build.json'
report=json.loads(path.read_text())
if not report['passed']:raise RuntimeError('Assemble the Pardeep character first')
finish_materials(report)
runpy.run_path(str(root/'Scripts/build_pardeep_turban.py'),run_name='__main__')
path.write_text(json.dumps(report,indent=2)+'\n')
unreal.log('PARDEEP_APPEARANCE_REFINED')
