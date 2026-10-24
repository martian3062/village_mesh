"""Attach portable attribution, authored contracts and exact graphics launcher."""
from pathlib import Path
import json,shutil
from readme_sections import export_notices, export_package_readme
ROOT=Path(__file__).resolve().parents[1]
def main():
    package=ROOT/'Saved/Packages/V25/Windows'
    if not (package/'rural_pardeep.exe').exists():raise RuntimeError('Package missing')
    docs=package/'Documentation';docs.mkdir(exist_ok=True)
    for name in ('LICENSE',):shutil.copyfile(ROOT/name,docs/name)
    export_package_readme(docs/'README.md')
    export_notices(docs/'THIRD_PARTY_NOTICES.txt')
    for name in ('NPC','Farms','Roads','Wardrobe','Dialogue','Models','Fonts'):
        target=docs/'Assets'/name;target.mkdir(parents=True,exist_ok=True)
        for path in (ROOT/'Assets'/name).iterdir():
            if path.is_file():shutil.copyfile(path,target/path.name)
    shutil.copyfile(ROOT/'Assets/v25_assets.lock.json',docs/'Assets/v25_assets.lock.json')
    routes=docs/'Assets/Routes';routes.mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'Assets/Routes/tractor_route.json',routes/'tractor_route.json')
    target_docs=docs/'Docs/V25';target_docs.mkdir(parents=True,exist_ok=True)
    for path in (ROOT/'Docs/V25').iterdir():
        if path.is_file():shutil.copyfile(path,target_docs/path.name)
    shutil.copyfile(ROOT/'Docs/V25_ACCEPTANCE.txt',docs/'Docs/V25_ACCEPTANCE.txt')
    q=json.loads((ROOT/'Config/v2_quality.json').read_text());commands=','.join(q['cvars']+['r.ScreenPercentage 67','t.MaxFPS 60'])
    (package/'Play_V25.cmd').write_text('@echo off\nstart "" "%~dp0rural_pardeep.exe" -VillageV25 -windowed -ResX=1440 -ResY=900 -ForceRes "-ExecCmds='+commands+'"\n',encoding='ascii')
    (package/'README_V25.txt').write_text('''VILLAGE MESH V2.5 - LOCAL WINDOWS DEVELOPMENT PROTOTYPE

Run Play_V25.cmd. The activation flag is required: -VillageV25.
WASD/mouse walk/look; Shift run; E doors/objects; T talk; 1-5 dialogue choices.
F11 farms; F5 experimental policy toggle; F6 weather; F7 time; F10 V2 rooms.
Interactive preset: Epic scalability, 1440x900, 67% render scale, 60 FPS cap.

Eight named fictional adults, four inferred demonstration plots, an authored
access graph, passage reservations, draft Punjabi subtitles and local save state.
Character and tractor geometry are original procedural prototypes. They are not
accepted as locally accurate wardrobe or a finished vehicle/animation rig.
No recorded voices, intent classifier or language decoder are shipped.
Detailed guide and validation: Documentation/README.md, V2.5 sections.

The action policy has 121,520 unique learned parameters. Rules are the default.
F5 enables experimental learned ranking; missing/failed inference retains rules.
Synthetic imitation accuracy does not demonstrate better real-world behaviour.
Noto Sans Gurmukhi and its OFL licence are included in Content/V25/Fonts and
Documentation/Assets/Fonts. All Punjabi lines remain visibly marked draft.

Source and rebuild instructions:
https://github.com/martian3062/village_mesh

Original code/model: MIT. Unreal runtime: Epic's Unreal Engine licence.
Unreal itself is not open source under MIT.
https://www.unrealengine.com/en-US/eula/unreal
Map sources: OpenStreetMap / Overture / Microsoft / Google; ODbL / CC BY 4.0.
The Well trace: Rudy Morel, CCM/Flatiron Institute, CC BY 4.0.
Poly Haven textures/vegetation: CC0. See Documentation/THIRD_PARTY_NOTICES.txt.

This local Development build is not a fresh-machine-certified shipping release.
''',encoding='utf-8')
    print('V2.5 package notes, attribution and authored source contracts copied.')
if __name__=='__main__':main()
