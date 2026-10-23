"""Download CC0 PBR sets. Uses pinned hashes once Assets/textures.lock.json exists."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "Assets/textures.lock.json"
ASSETS = ("brown_mud_leaves_01", "red_brick_03", "rough_plaster_03", "aerial_grass_rock", "asphalt_02")


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "village-mesh/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def main():
    if LOCK.exists():
        entries = json.loads(LOCK.read_text())["textures"]
    else:
        entries = []
    for asset in ASSETS:
        if any(entry["asset"] == asset for entry in entries):
            continue
        info = json.loads(fetch("https://api.polyhaven.com/files/" + asset))
        for channel, api_key in (("color", "Diffuse"), ("normal", "nor_dx"), ("roughness", "Rough")):
            record = info[api_key]["2k"]["jpg"]
            entries.append(dict(asset=asset, channel=channel, url=record["url"],
                                md5=record["md5"], source="https://polyhaven.com/a/" + asset, license="CC0-1.0"))
    dest = ROOT / "Assets/Downloaded"
    dest.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        path = dest / (entry["asset"] + "_" + entry["channel"] + ".jpg")
        data = path.read_bytes() if path.exists() else fetch(entry["url"])
        if hashlib.md5(data).hexdigest() != entry["md5"]:
            raise RuntimeError("Checksum mismatch: " + path.name)
        sha = hashlib.sha256(data).hexdigest()
        if entry.get("sha256", sha) != sha:
            raise RuntimeError("SHA256 mismatch: " + path.name)
        entry["sha256"] = sha
        path.write_bytes(data)
        print(path.name, len(data))
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps({"license_url": "https://polyhaven.com/license", "textures": entries}, indent=2) + "\n")


if __name__ == "__main__":
    main()
