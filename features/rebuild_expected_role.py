"""Automated Expected Role Rebuild Engine (ADR 0016 / Transfer Reconciliation).

Reconciles all players from data/processed/players.parquet into features/expected_roles.csv.
Fetches dual lineup sources (predicted XIs and nailed markers) when online, preserves existing
curated roles, and assigns position/price-tier priors to new transfers and mid-season signings.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from html import unescape
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from features.expected_role_prior import (
    DEFAULT_EXPECTED_ROLE_TABLE,
    DEFAULT_LINEUP_SIGNALS,
    LIVE_SEASON,
    OUT_OF_CONTENTION,
    ROLE_PRIORS,
    write_lineup_signals,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FFS_TEAM_NEWS_URL = "https://www.fantasyfootballscout.co.uk/team-news"
MEERKAT_URL = "https://fpl.page/article/fpl-gw1-predicted-lineups-2627"

FFS_CODE_TO_SHORT: dict[str, str] = {
    "ars": "ARS", "avl": "AVL", "bou": "BOU", "bre": "BRE", "bha": "BHA",
    "che": "CHE", "cov": "COV", "cry": "CRY", "eve": "EVE", "ful": "FUL",
    "hul": "HUL", "ips": "IPS", "lee": "LEE", "liv": "LIV", "mci": "MCI",
    "mun": "MUN", "new": "NEW", "nfo": "NFO", "sun": "SUN", "tot": "TOT",
}

MEERKAT_CLUB_HEADERS: dict[str, str] = {
    "ARSENAL": "ARS", "ASTON VILLA": "AVL", "BOURNEMOUTH": "BOU", "BRENTFORD": "BRE",
    "BRIGHTON": "BHA", "CHELSEA": "CHE", "COVENTRY": "COV", "CRYSTAL PALACE": "CRY",
    "EVERTON": "EVE", "FULHAM": "FUL", "HULL": "HUL", "IPSWICH": "IPS", "LEEDS": "LEE",
    "LIVERPOOL": "LIV", "MAN CITY": "MCI", "MAN UNITED": "MUN", "NEWCASTLE": "NEW",
    "NOTTINGHAM FOREST": "NFO", "SUNDERLAND": "SUN", "SPURS": "TOT",
}

POS_MAP: dict[int, str] = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("'", "").replace("-", " ").replace(".", " ")
    return re.sub(r"\s+", " ", text).strip()


def _name_parts(text: str) -> tuple[set[str], set[str]]:
    parts = _norm(text).split()
    return {p for p in parts if len(p) > 1}, {p for p in parts if len(p) == 1}


def _surname_last_token(second_name: str) -> str:
    last_parts = [p for p in _norm(second_name).split() if len(p) > 1]
    return last_parts[-1] if last_parts else ""


def player_matches_source(
    source_name: str,
    web_name: str,
    first_name: str = "",
    second_name: str = "",
) -> bool:
    src_sig, src_init = _name_parts(source_name)
    if not src_sig:
        return False
    web_sig, web_init = _name_parts(web_name)
    first_sig, first_init = _name_parts(first_name)
    last_sig, last_init = _name_parts(second_name)
    identity = web_sig | first_sig | last_sig
    if not identity:
        return False
    if _norm(source_name) == _norm(web_name):
        return True
    if len(src_sig) == 1 and not src_init:
        token = next(iter(src_sig))
        surname_last = _surname_last_token(second_name)
        return token in web_sig or (bool(surname_last) and token == surname_last)
    if not src_sig <= identity:
        return False
    identity_letters = {t[0] for t in identity} | web_init | first_init | last_init
    if src_init and not src_init <= identity_letters:
        return False
    if web_init and not web_init <= (identity_letters | {t[0] for t in src_sig}):
        return False
    return True


def scrape_ffs_predicted_xis(client: httpx.Client | None = None) -> dict[str, list[str]]:
    """Scrape Predicted XIs from Fantasy Football Scout Team News."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FPL-Jubilee/1.0)"}
    try:
        if client:
            resp = client.get(FFS_TEAM_NEWS_URL, headers=headers, timeout=8.0)
        else:
            with httpx.Client(timeout=8.0) as local_client:
                resp = local_client.get(FFS_TEAM_NEWS_URL, headers=headers)
        if resp.status_code != 200:
            logger.warning(f"FFS Team News returned HTTP {resp.status_code}")
            return {}
        html = resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch FFS Team News: {e}")
        return {}

    sections = re.split(r'<div[^>]*class="[^"]*team-news-club[^"]*"[^>]*data-club="([^"]+)"', html)
    xis: dict[str, list[str]] = {}
    for i in range(1, len(sections), 2):
        raw_club = sections[i].strip().lower()
        club_short = FFS_CODE_TO_SHORT.get(raw_club)
        if not club_short:
            continue
        section_html = sections[i + 1] if i + 1 < len(sections) else ""
        xi_match = re.search(r'<div[^>]*class="[^"]*predicted-lineup[^"]*"[^>]*>(.*?)</div>', section_html, re.S)
        if not xi_match:
            continue
        names = re.findall(r'<span[^>]*class="[^"]*player-name[^"]*"[^>]*>(.*?)</span>', xi_match.group(1))
        cleaned = [unescape(re.sub(r"<[^>]+>", "", name)).strip() for name in names if name.strip()]
        if cleaned:
            xis[club_short] = cleaned
    return xis


def scrape_meerkat_nailed(client: httpx.Client | None = None) -> dict[str, list[str]]:
    """Scrape nailed markers from FPL Meerkat."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FPL-Jubilee/1.0)"}
    try:
        if client:
            resp = client.get(MEERKAT_URL, headers=headers, timeout=8.0)
        else:
            with httpx.Client(timeout=8.0) as local_client:
                resp = local_client.get(MEERKAT_URL, headers=headers)
        if resp.status_code != 200:
            logger.warning(f"FPL Meerkat returned HTTP {resp.status_code}")
            return {}
        html = resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch FPL Meerkat: {e}")
        return {}

    nailed: dict[str, list[str]] = {}
    blocks = re.split(r"<h[23][^>]*>(.*?)</h[23]>", html)
    current_club: str | None = None
    for token in blocks:
        clean_header = re.sub(r"<[^>]+>", "", token).strip().upper()
        if clean_header in MEERKAT_CLUB_HEADERS:
            current_club = MEERKAT_CLUB_HEADERS[clean_header]
            if current_club not in nailed:
                nailed[current_club] = []
            continue
        if current_club:
            green_names = re.findall(r"🟢\s*([^<\n,]+)", token)
            for gname in green_names:
                gclean = unescape(gname).strip()
                if gclean and gclean not in nailed[current_club]:
                    nailed[current_club].append(gclean)
    return nailed


def _infer_newcomer_role(
    row: pd.Series,
    in_xi: bool,
    is_nailed: bool,
) -> tuple[str, float, float, float, float, float, str, str]:
    """Infer Expected Role for a player based on lineup signals and price tier heuristics."""
    status = str(row.get("status", "a"))
    chance = row.get("chance_of_playing_next_round")
    chance_val = float(chance) if pd.notna(chance) and chance is not None else 100.0
    pos_id = int(row.get("position_id", 3))
    now_cost = float(row.get("now_cost", 50)) / 10.0

    if status in ("u", "n") or chance_val <= 0.0:
        p_start, p_sub, p_dnp, mins_s, mins_u = OUT_OF_CONTENTION
        return "Out of Contention", p_start, p_sub, p_dnp, mins_s, mins_u, "api_unavailable", "API status unavailable or 0% chance"

    if in_xi and is_nailed:
        p_start, p_sub, p_dnp, mins_s, mins_u = ROLE_PRIORS["Nailed Starter"]
        return "Nailed Starter", p_start, p_sub, p_dnp, mins_s, mins_u, "unanimous_dual_source", "Dual-source: FFS predicted XI + Meerkat nailed"

    if in_xi or is_nailed:
        p_start, p_sub, p_dnp, mins_s, mins_u = ROLE_PRIORS["Regular Starter"]
        return "Regular Starter", p_start, p_sub, p_dnp, mins_s, mins_u, "source_disagreement_or_single", "Single-source lineup signal starter"

    # Price tier heuristics for newly added transfers
    if pos_id == 1:  # Goalkeeper
        if now_cost >= 5.0:
            role = "Regular Starter"
        elif now_cost <= 4.0:
            role = "Out of Contention"
        else:
            role = "Cameo"
    elif pos_id == 2:  # Defender
        if now_cost >= 5.5:
            role = "Regular Starter"
        elif now_cost >= 4.5:
            role = "Rotation"
        elif now_cost <= 4.0:
            role = "Cameo"
        else:
            role = "Cameo"
    else:  # Midfielder / Forward
        if now_cost >= 6.0:
            role = "Regular Starter"
        elif now_cost >= 5.0:
            role = "Rotation"
        else:
            role = "Cameo"

    p_start, p_sub, p_dnp, mins_s, mins_u = ROLE_PRIORS[role]
    reason = f"Auto-inferred role for transfer/signing (£{now_cost:.1f}m {POS_MAP.get(pos_id, 'MID')})"
    return role, p_start, p_sub, p_dnp, mins_s, mins_u, "transfer_price_heuristic", reason


def rebuild_expected_roles(
    processed_dir: Path | None = None,
    output_path: Path | None = None,
    existing_table_path: Path | None = None,
    season: str = LIVE_SEASON,
    client: httpx.Client | None = None,
) -> pd.DataFrame:
    """Reconcile and rebuild the full Expected Role table for all players."""
    proc_dir = processed_dir or (PROJECT_ROOT / "data" / "processed")
    out_path = output_path or DEFAULT_EXPECTED_ROLE_TABLE

    players_file = proc_dir / "players.parquet"
    clubs_file = proc_dir / "clubs.parquet"
    if not players_file.exists() or not clubs_file.exists():
        raise FileNotFoundError(f"Missing processed player or club data at {proc_dir}")

    df_players = pd.read_parquet(players_file)
    df_clubs = pd.read_parquet(clubs_file)
    club_map = dict(zip(df_clubs["id"], df_clubs["name"]))
    club_short_map = dict(zip(df_clubs["id"], df_clubs["short_name"]))

    # Load existing roles table if present
    existing_map: dict[int, dict[str, Any]] = {}
    if existing_table_path is not None:
        read_path = existing_table_path if existing_table_path.exists() else None
    elif out_path.exists():
        read_path = out_path
    elif proc_dir == PROJECT_ROOT / "data" / "processed":
        legacy_path = PROJECT_ROOT / "features" / "expected-role-gw1-5.csv"
        read_path = legacy_path if legacy_path.exists() else None
    else:
        read_path = None

    if read_path and read_path.exists():
        try:
            df_existing = pd.read_csv(read_path)
            if "player_id" in df_existing.columns:
                for _, erow in df_existing.iterrows():
                    pid = int(erow["player_id"])
                    existing_map[pid] = erow.to_dict()
        except Exception as e:
            logger.warning(f"Could not read existing role table from {read_path}: {e}")

    # Fetch live lineup signals if available
    ffs_xis = scrape_ffs_predicted_xis(client)
    meerkat = scrape_meerkat_nailed(client)
    if ffs_xis or meerkat:
        write_lineup_signals(DEFAULT_LINEUP_SIGNALS, season, ffs_xis, meerkat)

    rows: list[dict[str, Any]] = []
    for _, prow in df_players.iterrows():
        pid = int(prow["id"])
        cid = int(prow["club_id"]) if pd.notna(prow.get("club_id")) else 0
        club_name = club_map.get(cid, "Unknown")
        club_short = club_short_map.get(cid, "UNK")
        web_name = str(prow.get("web_name", f"Player {pid}"))
        first_name = str(prow.get("first_name", ""))
        second_name = str(prow.get("second_name", ""))
        pos_id = int(prow.get("position_id", 3))
        pos_code = POS_MAP.get(pos_id, "MID")

        status = str(prow.get("status", "a"))
        raw_chance = prow.get("chance_of_playing_next_round")
        chance_val = float(raw_chance) if pd.notna(raw_chance) and raw_chance is not None else None
        news = str(prow.get("news", "") or "")
        news_added = str(prow.get("news_added", "") or "")

        # Check lineup signals
        club_xi = ffs_xis.get(club_short, [])
        club_nailed = meerkat.get(club_short, [])
        in_xi = any(player_matches_source(src, web_name, first_name, second_name) for src in club_xi)
        is_nailed = any(player_matches_source(src, web_name, first_name, second_name) for src in club_nailed)

        existing = existing_map.get(pid)
        if existing and existing.get("conflict_rule") not in ("transfer_price_heuristic", "api_unavailable"):
            role = str(existing.get("expected_role", "Rotation"))
            p_start = float(existing.get("p_start", ROLE_PRIORS[role][0]))
            p_sub = float(existing.get("p_sub_in", ROLE_PRIORS[role][1]))
            p_dnp = float(existing.get("p_dnp", ROLE_PRIORS[role][2]))
            mins_s = float(existing.get("mins_if_start", ROLE_PRIORS[role][3]))
            mins_u = float(existing.get("mins_if_sub", ROLE_PRIORS[role][4]))
            override = bool(existing.get("override", False))
            confidence = str(existing.get("confidence", "medium"))
            conflict_rule = str(existing.get("conflict_rule", "curated_preseason"))
            reason = str(existing.get("reason", "Curated baseline expected role"))
            sources = str(existing.get("sources", "Preseason squad review"))
            source_refs = str(existing.get("source_refs", "") or "")
            avail_override = str(existing.get("availability_override", "") or "")
        else:
            role, p_start, p_sub, p_dnp, mins_s, mins_u, conflict_rule, reason = _infer_newcomer_role(
                prow, in_xi, is_nailed
            )
            override = False
            confidence = "medium" if in_xi or is_nailed else "low"
            sources = "FFS Team News; FPL Meerkat; FPL API" if in_xi or is_nailed else "FPL API Transfer Ingest"
            source_refs = ""
            avail_override = ""

        # Determine draft_availability overlay
        if status in ("u", "n") or (chance_val is not None and chance_val <= 0.0):
            draft_avail = "exclude_gw1"
            avail_status = "exclude_gw1"
        elif chance_val is not None and chance_val < 100.0:
            draft_avail = "watch"
            avail_status = "watch"
        elif role in ("Nailed Starter", "Regular Starter"):
            draft_avail = "eligible"
            avail_status = "available"
        else:
            draft_avail = "not_role_eligible"
            avail_status = "not_role_eligible"

        row_dict: dict[str, Any] = {
            "season": season,
            "club": club_name,
            "club_short": club_short,
            "player_id": pid,
            "web_name": web_name,
            "position": pos_code,
            "expected_role": role,
            "p_start": p_start,
            "p_sub_in": p_sub,
            "p_dnp": p_dnp,
            "mins_if_start": mins_s,
            "mins_if_sub": mins_u,
            "override": override,
            "confidence": confidence,
            "conflict_rule": conflict_rule,
            "draft_eligible": role in ("Nailed Starter", "Regular Starter"),
            "reason": reason,
            "sources": sources,
            "source_refs": source_refs,
            "api_status": status,
            "api_chance_of_playing_next_round": chance_val,
            "api_chance_of_playing_this_round": None,
            "api_news": news,
            "api_news_added": news_added,
            "api_club_id": cid,
            "api_club_short": club_short,
            "registration_status": "registered",
            "registration_reason": "",
            "availability_status": avail_status,
            "availability_override": avail_override,
            "availability_confidence": "high",
            "draft_availability": draft_avail,
            "availability_reason": news if news else ("Fit and available for selection" if draft_avail == "eligible" else "Role not draft-eligible"),
            "availability_sources": sources,
            "availability_source_refs": "",
        }
        rows.append(row_dict)

    df_out = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(out_path, index=False)
    logger.info(f"Rebuilt Expected Role Table at {out_path} with {len(df_out)} players (100% coverage)")
    return df_out
