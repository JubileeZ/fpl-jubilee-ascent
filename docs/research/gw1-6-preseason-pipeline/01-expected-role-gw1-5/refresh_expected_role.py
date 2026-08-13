"""Stage 1 Expected Role rebuild from FFS Team News + FPL Meerkat.

Fetches dual lineup sources over HTTP, applies conflict rules onto the XI Contention
Set scaffold (existing Expected Role Table), merges API availability, applies known
official overlays / transfer club moves, and writes the pipeline CSV.
"""

from __future__ import annotations

import re
import unicodedata
from html import unescape
from pathlib import Path

import httpx
import pandas as pd

FFS_TEAM_NEWS_URL = "https://www.fantasyfootballscout.co.uk/team-news"
MEERKAT_URL = "https://fpl.page/article/fpl-gw1-predicted-lineups-2627"

ROLE_PRIORS = {
    "Nailed Starter": (0.90, 0.05, 0.05, 85, 20),
    "Regular Starter": (0.75, 0.10, 0.15, 80, 20),
    "Rotation": (0.40, 0.25, 0.35, 70, 20),
    "Cameo": (0.10, 0.35, 0.55, 60, 15),
}

FFS_CODE_TO_SHORT = {
    "ars": "ARS", "avl": "AVL", "bou": "BOU", "bre": "BRE", "bha": "BHA",
    "che": "CHE", "cov": "COV", "cry": "CRY", "eve": "EVE", "ful": "FUL",
    "hul": "HUL", "ips": "IPS", "lee": "LEE", "liv": "LIV", "mci": "MCI",
    "mun": "MUN", "new": "NEW", "nfo": "NFO", "sun": "SUN", "tot": "TOT",
}

MEERKAT_CLUB_HEADERS = {
    "ARSENAL": "ARS", "ASTON VILLA": "AVL", "BOURNEMOUTH": "BOU", "BRENTFORD": "BRE",
    "BRIGHTON": "BHA", "CHELSEA": "CHE", "COVENTRY": "COV", "CRYSTAL PALACE": "CRY",
    "EVERTON": "EVE", "FULHAM": "FUL", "HULL": "HUL", "IPSWICH": "IPS", "LEEDS": "LEE",
    "LIVERPOOL": "LIV", "MAN CITY": "MCI", "MAN UNITED": "MUN", "NEWCASTLE": "NEW",
    "NOTTINGHAM FOREST": "NFO", "SUNDERLAND": "SUN", "SPURS": "TOT",
}

# Official availability overlays (club evidence) applied after scrape + API merge.
OFFICIAL_AVAILABILITY = {
    ("Saliba", "ARS"): ("exclude_gw1-5", "Back rehabilitation; out early-season band."),
    ("Rodri", "MCI"): ("exclude_gw1", "Back surgery recovery; miss GW1."),
    ("Rodrigo", "MCI"): ("exclude_gw1", "Back surgery recovery; miss GW1."),
    ("Mac Allister", "LIV"): ("watch", "Post-tournament fitness management."),
    ("Saka", "ARS"): ("watch", "Post-tournament fitness management."),
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("'", "").replace("-", " ").replace(".", " ")
    return re.sub(r"\s+", " ", text).strip()


def _name_parts(text: str) -> tuple[set[str], set[str]]:
    """Significant tokens (len>1) and single-letter initials."""
    parts = _norm(text).split()
    return {p for p in parts if len(p) > 1}, {p for p in parts if len(p) == 1}


def player_matches_source(
    source_name: str,
    web_name: str,
    first_name: str = "",
    second_name: str = "",
) -> bool:
    """True if a lineup-source name refers to this FPL player.

    Identity is web_name + first_name + second_name, so 'Van Dijk' matches
    web_name 'Virgil' and 'Bruno Fernandes' matches 'B.Fernandes' not 'Bruno G.'.
    """
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
    if not src_sig <= identity:
        return False
    identity_letters = {t[0] for t in identity} | web_init | first_init | last_init
    if src_init and not src_init <= identity_letters:
        return False
    if web_init and not web_init <= (identity_letters | {t[0] for t in src_sig}):
        return False
    return True


def name_match(source_name: str, web_name: str) -> bool:
    """web_name-only match. Prefer player_matches_source when first/last known."""
    return player_matches_source(source_name, web_name)


def _player_index(players: pd.DataFrame | None) -> pd.DataFrame:
    if players is None or players.empty:
        return pd.DataFrame()
    return players.drop_duplicates(subset=["id"]).set_index("id")


def _identity(pmap: pd.DataFrame, pid: int, web_name: str) -> tuple[str, str, str]:
    web = str(web_name)
    if pmap.empty or pid not in pmap.index:
        return web, "", ""
    prow = pmap.loc[pid]
    if isinstance(prow, pd.DataFrame):
        prow = prow.iloc[0]
    return web, str(prow.get("first_name") or ""), str(prow.get("second_name") or "")


def scrape_ffs_predicted_xis(client: httpx.Client | None = None) -> dict[str, list[str]]:
    http = client or httpx.Client(timeout=60.0, follow_redirects=True)
    html = http.get(FFS_TEAM_NEWS_URL).text
    blocks = re.split(r'<li class="team-news-item" data-team-code="([^"]+)">', html)
    out: dict[str, list[str]] = {}
    for i in range(1, len(blocks), 2):
        code = blocks[i].lower()
        short = FFS_CODE_TO_SHORT.get(code)
        if short is None:
            continue
        names = [
            n.strip()
            for n in re.findall(
                r'<span class="[^"]*player-name[^"]*"[^>]*>([^<]+)</span>', blocks[i + 1]
            )
        ]
        out[short] = names[:11]
    if len(out) < 20:
        raise RuntimeError(f"FFS scrape incomplete: {len(out)} clubs")
    return out


def scrape_meerkat_nailed(client: httpx.Client | None = None) -> dict[str, list[str]]:
    http = client or httpx.Client(timeout=60.0, follow_redirects=True)
    html = http.get(MEERKAT_URL).text
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>|</h\d>|</div>|</li>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    current: str | None = None
    nailed: dict[str, list[str]] = {v: [] for v in MEERKAT_CLUB_HEADERS.values()}
    header_re = re.compile(
        r"^(ARSENAL|ASTON VILLA|BOURNEMOUTH|BRENTFORD|BRIGHTON|CHELSEA|"
        r"COVENTRY|CRYSTAL PALACE|EVERTON|FULHAM|HULL|IPSWICH|LEEDS|"
        r"LIVERPOOL|MAN CITY|MAN UNITED|NEWCASTLE|NOTTINGHAM FOREST|"
        r"SUNDERLAND|SPURS)\s*$",
        re.I,
    )
    for ln in lines:
        h = header_re.match(ln)
        if h:
            current = MEERKAT_CLUB_HEADERS[h.group(1).upper()]
            continue
        if current is None or "🟢" not in ln:
            continue
        # Only the green-circle starter line (ignore later prose).
        clean = ln.replace("🟢", " ").replace("*", " ")
        # Take text before first sentence-like clause if present
        clean = re.split(r"\.\s", clean, maxsplit=1)[0]
        for part in re.split(r"[,;/]", clean):
            name = part.strip(" -•|\t")
            name = re.sub(r"^\W+", "", name)
            if 2 <= len(name) <= 40 and not any(
                w in name.lower()
                for w in ("looks", "expect", "with ", "should", "anticipate", "i ", "we ")
            ):
                nailed[current].append(name)
        current = None  # only first 🟢 line per club section
    return nailed


def _apply_role_priors(df: pd.DataFrame, idx: int, role: str, reason: str, sources: str) -> None:
    p_start, p_sub, p_dnp, mins_s, mins_u = ROLE_PRIORS[role]
    df.at[idx, "expected_role"] = role
    df.at[idx, "p_start"] = p_start
    df.at[idx, "p_sub_in"] = p_sub
    df.at[idx, "p_dnp"] = p_dnp
    df.at[idx, "mins_if_start"] = mins_s
    df.at[idx, "mins_if_sub"] = mins_u
    df.at[idx, "confidence"] = "high" if role == "Nailed Starter" else "medium"
    df.at[idx, "conflict_rule"] = (
        "unanimous_dual_source" if role == "Nailed Starter" else "source_disagreement_or_single"
    )
    df.at[idx, "draft_eligible"] = role in ("Nailed Starter", "Regular Starter")
    df.at[idx, "reason"] = reason
    df.at[idx, "sources"] = sources
    if role in ("Nailed Starter", "Regular Starter"):
        if str(df.at[idx, "draft_availability"]) == "not_role_eligible":
            df.at[idx, "draft_availability"] = "eligible"
    else:
        df.at[idx, "draft_availability"] = "not_role_eligible"


def _match_source_names(
    names: list[str],
    web_name: str,
    first_name: str = "",
    second_name: str = "",
) -> bool:
    return any(player_matches_source(n, web_name, first_name, second_name) for n in names)


def rebuild_roles_from_sources(
    df: pd.DataFrame,
    ffs_xis: dict[str, list[str]],
    meerkat_nailed: dict[str, list[str]],
    players: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = df.copy()
    pmap = _player_index(players)
    for idx, row in df.iterrows():
        club = str(row["club_short"])
        web, first, last = _identity(pmap, int(row["player_id"]), str(row["web_name"]))
        in_ffs = _match_source_names(ffs_xis.get(club, []), web, first, last)
        in_meerkat = _match_source_names(meerkat_nailed.get(club, []), web, first, last)
        if in_ffs and in_meerkat:
            _apply_role_priors(
                df, idx, "Nailed Starter",
                "Unanimous: FFS predicted XI + Meerkat 🟢 nailed.",
                "FFS Team News; FPL Meerkat",
            )
        elif in_ffs or in_meerkat:
            src = "FFS predicted XI" if in_ffs else "Meerkat 🟢 / predicted"
            _apply_role_priors(
                df, idx, "Regular Starter",
                f"Single-source or non-unanimous starter signal ({src}).",
                "FFS Team News; FPL Meerkat",
            )
        elif str(row["expected_role"]) in ("Nailed Starter", "Regular Starter"):
            # Dropped from both starter signals → rotation risk
            _apply_role_priors(
                df, idx, "Rotation",
                "Previously draft-role but absent from current FFS XI and Meerkat nailed list.",
                "FFS Team News; FPL Meerkat",
            )
    return df


def apply_api_and_official_availability(df: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    pmap = players.set_index("id", drop=False)
    for idx, row in df.iterrows():
        pid = int(row["player_id"])
        if pid not in pmap.index:
            continue
        prow = pmap.loc[pid]
        chance = prow.get("chance_of_playing_next_round")
        news = str(prow.get("news") or "")
        status = str(prow.get("status") or "")
        df.at[idx, "api_status"] = status
        df.at[idx, "api_chance_of_playing_next_round"] = chance
        df.at[idx, "api_news"] = news
        # Soft API hints only when not already officially overlaid
        if str(df.at[idx, "draft_availability"]) in ("eligible", "not_role_eligible", ""):
            if status in ("i", "s") or (pd.notna(chance) and float(chance) == 0):
                df.at[idx, "draft_availability"] = "exclude_gw1"
                df.at[idx, "availability_reason"] = f"API status={status}; chance={chance}; {news}"[:240]
            elif pd.notna(chance) and float(chance) < 75:
                df.at[idx, "draft_availability"] = "watch"
                df.at[idx, "availability_reason"] = f"API chance={chance}; {news}"[:240]

    for (web, club), (avail, reason) in OFFICIAL_AVAILABILITY.items():
        mask = (df["web_name"] == web) & (df["club_short"] == club)
        if not mask.any():
            # fuzzy web_name
            mask = (df["club_short"] == club) & df["web_name"].map(lambda x: name_match(web, str(x)))
        if mask.any():
            df.loc[mask, "draft_availability"] = avail
            df.loc[mask, "availability_reason"] = reason
            df.loc[mask, "availability_sources"] = "Official club / research overlay"
    return df


def apply_transfer_club_moves(df: pd.DataFrame) -> pd.DataFrame:
    """Hard club corrections for confirmed moves still wrong in scaffold."""
    df = df.copy()
    moves = [
        ("Bruno G.", "ARS", "Arsenal", "Confirmed £75m transfer to Arsenal."),
        ("Welbeck", "CHE", "Chelsea", "Confirmed £5m depth move to Chelsea."),
        ("Lacroix", "CHE", "Chelsea", "Confirmed transfer to Chelsea."),
        ("Trafford", "LEE", "Leeds United", "Confirmed transfer to Leeds."),
        ("Tzolakis", "HUL", "Hull City", "Confirmed transfer to Hull."),
        ("Tonali", "TOT", "Tottenham Hotspur", "Confirmed transfer to Spurs."),
        ("Rushworth", "COV", "Coventry City", "Confirmed transfer to Coventry; FFS XI starter."),
    ]
    for web, short, club, reason in moves:
        mask = df["web_name"] == web
        if not mask.any():
            mask = df["web_name"].map(lambda x: name_match(web, str(x)))
        if mask.any():
            df.loc[mask, "club_short"] = short
            df.loc[mask, "club"] = club
            df.loc[mask, "reason"] = reason
    # Welbeck depth
    welbeck = df["web_name"] == "Welbeck"
    if welbeck.any():
        _apply_role_priors(
            df, df.index[welbeck][0], "Rotation",
            "Confirmed £5m transfer to Chelsea as forward depth.",
            "FFS transfers; FFS Team News",
        )
    return df


def inject_missing_ffs_starters(
    df: pd.DataFrame,
    ffs_xis: dict[str, list[str]],
    meerkat_nailed: dict[str, list[str]],
    players: pd.DataFrame,
    clubs: pd.DataFrame,
) -> pd.DataFrame:
    """Append FFS predicted-XI players absent from the contention scaffold."""
    df = df.copy()
    club_name = dict(zip(clubs["short_name"], clubs["name"], strict=False))
    club_id_by_short = dict(zip(clubs["short_name"], clubs["id"], strict=False))
    pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
    existing_ids = set(df["player_id"].astype(int))
    pmap = _player_index(players)
    added = 0

    def _frame_hits(src_name: str, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        mask = frame.apply(
            lambda r: player_matches_source(
                src_name,
                str(r["web_name"]),
                str(r.get("first_name") or ""),
                str(r.get("second_name") or ""),
            ),
            axis=1,
        )
        return frame.loc[mask]

    for short, names in ffs_xis.items():
        club_players = players[players["club_id"] == club_id_by_short.get(short, -1)]
        for src_name in names:
            already = False
            for row in df.itertuples():
                if str(row.club_short) != short:
                    continue
                web, first, last = _identity(pmap, int(row.player_id), str(row.web_name))
                if player_matches_source(src_name, web, first, last):
                    already = True
                    break
            if already:
                continue
            # Match within club first, then league-wide identity (not first-name-only)
            hit = _frame_hits(src_name, club_players)
            if hit.empty:
                hit = _frame_hits(src_name, players)
            if hit.empty:
                continue
            prow = hit.iloc[0]
            pid = int(prow["id"])
            if pid in existing_ids:
                # Player exists under another club row — move club
                mask = df["player_id"] == pid
                df.loc[mask, "club_short"] = short
                df.loc[mask, "club"] = club_name.get(short, short)
                continue
            in_meerkat = _match_source_names(
                meerkat_nailed.get(short, []),
                str(prow["web_name"]),
                str(prow.get("first_name") or ""),
                str(prow.get("second_name") or ""),
            )
            role = "Nailed Starter" if in_meerkat else "Regular Starter"
            p_start, p_sub, p_dnp, mins_s, mins_u = ROLE_PRIORS[role]
            new_row = {col: "" for col in df.columns}
            new_row.update({
                "club": club_name.get(short, short),
                "club_short": short,
                "player_id": pid,
                "web_name": prow["web_name"],
                "position": pos_map.get(int(prow["position_id"]), "MID"),
                "expected_role": role,
                "p_start": p_start,
                "p_sub_in": p_sub,
                "p_dnp": p_dnp,
                "mins_if_start": mins_s,
                "mins_if_sub": mins_u,
                "confidence": "medium",
                "conflict_rule": "ffs_xi_inject",
                "draft_eligible": True,
                "reason": f"Injected from FFS predicted XI ({src_name}).",
                "sources": "FFS Team News",
                "draft_availability": "eligible",
                "api_club_id": int(prow["club_id"]),
                "api_club_short": short,
            })
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            existing_ids.add(pid)
            added += 1
    if added:
        print(f"  injected {added} missing FFS XI players into contention set")
    return df


def refresh_expected_roles(
    input_csv: str = "data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv",
    output_csvs: list[str] | None = None,
    players_parquet: str = "data/processed/players.parquet",
    clubs_parquet: str = "data/processed/clubs.parquet",
    client: httpx.Client | None = None,
) -> pd.DataFrame:
    if output_csvs is None:
        output_csvs = [
            "data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv",
        ]

    df = pd.read_csv(input_csv)
    players = pd.read_parquet(players_parquet)
    clubs = pd.read_parquet(clubs_parquet)

    print(f"Scraping FFS Team News: {FFS_TEAM_NEWS_URL}")
    ffs_xis = scrape_ffs_predicted_xis(client)
    print(f"  clubs={len(ffs_xis)} predicted XI rows={sum(len(v) for v in ffs_xis.values())}")

    print(f"Scraping FPL Meerkat: {MEERKAT_URL}")
    meerkat = scrape_meerkat_nailed(client)
    print(f"  nailed markers={sum(len(v) for v in meerkat.values())}")

    df = apply_transfer_club_moves(df)
    df = inject_missing_ffs_starters(df, ffs_xis, meerkat, players, clubs)
    df = rebuild_roles_from_sources(df, ffs_xis, meerkat, players=players)
    df = apply_api_and_official_availability(df, players)

    for web in ("Rushworth", "Kinsky", "Trafford", "Tzolakis"):
        mask = df["web_name"].map(lambda x, w=web: name_match(w, str(x)))
        if mask.any() and str(df.loc[mask, "expected_role"].iloc[0]) in (
            "Nailed Starter", "Regular Starter",
        ):
            if str(df.loc[mask, "draft_availability"].iloc[0]) == "not_role_eligible":
                df.loc[mask, "draft_availability"] = "eligible"

    for out_path in output_csvs:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(p, index=False)
        print(f"Updated {p} ({len(df)} rows)")

    md_path = Path("docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md")
    if md_path.exists():
        sync_expected_role_markdown(df, md_path)
        print(f"Synced 20-club tables in {md_path}")
    return df


CLUB_MD_ORDER = [
    "ARS", "AVL", "BOU", "BRE", "BHA", "CHE", "COV", "CRY", "EVE", "FUL",
    "HUL", "IPS", "LEE", "LIV", "MCI", "MUN", "NEW", "NFO", "TOT", "SUN",
]
_ROLE_SORT = {"Nailed Starter": 0, "Regular Starter": 1, "Rotation": 2, "Cameo": 3}
_POS_SORT = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}


def _avail_counts(df: pd.DataFrame) -> dict[str, int]:
    vc = df["draft_availability"].astype(str).value_counts()
    return {k: int(vc.get(k, 0)) for k in ("eligible", "not_role_eligible", "exclude_gw1", "watch", "exclude_gw1-5")}


def render_club_tables(df: pd.DataFrame) -> str:
    """Render Findings §2 20-club markdown tables from the role CSV."""
    n = len(df)
    chunks = [
        "### 2. 20-Club Player Role & Draft Availability Breakdown",
        "",
        (
            f"Complete roster of all {n} players across the 20 Premier League clubs "
            "in the XI Contention Set, showing assigned fit-role, baseline starter "
            "probability ($p_{\\text{start}}$), Draft Availability overlay, and source signals."
        ),
        "",
    ]
    for i, short in enumerate(CLUB_MD_ORDER, start=1):
        club_df = df[df["club_short"] == short].copy()
        if club_df.empty:
            continue
        club_df["_rs"] = club_df["expected_role"].map(lambda r: _ROLE_SORT.get(str(r), 9))
        club_df["_ps"] = club_df["position"].map(lambda p: _POS_SORT.get(str(p), 9))
        club_df = club_df.sort_values(["_ps", "_rs", "web_name"])
        club_name = str(club_df["club"].iloc[0])
        roles = club_df["expected_role"].value_counts()
        n_nail = int(roles.get("Nailed Starter", 0))
        n_reg = int(roles.get("Regular Starter", 0))
        n_rot = int(roles.get("Rotation", 0))
        n_cam = int(roles.get("Cameo", 0))
        n_draft = n_nail + n_reg
        chunks.append(f"#### {i}. {club_name} (`{short}`) — {len(club_df)} players")
        chunks.append(
            f"- **Summary**: Nailed: {n_nail} · Regular: {n_reg} · Rotation: {n_rot} · "
            f"Cameo: {n_cam} | Draft Eligible: {n_draft}"
        )
        chunks.append("")
        chunks.append(
            "| Player | Pos | Role | $p_{\\text{start}}$ | Draft Availability | Evidence / Source Signal |"
        )
        chunks.append("|---|---|---|---|---|---|")
        for row in club_df.itertuples():
            reason = str(getattr(row, "reason", "") or "").replace("|", "/")
            chunks.append(
                f"| **{row.web_name}** | {row.position} | {row.expected_role} | "
                f"{float(row.p_start):.2f} | `{row.draft_availability}` | {reason} |"
            )
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def sync_expected_role_markdown(df: pd.DataFrame, md_path: Path) -> None:
    """Patch High-Level Summary counts and replace §2 club tables."""
    text = md_path.read_text(encoding="utf-8")
    n = len(df)
    roles = df["expected_role"].value_counts()
    n_nail = int(roles.get("Nailed Starter", 0))
    n_reg = int(roles.get("Regular Starter", 0))
    n_rot = int(roles.get("Rotation", 0))
    n_cam = int(roles.get("Cameo", 0))
    n_draft = n_nail + n_reg
    av = _avail_counts(df)
    summary = (
        f"- Contention set: **{n}** rows. Roles: Nailed {n_nail} · Regular {n_reg} · "
        f"Rotation {n_rot} · Cameo {n_cam}.\n"
        f"- Draft Eligible: **{n_draft}** players (Nailed {n_nail} + Regular {n_reg}).\n"
        f"- Availability: eligible {av['eligible']} · not_role_eligible {av['not_role_eligible']} · "
        f"exclude_gw1 {av['exclude_gw1']} · watch {av['watch']} · exclude_gw1-5 {av['exclude_gw1-5']}."
    )
    text = re.sub(
        r"- Contention set:.*\n- Draft Eligible:.*\n- Availability:.*",
        summary,
        text,
        count=1,
    )
    tables = render_club_tables(df)
    text = re.sub(
        r"### 2\. 20-Club Player Role & Draft Availability Breakdown\n.*?(?=\n## Decision\n)",
        tables + "\n",
        text,
        count=1,
        flags=re.S,
    )
    md_path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    refresh_expected_roles()
