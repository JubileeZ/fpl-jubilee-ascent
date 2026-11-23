"""Recover the pinned EXT-40 research inputs and stage the Development issues."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path

from fetch_deadline_research_inputs import fetch
import historical_replay_inputs


def prepare(work: Path) -> None:
    """Recover immutable Dev and source files. Do not acquire new snapshots."""
    root = historical_replay_inputs.REPO
    mirror = work / "mirror"
    downloads: dict[Path, tuple[str, str]] = {}
    for season in ("2025-26", "2024-25"):
        manifest_path = root / "config" / f"dev_mirror_{season.replace('-', '_')}_manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        if manifest["season"] != season:
            raise ValueError(f"Unexpected manifest season {manifest_path}")
        for origin in manifest["origins"]:
            for field in ("bootstrap", "settled_outcomes", "fixtures"):
                receipt = origin[field]
                if field == "fixtures" and season == "2025-26" and origin["gw"] > historical_replay_inputs.PREFIX_END:
                    continue
                if field in ("bootstrap", "fixtures") and receipt.get("status") != "supported":
                    continue
                path = (mirror / receipt["local_relpath"]).resolve()
                if not path.is_relative_to(mirror / season):
                    raise ValueError(f"Unexpected mirror path {path}")
                downloads[path] = receipt["url"], receipt["blob_sha256"]

    with historical_replay_inputs.SOURCE_PATH.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["season"] != "2025-26":
                raise ValueError("Unexpected development fixture season")
            gameweek = int(row["origin_gw"])
            if gameweek > historical_replay_inputs.PREFIX_END:
                fixture = work / "fixtures" / f"gw{gameweek:02d}.json"
                downloads[fixture] = row["source_url"], row["sha256"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = [pool.submit(fetch, path, url, digest) for path, (url, digest) in downloads.items()]
        for job in jobs:
            job.result()
    print(f"Verified {len(downloads)} historical source files", flush=True)
    historical_replay_inputs.MIRROR_ROOT = mirror
    historical_replay_inputs.stage_s1_inputs(work)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    prepare(args.work.resolve())


if __name__ == "__main__":
    main()
