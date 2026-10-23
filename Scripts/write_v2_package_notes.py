"""Attach source attribution and portable reference data to the local package."""
from pathlib import Path
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]


def main():
    package=ROOT/'Saved/Packages/V2/Windows'
    if not (package/'rural_pardeep.exe').is_file():raise RuntimeError('V2 package is missing')
    docs=package/'Documentation';docs.mkdir(exist_ok=True)
    for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):
        shutil.copyfile(ROOT/name,docs/name)
    for directory in ('Geodata','Architecture','Reference','Routes'):
        target=docs/'Assets'/directory;target.mkdir(parents=True,exist_ok=True)
        for path in (ROOT/'Assets'/directory).iterdir():
            if path.suffix in ('.json','.geojson'):shutil.copyfile(path,target/path.name)
    for name in ('textures.lock.json','models.lock.json'):
        shutil.copyfile(ROOT/'Assets'/name,docs/'Assets'/name)
    graphics=json.loads((ROOT/'Config/v2_quality.json').read_text())
    commands=','.join(graphics['cvars']+['r.ScreenPercentage '+str(graphics['playable_screen_percentage']),
        't.MaxFPS '+str(graphics['interactive_max_fps'])])
    (package/'Play_V2.cmd').write_text('@echo off\nstart "" "%~dp0rural_pardeep.exe" -windowed -ResX=1440 -ResY=900 -ForceRes "-ExecCmds='+commands+'"\n',encoding='ascii')
    (package/'README_V2.txt').write_text('''VILLAGE MESH V2 - LOCAL WINDOWS DEVELOPMENT BUILD

Launch Play_V2.cmd for the tested 1440x900 / Epic / 67% render preset.
Interactive play is capped at 60 FPS. Automated profiling remains uncapped.
The default world is Lvl_PandoriV2_WP. rural_pardeep.exe also launches directly.
WASD / mouse: walk / look. Shift: run. Space: jump.
F10: cycle through the three room entrances. Aim at a door and press E.
E also grabs/drops physics objects; right mouse throws.
F6: weather. F7: local time. F8: physics yard. F9: overview.

This is a 240 m procedural pilot on mapped Pandori Nijjaran footprints:
16 detailed frontages and three representative interiors. Building heights,
facades, room layouts and ground levels are inferred, not surveyed.
No local architectural review or independent fresh-machine test is claimed.

Source, generation scripts, full README and validation evidence:
https://github.com/martian3062/village_mesh

Original project source: MIT (Documentation/LICENSE).
The source repository's third-party notices are in Documentation.
This local executable also contains Unreal runtime components, governed by
Epic's Unreal Engine terms; Unreal itself is not MIT-licensed.
https://www.unrealengine.com/en-US/eula/unreal

Map data: OpenStreetMap contributors / Overture Maps / Microsoft / Google.
The source extracts and provider metadata are included in Documentation/Assets.
Geographic databases retain ODbL; Google source attribution retains CC BY 4.0.
CC0 textures and vegetation: Poly Haven; source URLs/checksums are included.
The Well shear-flow trace: Rudy Morel, CCM/Flatiron Institute, CC BY 4.0;
adaptation details are in rural_pardeep/Content/Well/wind.source.json.
The trace drives artistic wind playback; it is not a local weather forecast.
''',encoding='utf-8')
    print('Attached V2 package README, attribution and source manifests')


if __name__=='__main__':main()
