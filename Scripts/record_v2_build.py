"""Record the final source/package fingerprint after packaging restores authoring files."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def source_digest(path):
    # Git preserves these pinned data bytes, while source text can use CRLF on Windows.
    relative=path.relative_to(ROOT).as_posix()
    if path.suffix=='.geojson' or path.name.endswith('.osm.json') or relative=='Content/Well/wind.csv':
        return digest(path)
    return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def main():
    files=set()
    for directory in ('Scripts','Source','Config','Assets/Architecture','Assets/Reference','Assets/Routes','Assets/Geodata'):
        files.update(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in ('.py','.ps1','.cpp','.h','.cs','.ini','.json','.geojson'))
    files.add(ROOT/'rural_pardeep.uproject')
    for relative in ('Assets/textures.lock.json','Assets/models.lock.json','Content/Well/wind.csv','Content/Well/wind.source.json','Content/Validation/pilot.json'):
        files.add(ROOT/relative)
    # NUL delimiters avoid Windows text-mode CRLF translation changing path names.
    ignored_result=subprocess.run(['git','check-ignore','-z','--stdin'],cwd=ROOT,
        input=('\0'.join(p.relative_to(ROOT).as_posix() for p in files)+'\0').encode('utf-8'),capture_output=True)
    if ignored_result.returncode not in (0,1):raise RuntimeError(ignored_result.stderr.decode('utf-8'))
    ignored=set(ignored_result.stdout.decode('utf-8').split('\0'))
    files={p for p in files if p.relative_to(ROOT).as_posix() not in ignored}
    generated=json.loads((ROOT/'Saved/VillageMeshV2/generation_manifest.json').read_text())
    restored={p:digest(ROOT/p)==generated['input_sha256'][p] for p in ('Config/DefaultEngine.ini','rural_pardeep.uproject')}
    if not all(restored.values()):raise RuntimeError('Authoring descriptor/config does not match the pre-package generation snapshot')
    package=ROOT/'Saved/Packages/V2/Windows'
    package_files={str(p.relative_to(package)).replace('\\','/'):dict(bytes=p.stat().st_size,sha256=digest(p))
        for p in sorted(package.rglob('*')) if p.is_file() and p.suffix in ('.exe','.pak','.utoc','.ucas')}
    if not package_files:raise RuntimeError('No cooked package artifacts found')
    result=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),engine='5.8.3',
        authoring_files_restored=restored,
        source_hash_convention='UTF-8 text uses canonical LF newlines. GeoJSON, OSM JSON and wind.csv retain exact pinned bytes. Package artifacts use exact bytes.',
        source_sha256={str(p.relative_to(ROOT)).replace('\\','/'):source_digest(p) for p in sorted(files)},
        runtime_manifest_sha256=digest(ROOT/'Content/Validation/pilot.json'),
        package_files=package_files,
        note='Final source/runtime fingerprint. The earlier generation_manifest records the geometry build before later diagnostic and V2 rain-material refinements; no V1 map assets were regenerated.')
    (ROOT/'Docs/V2/build_manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(source_files=len(files),package_files=len(package_files),authoring_files_restored=restored)))


if __name__=='__main__':main()
