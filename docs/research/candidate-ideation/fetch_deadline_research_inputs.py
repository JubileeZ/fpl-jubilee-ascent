from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path.cwd()
WORK = ROOT / ".tmp/agent/ext38-ext39"
MIRROR = WORK / "mirror"
ALLOWED = {
    "Randdalf/fplcache",
    "vaastav/Fantasy-Premier-League",
    "arshadfaizan360/fpl-data-mirror",
}


def fetch(destination: Path, url: str, digest: str) -> None:
    site = urlparse(url)
    repo = "/".join(site.path.strip("/").split("/")[:2])
    if (
        site.scheme != "https"
        or site.netloc != "raw.githubusercontent.com"
        or repo not in ALLOWED
    ):
        raise ValueError(f"Unexpected pinned URL {url}")
    if destination.is_file() and sha256(destination.read_bytes()).hexdigest() == digest:
        return
    for attempt in range(3):
        try:
            with urlopen(url, timeout=30) as response:
                payload = response.read(40_000_001)
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    if len(payload) > 40_000_000 or sha256(payload).hexdigest() != digest:
        raise ValueError(
            f"Pinned input failed size or digest verification: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)


def main() -> None:
    manifest = json.loads(
        (ROOT / "config/dev_mirror_2025_26_manifest.json").read_bytes()
    )
    if manifest["season"] != "2025-26":
        raise ValueError("Expected development season")
    items: dict[Path, tuple[str, str]] = {}
    for origin in manifest["origins"]:
        for field in ("bootstrap", "settled_outcomes", "fixtures"):
            if field == "fixtures" and origin["gw"] > 7:
                continue
            receipt = origin[field]
            path = (MIRROR / receipt["local_relpath"]).resolve()
            if not path.is_relative_to(MIRROR):
                raise ValueError("Fixture mirror path escaped workspace")
            items[path] = receipt["url"], receipt["blob_sha256"]
    table = ROOT / "docs/research/candidate-ideation/s1_historical_fixture_sources.csv"
    with table.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["season"] != "2025-26":
                raise ValueError("Unexpected fixture season")
            gw = int(row["origin_gw"])
            if gw > 7:
                items[WORK / "fixtures" / f"gw{gw:02d}.json"] = (
                    row["source_url"],
                    row["sha256"],
                )
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = [
            pool.submit(fetch, path, url, digest)
            for path, (url, digest) in items.items()
        ]
        for job in jobs:
            job.result()
    print(f"Verified {len(items)} pinned development source files")


if __name__ == "__main__":
    main()
