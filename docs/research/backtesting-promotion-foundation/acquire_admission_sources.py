from __future__ import annotations

import csv
import argparse
import hashlib
import json
import lzma
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
TOPIC = Path(__file__).resolve().parent
OUTPUT = ROOT / 'data/reports/replay-admission/v1'
LIMIT = 10 * 1024 * 1024
SEASONS = ('2023-24', '2024-25', '2025-26')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unpack(data: bytes) -> bytes:
    decoder = lzma.LZMADecompressor()
    result = decoder.decompress(data, max_length=16 * 1024 * 1024 + 1)
    if len(result) > 16 * 1024 * 1024 or not decoder.eof:
        raise ValueError('decompressed size limit exceeded or incomplete stream')
    return result


def save_immutable(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('existing raw file differs')
        return
    path.write_bytes(data)


def log_attempt(record: dict[str, str], run_id: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    entry = {'run_id': run_id, **record}
    with (OUTPUT / 'retrieval-attempts.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, sort_keys=True) + '\n')


def report(rows: list[dict[str, str]]) -> None:
    openings = [row for row in rows if row['kind'] == 'opening_bootstrap']
    pilots = [row for row in rows if row['kind'] in {'origin_bootstrap_pilot', 'fixture_pilot'}]
    gaps = [row for row in rows if row['kind'] == 'origin_bootstrap_and_fixtures']
    def summary(items: list[dict[str, str]]) -> str:
        return '\n'.join(f"- {r['season']} {r['origin']} {r['kind']}: {r['status']}; bytes {r['bytes'] or 'unknown'}; {r['detail']}" for r in items) or '- No entries.'
    tree = TOPIC / 'acquisition_tree_inspection.csv'
    if tree.exists():
        with tree.open(newline='', encoding='utf-8-sig') as handle:
            tree_lines = '\n'.join(f"- {r['calendar_years']}: {r['path_count']} paths, commit {r['tree_commit']}; {r['inspection_method']}" for r in csv.DictReader(handle))
    else:
        tree_lines = '- No tree inspection companion.'
    (TOPIC / 'acquisition-report.md').write_text(f'''# Historical admission acquisition

**Updated**: 2026-10-29T20:00:00+07:00  
**Data stamp**: acquisition_manifest.csv (5 retrieved rows)  
**Season**: Multi-season  
**Status**: Active  
**Purpose**: Document historical admission source acquisition and raw file quarantine status for 2023-24, 2024-25, and 2025-26.  
**Scope**: Evaluates raw file manifests and tree inspections only; quarantined from forecast inputs.  
**Artifact**: [acquisition_manifest.csv](acquisition_manifest.csv)  

## Sources

- **Primary**: [Randdalf/fplcache](https://github.com/Randdalf/fplcache) — commits adb4450b, 75750671, 0bb12a87
- **Repository data**: `docs/research/backtesting-promotion-foundation/ownership_snapshot_provenance.csv`

## Method

Scope: 2023-24, 2024-25 and 2025-26. Opening cap 10 MiB; pilot cap 2 MiB. Manifest is current attempt status; append-only `data/reports/replay-admission/v1/retrieval-attempts.jsonl` retains attempt history. Earlier successes reconstructed from manifest; initial sandbox failures lack individual timestamps. A start without completion indicates an interrupted or killed attempt.

## Findings

### Opening latest status: {sum(r['status'] == 'retrieved_unadmitted' for r in openings)}/{len(openings)} retrieved.
{summary(openings)}

### Pilot latest status: {sum(r['status'] == 'retrieved_unadmitted' for r in pilots)}/{len(pilots)} retrieved.
{summary(pilots)}

### Coverage summary
All {len(gaps)} complete-origin labels remain pending. Opening deadlines are planned deadlines; a pilot bootstrap may record its own next deadline. Git times corroborate chronology, not exact capture or independent publication. Fixture source lineage, schedule completeness and announcement timing unverified. Raw files contain mixed facts and possible outcomes; quarantine, no forecast input. No freshness, eligibility, admission, numerical accuracy or replay feasibility established. No model, solver or outcome comparison.

### Manual tree inspection
Calendar-year paths, not verified origin coverage:
{tree_lines}

## Decision

Quarantine all retrieved raw files. No forecast input until causal admission and provenance verification are complete. Counts and rows derive from `acquisition_manifest.csv` columns `kind`, `status`, `season`, `origin`, `bytes`, `detail`; tree counts derive from `acquisition_tree_inspection.csv` columns `calendar_years`, `path_count`, `tree_commit`, `inspection_method`.

## Risks and unknowns

- Git commit timestamps corroborate publication chronology only; exact API capture timing unverified.
- Fixture announcement timing and schedule completeness unverified.
''', encoding='utf-8')


def main() -> None:
    run_id = datetime.now(timezone.utc).isoformat()
    with (TOPIC / 'ownership_snapshot_provenance.csv').open(newline='', encoding='utf-8') as handle:
        sources = {row['season']: row for row in csv.DictReader(handle) if row['season'] in SEASONS}
    manifest = TOPIC / 'acquisition_manifest.csv'
    if manifest.exists():
        with manifest.open(newline='', encoding='utf-8-sig') as handle:
            prior = list(csv.DictReader(handle))
    else:
        prior = []
    rows = []
    total = 0
    for season in SEASONS:
        source = sources[season]
        url = f"https://raw.githubusercontent.com/Randdalf/fplcache/{source['source_commit']}/{source['source_path']}"
        record = dict(season=season, origin='gw01', kind='opening_bootstrap', status='failed', url=url, commit=source['source_commit'], blob=source['git_blob_sha'], recorded_commit_utc=source['recorded_committer_utc'], capture_utc='unknown', publication_uncertainty='git committer time corroborates publication only; exact capture and independent publication unverified', retrieval_utc='', raw_sha256='', decompressed_sha256='', bytes='', parser='xz then JSON', path='', parent_refs='ownership_snapshot_provenance.csv', detail='')
        attempt_id = str(uuid.uuid4())
        log_attempt({**record, 'attempt_id': attempt_id, 'event': 'start', 'timestamp_utc': datetime.now(timezone.utc).isoformat()}, run_id)
        try:
            with urlopen(url, timeout=30) as response:
                payload = response.read(LIMIT - total + 1)
            total += len(payload)
            if total > LIMIT:
                raise ValueError('aggregate transfer limit exceeded')
            if digest(payload) != source['compressed_sha256']:
                raise ValueError('pinned hash mismatch')
            decoded = unpack(payload)
            parsed = json.loads(decoded)
            if not isinstance(parsed, dict) or not isinstance(parsed.get('events'), list):
                raise ValueError('unexpected bootstrap structure')
            target = OUTPUT / season / 'opening' / 'bootstrap.json.xz'
            save_immutable(target, payload)
            record.update(status='retrieved_unadmitted', retrieval_utc=datetime.now(timezone.utc).isoformat(), raw_sha256=digest(payload), decompressed_sha256=digest(decoded), bytes=str(len(payload)), path=target.relative_to(ROOT).as_posix(), detail='mixed bootstrap payload; planned opening deadlines only; no per-origin observation or fixture schedule')
        except Exception as exc:
            record.update(retrieval_utc=datetime.now(timezone.utc).isoformat(), detail=f'{type(exc).__name__}: {exc}')
        except BaseException as exc:
            log_attempt({**record, 'attempt_id': attempt_id, 'event': 'interrupted', 'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'detail': type(exc).__name__}, run_id)
            raise
        log_attempt({**record, 'attempt_id': attempt_id, 'event': 'finish', 'timestamp_utc': datetime.now(timezone.utc).isoformat()}, run_id)
        rows.append(record)
        for gw in range(1, 39):
            rows.append(dict(season=season, origin=f'gw{gw:02}', kind='origin_bootstrap_and_fixtures', status='missing', url='', commit='', blob='', recorded_commit_utc='', capture_utc='unknown', publication_uncertainty='unassessed', retrieval_utc='', raw_sha256='', decompressed_sha256='', bytes='', parser='', path='', parent_refs='opening_bootstrap' if gw == 1 else '', detail='per-origin observed deadline, bootstrap and contemporaneous fixtures not located; opening planned deadline is not an observed deadline'))
    rows.extend(row for row in prior if row['kind'] in {'origin_bootstrap_pilot', 'fixture_pilot'})
    with manifest.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report(rows)


def pilot() -> None:
    run_id = datetime.now(timezone.utc).isoformat()
    sources = [
        ('origin_bootstrap_pilot', 'https://raw.githubusercontent.com/Randdalf/fplcache/acaa50071f959d804abf8ca983adb1363b09619d/cache/2025/8/22/1251.json.xz', 'acaa50071f959d804abf8ca983adb1363b09619d', 'f3673c3bccbb98245bffd548560d3cd7d15f4d39', '2025-08-22T12:51:15Z', 'bootstrap.json.xz'),
        ('fixture_pilot', 'https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/e930bb766ff82d6dff6a47f40eefd4e65bba29ef/data/2025-26/fixtures.csv', 'e930bb766ff82d6dff6a47f40eefd4e65bba29ef', '04f6fbeafc2bafedcc89c3eaf873d2071516f33d', '2025-08-20T07:59:03Z', 'fixtures.csv'),
    ]
    manifest = TOPIC / 'acquisition_manifest.csv'
    with manifest.open(newline='', encoding='utf-8-sig') as handle:
        rows = [row for row in csv.DictReader(handle) if row['kind'] not in {'origin_bootstrap_pilot', 'fixture_pilot'}]
    total = 0
    for kind, url, commit, blob, commit_time, filename in sources:
        record = dict.fromkeys(rows[0], '')
        record.update(season='2025-26', origin='gw02', kind=kind, status='failed', url=url, commit=commit, blob=blob, recorded_commit_utc=commit_time, capture_utc='unknown', publication_uncertainty='recorded Git time only; exact capture and independent publication unverified', parser='xz then JSON' if filename.endswith('.xz') else 'CSV', parent_refs='historical GitHub path history and contents metadata')
        attempt_id = str(uuid.uuid4())
        log_attempt({**record, 'attempt_id': attempt_id, 'event': 'start', 'timestamp_utc': datetime.now(timezone.utc).isoformat()}, run_id)
        try:
            with urlopen(url, timeout=30) as response:
                raw = response.read(2 * 1024 * 1024 - total + 1)
            total += len(raw)
            if total > 2 * 1024 * 1024:
                raise ValueError('pilot aggregate transfer limit exceeded')
            git_blob = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
            if git_blob != blob:
                raise ValueError('Git blob mismatch')
            decoded = unpack(raw) if filename.endswith('.xz') else raw
            if filename.endswith('.xz'):
                events = json.loads(decoded)['events']
                selected = [event for event in events if event.get('is_next')]
                detail = 'observed is_next events: ' + json.dumps([{'id': event['id'], 'deadline_time': event['deadline_time']} for event in selected])
            else:
                header = next(csv.reader(decoded.decode('utf-8-sig').splitlines()))
                detail = 'CSV header: ' + ','.join(header) + '; fixture timing/announcement provenance unverified'
            target = OUTPUT / '2025-26' / 'origins' / 'gw02' / 'raw-mixed' / filename
            save_immutable(target, raw)
            record.update(status='retrieved_unadmitted', raw_sha256=digest(raw), decompressed_sha256=digest(decoded), bytes=str(len(raw)), path=target.relative_to(ROOT).as_posix(), detail=detail)
        except Exception as exc:
            record['detail'] = f'{type(exc).__name__}: {exc}'
        except BaseException as exc:
            log_attempt({**record, 'attempt_id': attempt_id, 'event': 'interrupted', 'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'detail': type(exc).__name__}, run_id)
            raise
        record['retrieval_utc'] = datetime.now(timezone.utc).isoformat()
        log_attempt({**record, 'attempt_id': attempt_id, 'event': 'finish', 'timestamp_utc': datetime.now(timezone.utc).isoformat()}, run_id)
        rows.append(record)
    with manifest.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot', action='store_true')
    parser.add_argument('--openings', action='store_true')
    args = parser.parse_args()
    if args.pilot and args.openings:
        parser.error('choose one acquisition mode')
    pilot() if args.pilot else main()
