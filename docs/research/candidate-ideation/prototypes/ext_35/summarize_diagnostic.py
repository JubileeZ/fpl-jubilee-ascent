"""Summarize completed EXT-35 retained diagnostic artifacts without rerunning models."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from backtesting.decision_regret import LineupDecision, PlayerOutcome, score_lineup
from backtesting.metrics import _formation_xi_stats, select_squad_and_formation_xi
from backtesting.process_points import aggregate_process_points, blended_points
from backtesting.walkforward import LEDGER_COMPONENTS, _build_actual_components

KEYS = ['player_id', 'gameweek_id', 'fixture_id']
STATES = ['p_dnp', 'p_start', 'p_sub_in', 'xmins_if_start', 'xmins_if_sub_in', 'p_60_if_start', 'p_60_if_sub_in', 'projected_minutes', 'xp_minutes']
SUMMARY_SOURCES = [Path(__file__).resolve(), *(ROOT / path for path in ['backtesting/metrics.py', 'backtesting/decision_regret.py', 'backtesting/process_points.py', 'backtesting/walkforward.py', 'backtesting/season_rules.py', 'models/scoring_matrix.py'])]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_hash(frame: pd.DataFrame, columns: list[str]) -> str:
    ordered = frame.sort_values(KEYS, kind='stable').reset_index(drop=True)
    if ordered.duplicated(KEYS).any():
        raise ValueError('duplicate fixture keys')
    payload = np.asarray(ordered[KEYS], dtype=np.int64).tobytes() + np.asarray(ordered[columns], dtype=np.float64).tobytes()
    return hashlib.sha256(json.dumps([*KEYS, *columns]).encode() + payload).hexdigest()


def checked(record: dict, root: Path) -> pd.DataFrame:
    path = Path(record['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'artifact outside diagnostic directory: {path}')
    if digest(path) != record['sha256']:
        raise ValueError(f'artifact hash mismatch: {path}')
    frame = pd.read_parquet(path)
    if len(frame) != record['rows']:
        raise ValueError(f'artifact row count mismatch: {path}')
    return frame


def decision(frame: pd.DataFrame) -> LineupDecision:
    starters, bench = select_squad_and_formation_xi(frame)
    if len(starters) != 11 or len(bench) != 4:
        raise ValueError('selection did not produce 11 starters and 4 bench players')
    ids = tuple(int(x) for x in starters.player_id)
    return LineupDecision(ids, tuple(int(x) for x in bench.player_id), ids[0], ids[1])


def score(frame: pd.DataFrame, lineup: LineupDecision, target: str) -> float:
    outcomes = {int(r.player_id): PlayerOutcome(int(r.player_id), int(r.position_id), float(getattr(r, target)), float(r.actual_minutes)) for r in frame.itertuples()}
    return score_lineup(lineup, outcomes).points


def run(manifest_path: Path, output: Path) -> None:
    summary_sources = {str(path.relative_to(ROOT)): digest(path) for path in SUMMARY_SOURCES}
    root = manifest_path.resolve().parent
    manifest = json.loads(manifest_path.read_text())
    variants, champion = manifest['variants'], manifest['champion']
    gws = list(range(1, 39))
    if manifest['status'] != 'complete' or manifest['role'] != 'dev' or manifest['gw_range'] != [1, 38] or manifest['completed_gameweeks'] != gws or len(variants) != 4 or manifest.get('promotion_authority') is not False or manifest.get('evidence_kind') != 'four_cell_projection_diagnostic':
        raise ValueError('manifest is incomplete or not the full development diagnostic')
    for name, expected in manifest['source_sha256'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or digest(path) != expected:
            raise ValueError(f'diagnostic source hash mismatch: {name}')
    cells = {(c['gameweek_id'], c['model'], c['regime']): c for c in manifest['cells']}
    expected_keys = {(gw, model, regime) for gw in gws for model in [champion, *variants] for regime in ['native', 'oracle']}
    if len(cells) != len(manifest['cells']) or set(cells) != expected_keys:
        raise ValueError('manifest cell coverage mismatch')
    for gw in gws:
        for model in [champion, *variants]:
            if cells[gw, model, 'native']['rate_hash'] != cells[gw, model, 'oracle']['rate_hash']:
                raise ValueError(f'GW{gw} {model}: native/oracle rate tensors differ')
    actual = checked(manifest['actual_outcomes'], root)
    output = output.resolve()
    if output.exists() or output == root or not output.is_relative_to(root):
        raise ValueError('output must be a new directory inside diagnostic directory')
    player_rows, fixture_rows, gw_rows = [], [], []
    previous: dict[tuple[str, str], set[int]] = {}
    unverified: dict[str, str] = {}
    for gw in gws:
        gw_dir = root / f'gw{gw:02d}'
        feature_path = gw_dir / 'features.parquet'
        unverified[str(feature_path.relative_to(root))] = digest(feature_path)
        features = pd.read_parquet(feature_path)
        meta = features[['player_id', 'position_id', 'now_cost', 'club_id']].drop_duplicates()
        if meta.duplicated('player_id').any() or meta.isna().any().any():
            raise ValueError(f'GW{gw}: inconsistent player metadata')
        actual_gw = _build_actual_components(actual.loc[actual.gameweek_id.eq(gw)].copy(), features)
        totals = actual_gw.groupby(['player_id', 'gameweek_id'], as_index=False)[['total_points', 'minutes'] + [f'actual_{c}' for c in LEDGER_COMPONENTS if f'actual_{c}' in actual_gw]].sum().rename(columns={'total_points': 'actual_points', 'minutes': 'actual_minutes'})
        totals = totals.merge(aggregate_process_points(actual_gw), on=['player_id', 'gameweek_id'], how='left')
        data: dict[tuple[str, str], tuple[pd.DataFrame, pd.DataFrame, LineupDecision, dict]] = {}
        regrets: dict[tuple[str, str, str], float] = {}
        for model in [champion, *variants]:
            for regime in ['native', 'oracle']:
                cell = cells[gw, model, regime]
                proj = checked(cell['projections'], root)
                rates = checked(cell['prepared_rates'], root)
                checked(cell['prepared_events'], root)
                rate_columns = [c for c in rates if c not in KEYS]
                if frame_hash(proj, STATES) != cell['state_hash'] or frame_hash(rates, rate_columns) != cell['rate_hash']:
                    raise ValueError(f'GW{gw} {model}/{regime}: tensor hash mismatch')
                group = proj.groupby(['player_id', 'gameweek_id'], as_index=False)[['projected_points', 'projected_minutes', *LEDGER_COMPONENTS]].sum()
                group = group.merge(meta, on='player_id', validate='one_to_one').merge(totals, on=['player_id', 'gameweek_id'], how='left', validate='one_to_one')
                outcome_cols = [c for c in group if c.startswith('actual_') or c == 'process_points']
                group[outcome_cols] = group[outcome_cols].fillna(0.0)
                group['blended_points'] = blended_points(group.actual_points, group.process_points)
                lineup = decision(group)
                data[model, regime] = (proj, group, lineup, cell)
                squad = set(lineup.starters + lineup.bench)
                prior = previous.get((model, regime))
                churn = float(15 - len(squad & prior)) if prior is not None else np.nan
                previous[model, regime] = squad
                group['model'], group['state_condition'] = model, regime
                group['selected'] = group.player_id.isin(squad)
                group['starter'] = group.player_id.isin(lineup.starters)
                group['bench_order'] = group.player_id.map({pid: i + 1 for i, pid in enumerate(lineup.bench)}).fillna(0).astype(int)
                group['captain'] = group.player_id.eq(lineup.captain)
                group['vice_captain'] = group.player_id.eq(lineup.vice_captain)
                group['churn'] = churn
                for target in ['actual_points', 'process_points', 'blended_points']:
                    regrets[model, regime, target] = _formation_xi_stats(group, target_column=target)[1]
                player_rows.append(group)
        for variant in variants:
            diagnostic_path = gw_dir / variant / 'rate_diagnostics.parquet'
            unverified[str(diagnostic_path.relative_to(root))] = digest(diagnostic_path)
            diag = pd.read_parquet(diagnostic_path)
            if diag.empty and 'player_id' not in diag:
                diag = diag.rename(columns={'index': 'player_id'})
            if diag.duplicated('player_id').any():
                raise ValueError('duplicate rate diagnostic player')
            for regime in ['native', 'oracle']:
                cp, cg, cl, cc = data[champion, regime]
                vp, vg, vl, vc = data[variant, regime]
                if cc['state_hash'] != vc['state_hash']:
                    raise ValueError('paired state tensors differ')
                pair = cp.merge(vp, on=KEYS, suffixes=('_champ', '_candidate'), validate='one_to_one')
                if len(pair) != len(cp) or len(pair) != len(vp):
                    raise ValueError('paired projection populations differ')
                pair = pair.merge(diag, on='player_id', how='left', validate='many_to_one')
                pair['variant'], pair['state_condition'] = variant, regime
                pair['rate_hash_champ'], pair['rate_hash_candidate'], pair['state_hash'] = cc['rate_hash'], vc['rate_hash'], cc['state_hash']
                for component in ['xp_goals', 'xp_bonus']:
                    pair[f'{component}_delta'] = pair[f'{component}_candidate'] - pair[f'{component}_champ']
                pair['selected_champ'] = pair.player_id.isin(cl.starters + cl.bench)
                pair['selected_candidate'] = pair.player_id.isin(vl.starters + vl.bench)
                fixture_rows.append(pair)
                cs, vs = set(cl.starters + cl.bench), set(vl.starters + vl.bench)
                row: dict[str, object] = {'gameweek_id': gw, 'variant': variant, 'state_condition': regime, 'selection_overlap': len(cs & vs) / len(cs | vs), 'churn_delta': float(vg.churn.iloc[0] - cg.churn.iloc[0])}
                projected = cg[['player_id', 'projected_points']].merge(vg[['player_id', 'projected_points']], on='player_id', suffixes=('_champ', '_candidate'), validate='one_to_one')
                fixed = projected.loc[projected.player_id.isin(cl.starters)]
                cap = projected.loc[projected.player_id.eq(cl.captain)]
                row['fixed_selection_projected_delta'] = float((fixed.projected_points_candidate - fixed.projected_points_champ).sum() + (cap.projected_points_candidate - cap.projected_points_champ).sum())
                for target in ['actual_points', 'process_points', 'blended_points']:
                    cscore, vscore = score(cg, cl, target), score(vg, vl, target)
                    row[f'{target}_champ_score'] = cscore
                    row[f'{target}_candidate_score'] = vscore
                    row[f'{target}_score_delta'] = vscore - cscore
                    row[f'{target}_fixed_selection_delta'] = score(vg, cl, target) - cscore
                    row[f'{target}_champ_formation_regret'] = regrets[champion, regime, target]
                    row[f'{target}_candidate_formation_regret'] = regrets[variant, regime, target]
                row['score_delta'] = row['blended_points_score_delta']
                gw_rows.append(row)
        print(f'Summarized GW{gw:02d}', flush=True)
    weekly = pd.DataFrame(gw_rows)
    native = weekly.loc[weekly.state_condition.eq('native'), ['gameweek_id', 'variant', 'score_delta']].rename(columns={'score_delta': 'native_delta'})
    oracle = weekly.loc[weekly.state_condition.eq('oracle'), ['gameweek_id', 'variant', 'score_delta']].rename(columns={'score_delta': 'oracle_delta'})
    interaction = native.merge(oracle, on=['gameweek_id', 'variant'], validate='one_to_one')
    interaction['oracle_minus_native'] = interaction.oracle_delta - interaction.native_delta
    if {str(path.relative_to(ROOT)): digest(path) for path in SUMMARY_SOURCES} != summary_sources:
        raise ValueError('summary source changed during computation')
    output.mkdir(parents=True)
    pd.concat(player_rows, ignore_index=True).to_parquet(output / 'player_gameweeks.parquet', index=False)
    pd.concat(fixture_rows, ignore_index=True).to_parquet(output / 'paired_fixtures.parquet', index=False)
    weekly.to_csv(output / 'paired_gameweeks.csv', index=False)
    interaction.to_csv(output / 'interactions.csv', index=False)
    if {str(path.relative_to(ROOT)): digest(path) for path in SUMMARY_SOURCES} != summary_sources:
        raise ValueError('summary source changed during output')
    (output / 'summary_manifest.json').write_text(json.dumps({'source_manifest_sha256': digest(manifest_path), 'summary_source_sha256': summary_sources, 'unverified_at_capture_sha256': unverified, 'score_definition': 'diagnostic reoptimized weekly lineup with autosubs and captain; blended = 50% actual + 50% process; not rolling net or promotion evidence', 'fixed_selection_definition': 'Champion selection evaluated on common outcomes under candidate and Champion; necessarily zero for unchanged outcomes. Projected delta sums player forecast differences over Champion starters plus captain, without predicted autosubs.', 'formation_regret_definition': 'canonical XI regret without captain', 'selection_overlap': 'squad Jaccard', 'churn_delta': 'candidate minus Champion top-15 churn; GW1 undefined', 'outputs_sha256': {p.name: digest(p) for p in output.iterdir()}}, indent=2) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.manifest, args.output)


if __name__ == '__main__':
    main()
