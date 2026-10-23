"""Fetch CC0 vegetation with checksummed geometry and original texture dependencies."""
import hashlib
import json
from pathlib import Path
from fetch_open_assets import fetch

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "Assets/models.lock.json"


def main():
    if LOCK.exists():
        entries = json.loads(LOCK.read_text())["files"]
    else:
        entries = []
        for asset, resolution in (("tree_small_02", "2k"), ("shrub_01", "1k")):
            info = json.loads(fetch("https://api.polyhaven.com/files/" + asset))
            record = info["fbx"][resolution]["fbx"]
            dependencies = {asset + "_" + resolution + ".fbx": record, **record.get("include", {})}
            for relative, item in dependencies.items():
                entries.append(dict(path=asset + "/" + relative, url=item["url"], md5=item["md5"],
                    source="https://polyhaven.com/a/" + asset, license="CC0-1.0"))
    for entry in entries:
        path = ROOT / "Assets/Downloaded/Models" / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes() if path.exists() else fetch(entry["url"])
        if hashlib.md5(data).hexdigest() != entry["md5"]:
            raise ValueError("Source checksum mismatch: " + entry["path"])
        sha = hashlib.sha256(data).hexdigest()
        if entry.get("sha256", sha) != sha:
            raise ValueError("Locked checksum mismatch: " + entry["path"])
        entry["sha256"] = sha
        path.write_bytes(data)
        print(entry["path"], len(data), flush=True)
    LOCK.write_text(json.dumps({"license_url": "https://polyhaven.com/license", "files": entries}, indent=2) + "\n")


if __name__ == "__main__":
    main()
