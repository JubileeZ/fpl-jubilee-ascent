# FPL-Jubilee-Ascent - Data Dictionary

This document maps fields fetched from the raw FPL API endpoints to the clean flat-file schema (Parquet/CSV) used by the modeling and solver engine.

---

## 1. Clubs (`clubs.parquet`)
*   **Source:** `/bootstrap-static/` (`teams` list)
*   **Fields Retained:**
    *   `id` (`int`): Club ID (e.g. 1 = Arsenal).
    *   `name` (`str`): e.g. "Arsenal".
    *   `short_name` (`str`): e.g. "ARS".
    *   `strength` (`int`): FPL overall rating (1-5).
    *   `strength_overall_home`, `strength_overall_away`, `strength_attack_home`, `strength_attack_away`, `strength_defence_home`, `strength_defence_away` (`int`): Club Strength Vector. Live 2026/27 overall = Official Fixture Difficulty at the *focal* venue (`_home`/`_away` = your home/away, not the opponent's ground). Attack/defence often 0.
*   **Discarded:** `code`, `draw`, `loss`, `win`, `played`, `points`, `position` (current standing), `team_division`, `link_url`, `pulse_id`, `unavailable`, `form`.

---

## 2. Positions (Static mapping in code)
*   **Source:** `/bootstrap-static/` (`element_types` list)
*   **Static mapping:**
    *   `1`: "GKP" (Goalkeeper)
    *   `2`: "DEF" (Defender)
    *   `3`: "MID" (Midfielder)
    *   `4`: "FWD" (Forward)

---

## 3. Gameweeks (`gameweeks.parquet`)
*   **Source:** `/bootstrap-static/` (`events` list)
*   **Fields Retained:**
    *   `id` (`int`): 1 to 38.
    *   `name` (`str`): e.g. "Gameweek 1".
    *   `deadline_time` (`datetime`): Deadline lockout timestamp (UTC).
    *   `finished` (`bool`): Whether the GW has concluded.
    *   `is_current` (`bool`): Active gameweek flag.
    *   `is_next` (`bool`): Next planning target flag.
*   **Discarded:** `release_time`, `average_entry_score`, `data_checked`, `highest_scoring_entry`, `deadline_time_epoch`, `deadline_time_game_offset`, `highest_score`, `is_previous`, `cup_leagues_created`, `h2h_ko_matches_created`, `can_enter`, `can_manage`, `released`, `ranked_count`, `overrides`, `chip_plays`, `most_selected`, `most_transferred_in`, `top_element`, `top_element_info`, `transfers_made`, `most_captained`, `most_vice_captained`.

---

## 4. Players (`players.parquet`)
*   **Source:** `/bootstrap-static/` (`elements` list)
*   **Fields Retained:**
    *   `id` (`int`): Unique player ID.
    *   `first_name` (`str`), `second_name` (`str`), `web_name` (`str`).
    *   `club_id` (`int`): Reference to Club ID (maps to `team` in raw API).
    *   `position_id` (`int`): 1=GKP, 2=DEF, 3=MID, 4=FWD (maps to `element_type` in raw API).
    *   `now_cost` (`int`): Current FPL cost in £0.1m increments (e.g. 100 = £10.0m).
    *   `status` (`str`): 'a' (available), 'i' (injured), 'd' (doubtful), etc.
    *   `chance_of_playing_next_round` (`int`, nullable), `chance_of_playing_this_round` (`int`, nullable).
    *   `news` (`str`), `news_added` (`datetime`, nullable).
    *   `selected_by_percent` (`float`): Ownership %.
    *   `corners_and_indirect_freekicks_order` (`int`, nullable), `direct_freekicks_order` (`int`, nullable), `penalties_order` (`int`, nullable).
    *   **Season Totals (Metrics for reference/baselines):** `total_points`, `minutes`, `goals_scored`, `assists`, `clean_sheets`, `goals_conceded`, `own_goals`, `penalties_saved`, `penalties_missed`, `yellow_cards`, `red_cards`, `saves`, `bonus`, `bps`, `influence`, `creativity`, `threat`, `ict_index`, `starts`, `expected_goals`, `expected_assists`, `expected_goal_involvements`, `expected_goals_conceded`.
*   **Discarded:** `code`, `team_code`, `squad_number`, `photo`, `removed`, `birth_date`, `region`, `team_join_date`, `has_temporary_code`, `opta_code`, `can_transact`, `can_select`, `cost_change_event`, `cost_change_event_fall`, `cost_change_start`, `cost_change_start_fall`, `price_change_percent`, `dreamteam_count`, `in_dreamteam`, `ep_this`, `ep_next`, `form`, `value_form`, `value_season`, `points_per_game`, `scout_risks`, `scout_news_link`.

---

## 5. Fixtures (`fixtures.parquet`)
*   **Source:** `/fixtures/`
*   **Fields Retained:**
    *   `id` (`int`): Unique fixture ID.
    *   `gameweek_id` (`int`): Reference to Gameweek ID (maps to `event` in raw API).
    *   `kickoff_time` (`datetime`).
    *   `home_club_id` (`int`): Reference to home Club (maps to `team_h`).
    *   `away_club_id` (`int`): Reference to away Club (maps to `team_a`).
    *   `finished` (`bool`), `started` (`bool`).
    *   `team_h_score` (`int`, nullable), `team_a_score` (`int`, nullable).
    *   `team_h_difficulty` (`int`), `team_a_difficulty` (`int`): Official Fixture Difficulty for the home/away club. Production models and FDR report derive Modified FDR (−0.25 home / +0.25 away); these columns stay the API ticks.
    *   `raw_stats` (`json`): Raw `'stats'` array containing goals/assists/bps details.
*   **Discarded:** `code`, `finished_provisional`, `provisional_start_time`, `minutes`, `pulse_id`.

---

## 6. Point-in-time Player Snapshots (`player_snapshots.parquet`)
*   **Source:** archived pre-deadline `/bootstrap-static/` snapshots.
*   **Required keys:** `player_id` or `id`, and `snapshot_gameweek_id`.
*   **Purpose:** historical position, club, price, and availability metadata as known at the simulated deadline. Backtests use the latest snapshot at or before the target gameweek.

---

## 7. Player Gameweek Performances (`player_performances.parquet`)
*   **Source:** `/element-summary/{player_id}/` (`history` list) & `/event/{gw_id}/live/`
*   **Fields Retained:**
    *   `player_id` (`int`): Reference to Player.
    *   `fixture_id` (`int`): Reference to Fixture.
    *   `gameweek_id` (`int`): Reference to Gameweek.
    *   `opponent_club_id` (`int`): Opposing Club ID.
    *   `was_home` (`bool`).
    *   `kickoff_time` (`datetime`).
    *   `team_h_score` (`int`, nullable), `team_a_score` (`int`, nullable).
    *   `price` (`int`): Player price at fixture time (maps to `value` in FPL API).
    *   `selected` (`int`): Ownership count.
    *   `transfers_balance` (`int`), `transfers_in` (`int`), `transfers_out` (`int`).
    *   **Performance metrics:** `minutes`, `total_points`, `goals_scored`, `assists`, `clean_sheets`, `goals_conceded`, `own_goals`, `penalties_saved`, `penalties_missed`, `yellow_cards`, `red_cards`, `saves`, `bonus`, `bps`, `influence`, `creativity`, `threat`, `ict_index`, `starts`, `expected_goals`, `expected_assists`, `expected_goal_involvements`, `expected_goals_conceded`, `defensive_contribution`.
*   **Discarded:** `modified`.

---

## 8. User Squad Picks (`user_picks.parquet`)
*   **Source:** `/my-team/{entry_id}/` (`picks` list) & `/entry/{entry_id}/event/{gw_id}/picks/`
*   **Fields Retained:**
    *   `entry_id` (`int`): Manager entry ID.
    *   `gameweek_id` (`int`).
    *   `player_id` (`int`).
    *   `lineup_index` (`int`): Squad slot 1 to 15 (maps to `position` in picks raw response).
    *   `multiplier` (`int`): 0=bench, 1=starter, 2=captain, 3=triple captain.
    *   `is_captain` (`bool`), `is_vice_captain` (`bool`).
    *   `purchase_price` (`int`), `selling_price` (`int`).
*   **Discarded:** None.

---

## 9. User State (`user_state.parquet`)
*   **Source:** `/my-team/{entry_id}/`
*   **Fields Retained:**
    *   `entry_id` (`int`).
    *   `bank` (`int`): Budget in bank.
    *   `value` (`int`): Total team value.
    *   `free_transfers` (`int`): Available free transfers.
    *   `active_chip` (`str`, nullable).
*   **Discarded:** `cost`, `status`, `limit`, `made`.

---

## 10. User Chips (`user_chips.parquet`)
*   **Source:** `/my-team/{entry_id}/` (`chips` list).
*   **Fields Retained:**
    *   `chip` (`str`): Normalized key `wc` / `bb` / `fh` / `tc`.
    *   `name` (`str`): FPL chip name (`wildcard`, `bboost`, `freehit`, `3xc`).
    *   `status` (`str`): `available`, `active`, or `played`.
    *   `start_event` (`int`, nullable), `stop_event` (`int`, nullable).
    *   `number` (`int`, nullable): FPL chip instance (1 = Chip Set 1, 2 = Chip Set 2).
    *   `chip_set` (`int`): 1 (GW1–19) or 2 (GW20–38).
*   **Discarded:** chip UI copy, `chip_type`.

---

## 11. Price History (`price_history.parquet`)
*   **Source:** Processed `players.parquet` after each `refresh_data` run.
*   **Fields Retained:**
    *   `player_id` (`int`): Reference to Player.
    *   `now_cost` (`int`): FPL cost in £0.1m increments at capture time.
    *   `web_name` (`str`, nullable), `club_id` (`int`, nullable).
    *   `gameweek_id` (`int`): Current or next Gameweek at capture.
    *   `captured_at` (`datetime`): UTC snapshot timestamp.
*   **Append behavior:** Each refresh adds a snapshot; `commands.price_report` compares latest, previous, and first snapshots.

---

## 12. Availability Snapshot Package
*   **Root:** `data/availability-snapshots/<season>/GW<gameweek>/<capture>-<hash>/`.
*   **Capture rule:** Stores only changed, complete packages captured in the 48
    hours before the recorded Gameweek deadline.
*   **Tables:** `players.parquet`, `clubs.parquet`, and `fixtures.parquet`.
    These preserve prediction-critical mutable FPL metadata as known at capture
    time.
*   **Metadata:** `metadata.json` records `schema_version`, `season`,
    `target_gameweek`, UTC `deadline`, UTC `captured_at`, `content_hash`,
    `snapshot_id`, and source endpoint versions.
*   **Validation:** Readers use only packages with matching season, Gameweek,
    deadline, schema version, tables, and content hash.

---

## 13. Projection Contract
Model output is long format with:
* `player_id`: Player identifier.
* `fixture_id`: Fixture identifier; `-1` denotes a blank gameweek row.
* `gameweek_id`: Target gameweek.
* `projected_points`: Fixture-level expected FPL points.
* `projected_minutes`: Fixture-level expected minutes.
* Participation-state projections additionally expose `p_dnp`, `p_start`,
  `p_sub_in`, `xmins_if_start`, and `xmins_if_sub_in`.
* Hybrid component projections expose the exact scoring ledger:
  minutes, goals, assists, clean sheets, goals conceded, saves, penalties
  saved/missed, own goals, yellow/red cards, Defcon, and bonus.

Solver exports aggregate `projected_points` and `projected_minutes` by
`player_id` and `gameweek_id`, preserving double-gameweek totals.
