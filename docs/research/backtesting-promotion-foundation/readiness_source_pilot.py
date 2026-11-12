"""Bounded public source recovery; quarantined inputs, no model or replay imports."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import lzma
import math
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

TOPIC = Path(__file__).resolve().parent
ROOT = TOPIC.parents[2]
OUTPUT = ROOT / "data/reports/readiness-source-pilot/v1"
REPOS = ("Randdalf/fplcache", "vaastav/Fantasy-Premier-League")
MAX_BYTES = 10 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def timeout_handler(signum: int, frame: Any) -> None:
    raise TimeoutError("public request wall-clock limit")


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    prefix = parsed.path.removeprefix("/repos/").lstrip("/")
    if parsed.scheme != "https" or parsed.hostname not in {
        "api.github.com", "raw.githubusercontent.com"
    } or not any(prefix.startswith(repo + "/") for repo in REPOS):
        raise ValueError("outside approved public source repositories")


class Fetcher:
    def __init__(self, output: Path, resume: bool = False) -> None:
        if not resume:
            output.mkdir(parents=True, exist_ok=False)
        self.output = output
        self.started = time.monotonic()
        self.count = 0
        self.bytes = 0
        self.records: list[dict[str, Any]] = []
        if resume:
            previous = json.loads((output / "summary.json").read_text())
            self.count = previous["requests"]
            self.bytes = previous["downloaded_bytes"]
            self.records = previous["attempts"]
            first = datetime.fromisoformat(self.records[0]["retrieval_utc"])
            self.started -= (datetime.now(timezone.utc) - first).total_seconds()
        self.opener = build_opener(NoRedirect())

    def log(self, row: dict[str, Any]) -> None:
        with (self.output / "attempts.jsonl").open("a") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def fetch(self, label: str, url: str, expected: str = "") -> bytes | None:
        validate_url(url)
        remaining = 1800 - (time.monotonic() - self.started)
        if self.count >= 30 or self.bytes >= MAX_BYTES or remaining <= 0:
            raise RuntimeError("phase resource cap exhausted")
        self.count += 1
        row: dict[str, Any] = {"attempt": self.count, "label": label, "url": url,
                              "retrieval_utc": datetime.now(timezone.utc).isoformat()}
        self.log({**row, "event": "start"})
        payload = bytearray()
        previous = signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, min(30, remaining))
        try:
            request = Request(url, headers={"User-Agent": "readiness-source-pilot"})
            with self.opener.open(request, timeout=min(30, remaining)) as response:
                while True:
                    chunk = response.read(min(65536, MAX_BYTES - self.bytes))
                    if not chunk:
                        break
                    payload.extend(chunk)
                    self.bytes += len(chunk)
                    if self.bytes >= MAX_BYTES:
                        raise RuntimeError("aggregate download cap reached")
            raw = bytes(payload)
            sha = hashlib.sha256(raw).hexdigest()
            (self.output / f"{self.count:02}-{label}.raw").write_bytes(raw)
            row.update(bytes=len(raw), sha256=sha, expected_sha256=expected,
                       status="hash_mismatch" if expected and sha != expected else "recovered")
            return raw if row["status"] == "recovered" else None
        except (OSError, ValueError, RuntimeError, HTTPError) as exc:
            if payload:
                (self.output / f"{self.count:02}-{label}.partial").write_bytes(payload)
            row.update(status="unavailable", bytes=len(payload), error=f"{type(exc).__name__}: {exc}")
            return None
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)
            self.records.append(row)
            self.log({**row, "event": "finish"})


def unpack(raw: bytes) -> bytes:
    decoder = lzma.LZMADecompressor()
    decoded = decoder.decompress(raw, max_length=16 * 1024 * 1024 + 1)
    if len(decoded) > 16 * 1024 * 1024 or not decoder.eof:
        raise ValueError("decoded size cap or incomplete stream")
    return decoded


def bootstrap_audit(raw: bytes, gw: int) -> dict[str, Any]:
    data = json.loads(unpack(raw))
    fields = ("id", "team", "element_type", "now_cost", "selected_by_percent",
              "status", "chance_of_playing_next_round", "news", "news_added")
    players = [{key: row.get(key) for key in fields} for row in data["elements"]]
    ids = [row["id"] for row in players]
    required = fields[:6]
    invalid = 0
    for row in players:
        try:
            invalid += int(not (math.isfinite(float(row["now_cost"])) and float(row["now_cost"]) > 0
                               and 0 <= float(row["selected_by_percent"]) <= 100
                               and int(row["element_type"]) in (1, 2, 3, 4)))
        except (TypeError, ValueError, OverflowError):
            invalid += 1
    events = [{key: row.get(key) for key in ("id", "deadline_time", "is_next")}
              for row in data["events"] if row["id"] == gw]
    return {"rows": len(players), "duplicate_ids": len(ids) - len(set(ids)),
            "missing_required_cells": sum(row[key] is None for row in players for key in required),
            "invalid_price_ownership_position_rows": invalid, "deadline": events,
            "null_next_round_chance": sum(row["chance_of_playing_next_round"] is None for row in players),
            "input_sample": players[:2], "fields": list(fields)}


def fixture_audit(raw: bytes) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    fields = ("id", "event", "team_h", "team_a", "kickoff_time", "provisional_start_time")
    rows = [{key: row.get(key) for key in fields} for row in reader]
    window = [row for row in rows if row["event"] and 2 <= int(row["event"]) <= 7]
    ids = [row["id"] for row in window]
    return {"header": reader.fieldnames, "rows": len(rows), "window_rows": len(window),
            "duplicate_window_ids": len(ids) - len(set(ids)),
            "missing_window_input_cells": sum(row[key] in (None, "") for row in window
                                              for key in ("id", "event", "team_h", "team_a", "kickoff_time")),
            "window_event_counts": {str(gw): sum(row["event"] == str(gw) for row in window)
                                    for gw in range(2, 8)}, "input_sample": window[:2]}


def run(resume: bool = False) -> None:
    fetcher = Fetcher(OUTPUT, resume=resume)
    result: dict[str, Any] = {"origin": "2025-26 GW2", "scope": "source feasibility only",
                             "status": "partial", "checks": {}, "commit_metadata": {}}
    try:
        with (TOPIC / "acquisition_manifest.csv").open() as handle:
            sources = [row for row in csv.DictReader(handle) if row["season"] == "2025-26"
                       and row["kind"] in ("opening_bootstrap", "origin_bootstrap_pilot", "fixture_pilot")]
        for source in sources:
            label = source["kind"]
            raw = fetcher.fetch(label, source["url"], source["raw_sha256"])
            if raw is not None:
                result["checks"][label] = (fixture_audit(raw) if label == "fixture_pilot"
                                             else bootstrap_audit(raw, 1 if label == "opening_bootstrap" else 2))
            repository = REPOS[1] if label == "fixture_pilot" else REPOS[0]
            metadata = fetcher.fetch(label + "-commit",
                                     f"https://api.github.com/repos/{repository}/commits/{source['commit']}")
            if metadata is not None:
                commit = json.loads(metadata)["commit"]
                result["commit_metadata"][label] = {key: commit.get(key) for key in
                                                     ("author", "committer", "verification", "tree")}
        result["seed_dependency"] = {"source": "data/archive/2024-25/processed",
                                      "exists": (ROOT / "data/archive/2024-25/processed").is_dir(),
                                      "causal_training_lineage": "unverified; no outcome rows inspected"}
    except Exception as exc:
        result["interruption"] = f"{type(exc).__name__}: {exc}"
    finally:
        result.update(requests=fetcher.count, downloaded_bytes=fetcher.bytes,
                      elapsed_seconds=time.monotonic() - fetcher.started, attempts=fetcher.records,
                      output=str(OUTPUT.relative_to(ROOT)))
        if not result["checks"]:
            result["status"] = "blocked"
        (OUTPUT / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps({key: result[key] for key in
                          ("status", "requests", "downloaded_bytes", "elapsed_seconds", "output")}))


def inspect_collector() -> None:
    """Extend the same phase with pinned collector tree/source metadata only."""
    result = json.loads((OUTPUT / "summary.json").read_text())
    fetcher = Fetcher(OUTPUT, resume=True)
    try:
        tree = result["commit_metadata"]["origin_bootstrap_pilot"]["tree"]["sha"]
        raw = fetcher.fetch("collector-tree", f"https://api.github.com/repos/{REPOS[0]}/git/trees/{tree}")
        if raw is not None:
            entries = json.loads(raw)["tree"]
            result["collector_root_paths"] = [entry["path"] for entry in entries]
            for entry in entries:
                if entry["type"] == "blob" and entry["path"].endswith(".py"):
                    fetcher.fetch("collector-" + entry["sha"],
                                  f"https://raw.githubusercontent.com/{REPOS[0]}/acaa50071f959d804abf8ca983adb1363b09619d/{entry['path']}")
    finally:
        result.update(requests=fetcher.count, downloaded_bytes=fetcher.bytes,
                      elapsed_seconds=time.monotonic() - fetcher.started, attempts=fetcher.records)
        (OUTPUT / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps({key: result[key] for key in ("requests", "downloaded_bytes", "elapsed_seconds")}))


def export_retained() -> None:
    """Export small, shareable companions from retained audit fields; no HTTP."""
    result = json.loads((OUTPUT / "summary.json").read_text())
    rows = []
    for source, checks in result["checks"].items():
        for metric, value in checks.items():
            if isinstance(value, int):
                rows.append({"source": source, "metric": metric, "value": value})
        for gw, count in checks.get("window_event_counts", {}).items():
            rows.append({"source": source, "metric": f"gw{gw}_fixtures", "value": count})
    with (TOPIC / "readiness_source_pilot_checks.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("source", "metric", "value"))
        writer.writeheader()
        writer.writerows(rows)
    audit = {key: result[key] for key in ("origin", "status", "requests", "downloaded_bytes",
                                         "elapsed_seconds", "output", "seed_dependency")}
    audit["attempts"] = result["attempts"]
    audit["commit_times"] = {source: {
        "author_date": metadata["author"]["date"],
        "committer_date": metadata["committer"]["date"],
        "verified": metadata["verification"]["verified"],
        "verified_at": metadata["verification"].get("verified_at"),
    } for source, metadata in result["commit_metadata"].items()}
    audit["deadlines"] = {source: checks["deadline"] for source, checks in result["checks"].items()
                          if "deadline" in checks}
    audit["producer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (TOPIC / "readiness_source_pilot_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="one-shot bounded public acquisition")
    parser.add_argument("--resume", action="store_true", help="retain original elapsed/request/byte budgets")
    parser.add_argument("--inspect-collector", action="store_true", help="extend same phase with pinned source code")
    parser.add_argument("--export", action="store_true", help="offline companion export from retained evidence")
    args = parser.parse_args()
    if args.export:
        export_retained()
    elif args.execute:
        if args.inspect_collector:
            inspect_collector()
        else:
            run(resume=args.resume)
    else:
        parser.print_help()
