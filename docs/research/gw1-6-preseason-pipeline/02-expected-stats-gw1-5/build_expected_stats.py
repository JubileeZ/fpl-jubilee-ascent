"""Expected Stats GW1–5 builder — Prior-Season Seed + Career Individual Rate.

Rules (ADR-0014):
- Resolve archive history via FPL `code` (ADR 0004), never raw cross-season player_id.
- Prior-Season Seed = latest archive season (2025/26) with minutes >= 450.
- No seed: Career Individual Rate (xG/xA/Defcon/saves) from last-season research
  package, else most recent older FPL history_past >= 450.
- No seed GC/CS: Destination Team Concede Rate (2025/26 PL GC/game;
  promoted Clubs inherit PL league-average, not Championship GC).
- Research Position Baseline only if no career package and no older FPL.
- Rate sheet covers XI Contention Set (Nailed / Regular / Rotation / Cameo).
- New Draft player with no seed: add CAREER_INDIVIDUAL_RATES package, then
  refresh_downstream.py (Stage 2 fail-closes if Nailed/Regular still on fallback).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

import pandas as pd

from features.builder import MIN_PRIOR_MINUTES

MIN_USABLE_MINUTES = MIN_PRIOR_MINUTES  # 450 — Prior-Season Seed floor
LATEST_ARCHIVE_SEASON = "2025/26"
XI_CONTENTION_ROLES = ("Nailed Starter", "Regular Starter", "Rotation", "Cameo")

POSITION_BASELINES = {
    "GKP": {"xg": 0.00, "xa": 0.00, "defcon": 0.00, "saves": 2.78, "gc": 1.38},
    "DEF": {"xg": 0.06, "xa": 0.06, "defcon": 4.25, "saves": 0.00, "gc": 1.39},
    "MID": {"xg": 0.15, "xa": 0.15, "defcon": 3.10, "saves": 0.00, "gc": 1.37},
    "FWD": {"xg": 0.41, "xa": 0.13, "defcon": 1.50, "saves": 0.00, "gc": 1.41},
}

# External packages: xG/xA/saves/gc from research.
# Defcon: use researched CBIT/CBITR when defcon_cbit=True (includes best-guess partial sources).
# If defcon_cbit=False → position baseline Defcon.
EXTERNAL_RESEARCH_RATES: dict[int, dict] = {
    25: {"xg": 0.770, "xa": 0.240, "saves": 0.00, "gc": 1.10, "defcon": 1.22, "defcon_cbit": False,
         "note": "External 3-season: Sporting CP / Arsenal (xG/xA); Defcon baseline (no CBIT)"},
    217: {"xg": 0.340, "xa": 0.350, "saves": 0.00, "gc": 1.20, "defcon": 2.28, "defcon_cbit": False,
          "note": "External 3-season: Leverkusen / Liverpool (xG/xA); Defcon baseline"},
    357: {"xg": 0.200, "xa": 0.250, "saves": 0.00, "gc": 1.25, "defcon": 2.81, "defcon_cbit": False,
          "note": "External 3-season: Leverkusen / Liverpool DEF; Defcon baseline"},
    211: {"xg": 0.240, "xa": 0.200, "saves": 0.00, "gc": 1.30, "defcon": 2.55, "defcon_cbit": False,
          "note": "External 3-season: Villarreal / Palace; Defcon baseline"},
    514: {"xg": 0.370, "xa": 0.170, "saves": 0.00, "gc": 1.30, "defcon": 2.40, "defcon_cbit": False,
          "note": "External 3-season: Bayern / Spurs; Defcon baseline"},
    335: {"xg": 0.090, "xa": 0.140, "saves": 0.00, "gc": 1.35, "defcon": 5.71, "defcon_cbit": False,
          "note": "External 3-season: Hoffenheim / Leeds; Defcon baseline"},
    336: {"xg": 0.330, "xa": 0.110, "saves": 0.00, "gc": 1.35, "defcon": 1.40, "defcon_cbit": False,
          "note": "External 3-season: Milan / Leeds; Defcon baseline"},
    331: {"xg": 0.040, "xa": 0.050, "saves": 0.00, "gc": 1.30, "defcon": 6.15, "defcon_cbit": False,
          "note": "External 3-season: Lille / Leeds; Defcon baseline"},
    445: {"xg": 0.110, "xa": 0.020, "saves": 0.00, "gc": 1.15, "defcon": 8.78, "defcon_cbit": False,
          "note": "External 3-season: Milan / Newcastle; Defcon baseline"},
    412: {"xg": 0.000, "xa": 0.000, "saves": 3.47, "gc": 1.15, "defcon": 0.00, "defcon_cbit": True,
          "note": "External 3-season: Antwerp / Man Utd GKP saves"},
    533: {"xg": 0.090, "xa": 0.080, "saves": 0.00, "gc": 1.25, "defcon": 8.42, "defcon_cbit": False,
          "note": "External 3-season: PSG / Leverkusen / Sunderland; Defcon baseline"},
    535: {"xg": 0.060, "xa": 0.020, "saves": 0.00, "gc": 1.25, "defcon": 9.82, "defcon_cbit": False,
          "note": "External 3-season: Getafe / Sunderland; Defcon baseline"},
    536: {"xg": 0.040, "xa": 0.020, "saves": 0.00, "gc": 1.25, "defcon": 7.24, "defcon_cbit": False,
          "note": "External 3-season: Atletico / Sunderland; Defcon baseline"},
    542: {"xg": 0.140, "xa": 0.200, "saves": 0.00, "gc": 1.30, "defcon": 5.31, "defcon_cbit": False,
          "note": "External 3-season: Rennes / Roma / Sunderland; Defcon baseline"},
    545: {"xg": 0.070, "xa": 0.080, "saves": 0.00, "gc": 1.30, "defcon": 6.25, "defcon_cbit": False,
          "note": "External 3-season: Union SG / Sunderland; Defcon baseline"},
    529: {"xg": 0.000, "xa": 0.000, "saves": 3.27, "gc": 1.31, "defcon": 0.00, "defcon_cbit": True,
          "note": "External 3-season: NEC / Sunderland GKP saves"},
    504: {"xg": 0.185, "xa": 0.035, "saves": 0.00, "gc": 1.46, "defcon": 12.45, "defcon_cbit": True,
          "note": "External Westerlo/HSV xG/xA; best-guess CBIT 12.45/90 from HSV Opta (blocks may be shots-only)"},
    172: {"xg": 0.000, "xa": 0.000, "saves": 2.25, "gc": 1.07, "defcon": 0.00, "defcon_cbit": True,
          "note": "External: Coventry GKP saves"},
    # Draft fallback packages (research 2026-08-02)
    173: {"xg": 0.091, "xa": 0.043, "saves": 0.00, "gc": 1.204, "defcon": 9.102, "defcon_cbit": True,
          "note": "External CHA 2023-26: Bobby Thomas Coventry CB; CBIT Defcon; FBref+FotMob; mins~10017"},
    193: {"xg": 0.570, "xa": 0.110, "saves": 0.00, "gc": 1.238, "defcon": 5.279, "defcon_cbit": True,
          "note": "External CHA 2023-26: Haji Wright; best-guess CBITR 5.28/90 from 23/24-24/25 FBref"},
    274: {"xg": 0.000, "xa": 0.000, "saves": 2.333, "gc": 1.010, "defcon": 0.00, "defcon_cbit": True,
          "note": "External SPFL 2023-26: Jack Butland Rangers proxy (no Hull mins yet); mins~9180"},
    290: {"xg": 0.081, "xa": 0.062, "saves": 0.00, "gc": 1.294, "defcon": 9.096, "defcon_cbit": True,
          "note": "External CHA 2023-26: Regan Slater Hull; CBITR Defcon; FBref+FotMob; mins~8905"},
    292: {"xg": 0.043, "xa": 0.031, "saves": 0.00, "gc": 1.28, "defcon": 8.32, "defcon_cbit": True,
          "note": "External 2023-26: Abdülkadir Ömür; best-guess CBITR 8.32/90 from Hull CHA FBref"},
    310: {"xg": 0.024, "xa": 0.032, "saves": 0.00, "gc": 1.47, "defcon": 13.57, "defcon_cbit": True,
          "note": "External 2023-26: Azor Matusiwa; best-guess CBITR 13.57/90 from Ligue 1 FBref"},
    316: {"xg": 0.236, "xa": 0.028, "saves": 0.00, "gc": 1.38, "defcon": 2.78, "defcon_cbit": True,
          "note": "External 2024-26: Emersonn; best-guess partial def actions 2.78/90 (Tkl+Int+Rec)"},
    # CBIT/CBITR Defcon upgrades (research 2026-08-02)
    182: {"xg": 0.035, "xa": 0.015, "saves": 0.00, "gc": 1.30, "defcon": 8.03, "defcon_cbit": True,
          "note": "External YB/Frankfurt xG/xA; best-guess CBIT 8.03/90 from UCL scout sample"},
    175: {"xg": 0.035, "xa": 0.150, "saves": 0.00, "gc": 1.00, "defcon": 7.00, "defcon_cbit": True,
          "note": "External Coventry DEF; FBref CBIT Defcon 7.00/90 (2023-25)"},
    188: {"xg": 0.185, "xa": 0.205, "saves": 0.00, "gc": 1.35, "defcon": 11.05, "defcon_cbit": True,
          "note": "External Coventry MID; FBref CBITR Defcon 11.05/90 (2023-25)"},
    186: {"xg": 0.255, "xa": 0.155, "saves": 0.00, "gc": 1.35, "defcon": 6.52, "defcon_cbit": True,
          "note": "External Coventry MID; FBref CBITR 6.52/90 Coventry slice only"},
    184: {"xg": 0.045, "xa": 0.205, "saves": 0.00, "gc": 1.25, "defcon": 10.80, "defcon_cbit": True,
          "note": "External Swansea/Coventry; FBref CBITR Defcon 10.80/90"},
    247: {"xg": 0.105, "xa": 0.175, "saves": 0.00, "gc": 1.40, "defcon": 12.03, "defcon_cbit": True,
          "note": "External Middlesbrough; FBref CBITR Defcon 12.03/90 (Hackney)"},
    278: {"xg": 0.075, "xa": 0.055, "saves": 0.00, "gc": 1.16, "defcon": 8.14, "defcon_cbit": True,
          "note": "External Preston; FBref CBIT Defcon 8.14/90 (Andrew Hughes)"},
    280: {"xg": 0.030, "xa": 0.125, "saves": 0.00, "gc": 1.24, "defcon": 7.36, "defcon_cbit": True,
          "note": "External Hull DEF; FBref CBIT Defcon 7.36/90 (Coyle)"},
    286: {"xg": 0.195, "xa": 0.215, "saves": 0.00, "gc": 1.50, "defcon": 9.97, "defcon_cbit": True,
          "note": "External Farense/Hull; FBref CBITR Defcon 9.97/90 (Belloumi)"},
    562: {"xg": 0.455, "xa": 0.175, "saves": 0.00, "gc": 1.20, "defcon": 7.69, "defcon_cbit": True,
          "note": "External Celtic xG/xA; best-guess CBITR 7.69/90 (SPFL incomplete; scout+FootyMetrics)"},
    334: {"xg": 0.070, "xa": 0.110, "saves": 0.00, "gc": 1.10, "defcon": 10.23, "defcon_cbit": True,
          "note": "External Sassuolo; FBref CBIT Defcon 10.23/90 (Muharemović)"},
    362: {"xg": 0.045, "xa": 0.085, "saves": 0.00, "gc": 1.24, "defcon": 10.87, "defcon_cbit": True,
          "note": "External Rennes/Clermont; FBref CBIT Defcon 10.87/90 (Jacquet)"},
    558: {"xg": 0.085, "xa": 0.100, "saves": 0.00, "gc": 1.20, "defcon": 12.30, "defcon_cbit": True,
          "note": "External RB Leipzig; FBref CBITR Defcon 12.30/90 (Schlager)"},
    # Draft Regular fallback packages (grill lock 2026-08-10)
    110: {"xg": 0.000, "xa": 0.000, "saves": 3.10, "gc": 1.41, "defcon": 0.00, "defcon_cbit": True,
          "note": "External CHA 2023/24 Swansea #1: Rushworth ~3.10 saves/90, GA90 1.41 (FBref)"},
    20: {"xg": 0.220, "xa": 0.120, "saves": 0.00, "gc": 1.30, "defcon": 4.50, "defcon_cbit": True,
         "note": "External best-guess: Dowman academy MID; tempered from thin 2025/26 FPL sample"},
    557: {"xg": 0.320, "xa": 0.180, "saves": 0.00, "gc": 1.25, "defcon": 2.80, "defcon_cbit": True,
          "note": "External best-guess: Tzolis Club Brugge/PAOK wing rates → FPL MID proxy"},
    152: {"xg": 0.050, "xa": 0.080, "saves": 0.00, "gc": 1.35, "defcon": 7.50, "defcon_cbit": True,
          "note": "External best-guess: Palestra Chelsea RWB/RB; CHA/U23 defensive proxy"},
    185: {"xg": 0.160, "xa": 0.140, "saves": 0.00, "gc": 1.35, "defcon": 6.80, "defcon_cbit": True,
          "note": "External best-guess: Sakamoto J-League/CHA creative MID proxy"},
    194: {"xg": 0.380, "xa": 0.100, "saves": 0.00, "gc": 1.40, "defcon": 2.20, "defcon_cbit": True,
          "note": "External best-guess: Thomas-Asante CHA FWD xG proxy (~0.38/90)"},
    279: {"xg": 0.040, "xa": 0.030, "saves": 0.00, "gc": 1.20, "defcon": 8.50, "defcon_cbit": True,
          "note": "External best-guess: Ajayi CHA/PL CB; CBIT-style Defcon proxy"},
    287: {"xg": 0.120, "xa": 0.110, "saves": 0.00, "gc": 1.40, "defcon": 7.20, "defcon_cbit": True,
          "note": "External best-guess: Millar Scottish/CHA wing-mid proxy"},
    564: {"xg": 0.000, "xa": 0.000, "saves": 3.20, "gc": 1.25, "defcon": 0.00, "defcon_cbit": True,
          "note": "External best-guess: Scherpen Ajax/Eredivisie GKP saves proxy"},
    308: {"xg": 0.050, "xa": 0.060, "saves": 0.00, "gc": 1.25, "defcon": 7.80, "defcon_cbit": True,
          "note": "External best-guess: Furlong CHA RB/CB; CBIT Defcon proxy"},
    309: {"xg": 0.100, "xa": 0.160, "saves": 0.00, "gc": 1.35, "defcon": 8.50, "defcon_cbit": True,
          "note": "External best-guess: Núñez Norwich/CHA progressive MID proxy"},
    324: {"xg": 0.180, "xa": 0.140, "saves": 0.00, "gc": 1.40, "defcon": 5.50, "defcon_cbit": True,
          "note": "External best-guess: Mehmeti Basel/CHA attacking MID proxy"},
    289: {"xg": 0.140, "xa": 0.090, "saves": 0.00, "gc": 1.40, "defcon": 9.00, "defcon_cbit": True,
          "note": "External best-guess: Crooks CHA box-mid; CBITR Defcon proxy"},
    551: {"xg": 0.170, "xa": 0.030, "saves": 0.00, "gc": 1.35, "defcon": 7.86, "defcon_cbit": True,
          "note": "External: Angulo thin 2025/26 FPL (401m) scaled xG/xA/Defcon as package"},
    283: {"xg": 0.040, "xa": 0.050, "saves": 0.00, "gc": 1.30, "defcon": 8.00, "defcon_cbit": True,
          "note": "External best-guess: Jacob NEW DEF; CBIT Defcon proxy"},
    # Newly injected Draft Regular starters (scraped 2026-08-11/12)
    461: {"xg": 0.260, "xa": 0.170, "saves": 0.00, "gc": 1.25, "defcon": 4.80, "defcon_cbit": True,
          "note": "External best-guess: Bazoumana Touré Allsvenskan wing rates → NEW MID proxy"},
    541: {"xg": 0.040, "xa": 0.080, "saves": 0.00, "gc": 1.25, "defcon": 8.80, "defcon_cbit": True,
          "note": "External 2023-26: Thomas Meunier Ligue 1 / Super Lig RB; CBIT Defcon proxy"},
    321: {"xg": 0.340, "xa": 0.140, "saves": 0.00, "gc": 1.35, "defcon": 2.40, "defcon_cbit": True,
          "note": "External best-guess: Sindre Walle Egeli Danish Superliga FWD rates → IPS proxy"},
    462: {"xg": 0.120, "xa": 0.140, "saves": 0.00, "gc": 1.30, "defcon": 5.80, "defcon_cbit": True,
          "note": "External best-guess: Sean Steur Ajax/NEW progressive midfield proxy"},
    523: {"xg": 0.220, "xa": 0.160, "saves": 0.00, "gc": 1.30, "defcon": 4.10, "defcon_cbit": True,
          "note": "External best-guess: Mikey Moore Spurs academy / creative MID proxy"},
}

# Last-season Career Individual Rates for Draft newcomers with no Prior-Season Seed.
# GC omitted: Destination Team Concede Rate is applied at build time (ADR-0014).
# New-player path: Stage 1 injects Nailed/Regular with no Prior-Season Seed → add
# {player_id: {xg, xa, saves, defcon, defcon_cbit, minutes?, note}} last completed
# senior league season. Omit gc (Destination Team Concede Rate overlays it).
# Then: uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py
CAREER_INDIVIDUAL_RATES: dict[int, dict] = {
    557: {"xg": 0.417, "xa": 0.467, "saves": 0.00, "defcon": 6.06, "defcon_cbit": True,
          "note": "2025/26 Belgian Pro League Club Brugge; ~3072m; FotMob"},
    504: {"xg": 0.188, "xa": 0.101, "saves": 0.00, "defcon": 12.46, "defcon_cbit": True,
          "note": "2025/26 Bundesliga Hamburger SV; ~2441m; FootyStats"},
    152: {"xg": 0.050, "xa": 0.104, "saves": 0.00, "defcon": 3.50, "defcon_cbit": True,
          "note": "2025/26 Serie A Cagliari; ~3084m; FotMob"},
    182: {"xg": 0.041, "xa": 0.047, "saves": 0.00, "defcon": 8.97, "defcon_cbit": True,
          "note": "2025/26 Bundesliga Eintracht Frankfurt; ~1676m; FotMob"},
    173: {"xg": 0.089, "xa": 0.104, "saves": 0.00, "defcon": 8.56, "defcon_cbit": True,
          "note": "2025/26 Championship Coventry; ~2924m; FotMob"},
    175: {"xg": 0.026, "xa": 0.141, "saves": 0.00, "defcon": 6.42, "defcon_cbit": True,
          "note": "2025/26 Championship Coventry; ~3784m; FotMob"},
    188: {"xg": 0.180, "xa": 0.198, "saves": 0.00, "defcon": 7.95, "defcon_cbit": True,
          "note": "2025/26 Championship Coventry; ~2320m; FotMob"},
    186: {"xg": 0.291, "xa": 0.166, "saves": 0.00, "defcon": 5.00, "defcon_cbit": True,
          "note": "2025/26 Championship Coventry; ~2989m; FotMob"},
    184: {"xg": 0.038, "xa": 0.199, "saves": 0.00, "defcon": 9.58, "defcon_cbit": True,
          "note": "CHA 2025/26 Coventry 4125m; xG/xA/defcon FotMob Opta"},
    185: {"xg": 0.153, "xa": 0.193, "saves": 0.00, "defcon": 6.13, "defcon_cbit": True,
          "note": "CHA 2025/26 Coventry 2494m; xG/xA/defcon FotMob Opta"},
    193: {"xg": 0.610, "xa": 0.070, "saves": 0.00, "defcon": 4.47, "defcon_cbit": True,
          "note": "CHA 2025/26 Coventry 2594m; xG/xA FootyStats Opta; CBITR FS CBIT + FotMob recovery scale"},
    194: {"xg": 0.610, "xa": 0.170, "saves": 0.00, "defcon": 6.21, "defcon_cbit": True,
          "note": "CHA 2025/26 Coventry 1865m; xG/xA FootyStats Opta; CBITR FS CBIT + FotMob recovery scale"},
    247: {"xg": 0.150, "xa": 0.233, "saves": 0.00, "defcon": 8.83, "defcon_cbit": True,
          "note": "CHA 2025/26 Middlesbrough 3314m; xG/xA/defcon FotMob Opta"},
    280: {"xg": 0.010, "xa": 0.091, "saves": 0.00, "defcon": 6.18, "defcon_cbit": True,
          "note": "CHA 2025/26 Hull 3187m; xG/xA/defcon FotMob Opta"},
    290: {"xg": 0.056, "xa": 0.054, "saves": 0.00, "defcon": 10.24, "defcon_cbit": True,
          "note": "CHA 2025/26 Hull 3156m; xG/xA/defcon FotMob Opta"},
    286: {"xg": 0.228, "xa": 0.157, "saves": 0.00, "defcon": 10.89, "defcon_cbit": True,
          "note": "CHA 2025/26 Hull 934m; xG/xA/defcon FotMob Opta"},
    287: {"xg": 0.210, "xa": 0.120, "saves": 0.00, "defcon": 7.45, "defcon_cbit": True,
          "note": "Hull CHA 2025/26; 1848 min; FootyStats xG + FotMob; CBITR proxy"},
    564: {"xg": 0.000, "xa": 0.000, "saves": 1.90, "defcon": 0.00, "defcon_cbit": True,
          "note": "Union SG Belgian Pro League 2025/26; 2835 min; FotMob 60 saves (1.90/90)"},
    562: {"xg": 0.460, "xa": 0.190, "saves": 0.00, "defcon": 7.58, "defcon_cbit": True,
          "note": "Celtic SPFL 2025/26; 2837 min; FootyStats xG/xA; CBITR proxy"},
    309: {"xg": 0.270, "xa": 0.360, "saves": 0.00, "defcon": 7.50, "defcon_cbit": True,
          "note": "Ipswich CHA 2025/26; 2234 min; FootyStats xG/xA; CBITR proxy"},
    316: {"xg": 0.440, "xa": 0.110, "saves": 0.00, "defcon": 2.78, "defcon_cbit": True,
          "note": "Toulouse Ligue 1 2025/26; 1526 min; Goalazo xG/xA; CBITR Sporting Life"},
    334: {"xg": 0.100, "xa": 0.140, "saves": 0.00, "defcon": 11.56, "defcon_cbit": True,
          "note": "Sassuolo Serie A 2025/26; 2835 min; FootyStats xG/xA; CBIT Tkl+Int+Clr+Blk"},
    362: {"xg": 0.040, "xa": 0.110, "saves": 0.00, "defcon": 8.39, "defcon_cbit": True,
          "note": "Rennes Ligue 1 2025/26; 1673 min; FootyStats xG/xA; CBIT Tkl+Int+Clr+Blk"},
    461: {"xg": 0.240, "xa": 0.310, "saves": 0.00, "defcon": 4.77, "defcon_cbit": True,
          "note": "Hoffenheim Bundesliga 2025/26; 2327 min; FootyStats xG/xA; CBITR proxy"},
    551: {"xg": 0.300, "xa": 0.280, "saves": 0.00, "defcon": 5.01, "defcon_cbit": False,
          "note": "2025/26 Belgian Pro League Anderlecht MID; 1902m; FootyStats; CBITR no recoveries"},
    541: {"xg": 0.120, "xa": 0.170, "saves": 0.00, "defcon": 4.80, "defcon_cbit": False,
          "note": "2025/26 Ligue 1 Lille DEF; 1910m; FootyStats; CBIT Tkl+Int+Blk+Clr/90"},
    20: {"xg": 0.690, "xa": 0.190, "saves": 0.00, "defcon": 9.41, "defcon_cbit": False,
         "minutes": 153, "note": "2025/26 PL Arsenal MID; 153m THIN; FotMob; U18 2024/25 no Opta"},
    110: {"xg": 0.000, "xa": 0.000, "saves": 3.11, "defcon": 0.00, "defcon_cbit": True,
          "note": "2023/24 Championship Swansea GKP; 4140m; FBref 143 saves/46.0 90s"},
    289: {"xg": 0.130, "xa": 0.070, "saves": 0.00, "defcon": 9.18, "defcon_cbit": False,
          "note": "2025/26 Championship Hull MID; 2509m; FotMob xG/xA; CBITR"},
    321: {"xg": 0.330, "xa": 0.160, "saves": 0.00, "defcon": 2.40, "defcon_cbit": False,
          "note": "2024/25 Danish Superliga Nordsjælland FWD; 2205m; FootyStats/FBref; CBITR partial"},
    462: {"xg": 0.130, "xa": 0.110, "saves": 0.00, "defcon": 6.52, "defcon_cbit": False,
          "note": "2025/26 Eredivisie Ajax MID; 1135m; FotMob; CBITR"},
    523: {"xg": 0.215, "xa": 0.172, "saves": 0.00, "defcon": 6.34, "defcon_cbit": False,
          "note": "2025/26 Scottish Premiership Rangers loan MID; 2163m; FotMob; CBITR"},
}
EXTERNAL_RESEARCH_RATES.update(CAREER_INDIVIDUAL_RATES)

DRAFT_ROLES = ("Nailed Starter", "Regular Starter")


def raise_if_draft_on_fallback(out_df: pd.DataFrame) -> None:
    """Fail-closed: Nailed/Regular must not ship on Research Position Baseline."""
    draft_fb = out_df[
        out_df["expected_role"].isin(DRAFT_ROLES)
        & out_df["rate_source"].str.contains("fallback_baseline", na=False)
    ]
    if draft_fb.empty:
        return
    names = ", ".join(
        f"{row.web_name} ({int(row.player_id)}, {row.position}, {row.club_short})"
        for row in draft_fb.itertuples()
    )
    raise SystemExit(
        "Draft players on fallback_baseline. Add last-season CAREER_INDIVIDUAL_RATES "
        f"in build_expected_stats.py then re-run Stage 2: {names}"
    )


def _per90(events: float, minutes: float) -> float:
    return (events / minutes * 90.0) if minutes > 0 else 0.0


def _rates_from_sums(
    minutes: float,
    xg: float,
    xa: float,
    defcon: float,
    saves: float,
    gc: float,
    *,
    has_defcon_evidence: bool,
) -> dict[str, float] | None:
    if minutes < MIN_USABLE_MINUTES:
        return None
    return {
        "minutes": minutes,
        "xg": _per90(xg, minutes),
        "xa": _per90(xa, minutes),
        "defcon": _per90(defcon, minutes) if has_defcon_evidence else 0.0,
        "saves": _per90(saves, minutes),
        "gc": _per90(gc, minutes),
        "has_defcon_evidence": 1.0 if has_defcon_evidence else 0.0,
    }


def _archive_season_rates(
    archive_perf: pd.DataFrame,
    archive_pid: int | None,
) -> dict[str, float] | None:
    if archive_pid is None:
        return None
    hist = archive_perf[archive_perf["player_id"] == archive_pid]
    if hist.empty:
        return None
    minutes = float(pd.to_numeric(hist["minutes"], errors="coerce").fillna(0).sum())
    xg = float(pd.to_numeric(hist["expected_goals"], errors="coerce").fillna(0).sum())
    xa = float(pd.to_numeric(hist["expected_assists"], errors="coerce").fillna(0).sum())
    defcon = float(pd.to_numeric(hist["defensive_contribution"], errors="coerce").fillna(0).sum())
    saves = float(pd.to_numeric(hist["saves"], errors="coerce").fillna(0).sum())
    gc = float(pd.to_numeric(hist["goals_conceded"], errors="coerce").fillna(0).sum())
    return _rates_from_sums(
        minutes, xg, xa, defcon, saves, gc, has_defcon_evidence=defcon > 0
    )


def _history_past_season_rates(summary_path: Path, season: str) -> dict[str, float] | None:
    if not summary_path.exists():
        return None
    try:
        with open(summary_path) as f:
            es = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    for hp in es.get("history_past", []):
        if hp.get("season_name") != season:
            continue
        minutes = float(hp.get("minutes", 0) or 0)
        defcon = float(hp.get("defensive_contribution", 0) or 0)
        if defcon <= 0:
            cbi = float(hp.get("clearances_blocks_interceptions", 0) or 0)
            tackles = float(hp.get("tackles", 0) or 0)
            recoveries = float(hp.get("recoveries", 0) or 0)
            defcon = cbi + tackles + recoveries
        has_defcon = defcon > 0
        return _rates_from_sums(
            minutes,
            float(hp.get("expected_goals", 0) or 0),
            float(hp.get("expected_assists", 0) or 0),
            defcon,
            float(hp.get("saves", 0) or 0),
            float(hp.get("goals_conceded", 0) or 0),
            has_defcon_evidence=has_defcon,
        )
    return None


def _destination_gc_map(
    fixtures: pd.DataFrame,
    clubs: pd.DataFrame,
) -> tuple[dict[str, float], float]:
    """2025/26 PL goals conceded per game by club short_name, plus league average."""
    finished = fixtures[fixtures["finished"].fillna(False).astype(bool)]
    rows: list[tuple[int, float]] = []
    for _, row in finished.iterrows():
        home_score, away_score = row.get("team_h_score"), row.get("team_a_score")
        if pd.isna(home_score) or pd.isna(away_score):
            continue
        rows.append((int(row["home_club_id"]), float(away_score)))
        rows.append((int(row["away_club_id"]), float(home_score)))
    fallback = float(POSITION_BASELINES["DEF"]["gc"])
    if not rows:
        return {}, fallback
    gc_df = pd.DataFrame(rows, columns=["club_id", "gc"])
    means = gc_df.groupby("club_id")["gc"].mean()
    id_to_short = clubs.set_index("id")["short_name"].astype(str).to_dict()
    by_short = {id_to_short[club_id]: float(value) for club_id, value in means.items() if club_id in id_to_short}
    return by_short, float(means.mean())


def _lookup_destination_gc(club_short: str, gc_map: dict[str, float], league_avg: float) -> float:
    return float(gc_map.get(str(club_short), league_avg))


def _older_fpl_career(summary_path: Path) -> tuple[str, dict[str, float]] | None:
    """Most recent FPL history_past season other than the latest archive, if ≥450 mins."""
    found: list[tuple[str, dict[str, float]]] = []
    if not summary_path.exists():
        return None
    try:
        with open(summary_path) as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    for past in payload.get("history_past", []):
        season = str(past.get("season_name") or "")
        if not season or season == LATEST_ARCHIVE_SEASON:
            continue
        rates = _history_past_season_rates(summary_path, season)
        if rates is not None:
            found.append((season, rates))
    if not found:
        return None
    found.sort(key=lambda item: item[0], reverse=True)
    return found[0]


def _career_attack(
    pid: int,
    pos: str,
    summary_path: Path,
) -> tuple[dict[str, float], str, str] | None:
    """xG/xA/Defcon/saves for a Player with no Prior-Season Seed. GC is not returned."""
    base = POSITION_BASELINES.get(pos, POSITION_BASELINES["MID"])
    if pid in EXTERNAL_RESEARCH_RATES:
        ext = EXTERNAL_RESEARCH_RATES[pid]
        use_researched_defcon = bool(ext.get("defcon_cbit")) or pid in CAREER_INDIVIDUAL_RATES
        defcon = float(ext["defcon"]) if use_researched_defcon else float(base["defcon"])
        src = "career_individual" if pid in CAREER_INDIVIDUAL_RATES else "external_3season_research"
        xg, xa, saves = float(ext["xg"]), float(ext["xa"]), float(ext["saves"])
        sample_mins = float(ext["minutes"]) if ext.get("minutes") is not None else float(MIN_USABLE_MINUTES)
        note = str(ext["note"])
        if sample_mins < MIN_USABLE_MINUTES:
            weight = sample_mins / MIN_USABLE_MINUTES
            xg = weight * xg + (1.0 - weight) * float(base["xg"])
            xa = weight * xa + (1.0 - weight) * float(base["xa"])
            if pos != "GKP":
                defcon = weight * defcon + (1.0 - weight) * float(base["defcon"])
            note = f"{note}; thin-sample shrink w={weight:.2f} toward {pos} baseline"
        rates = {"xg": xg, "xa": xa, "saves": saves, "defcon": defcon}
        return rates, src, note
    older = _older_fpl_career(summary_path)
    if older is None:
        return None
    season, rates = older
    attack = {"xg": rates["xg"], "xa": rates["xa"], "saves": rates["saves"], "defcon": rates["defcon"]}
    note = f"Older FPL {season} ({rates['minutes']:.0f}m); destination GC overlay"
    return attack, "career_fpl_prior_year", note


def _fill_seed_defcon(seed: dict[str, float], pid: int, pos: str) -> tuple[float, str]:
    if seed.get("has_defcon_evidence", 0) > 0:
        return float(seed["defcon"]), "fpl_defcon"
    if pid in EXTERNAL_RESEARCH_RATES and EXTERNAL_RESEARCH_RATES[pid].get("defcon_cbit"):
        return float(EXTERNAL_RESEARCH_RATES[pid]["defcon"]), "defcon_external_fill"
    base = POSITION_BASELINES.get(pos, POSITION_BASELINES["MID"])
    return float(base["defcon"]), "defcon_baseline_fill"


def _default_priors(role: str) -> tuple[float, float, float, float, float]:
    if role == "Nailed Starter":
        return 0.90, 0.05, 0.05, 85.0, 20.0
    if role == "Regular Starter":
        return 0.75, 0.10, 0.15, 80.0, 20.0
    if role == "Rotation":
        return 0.45, 0.25, 0.30, 70.0, 20.0
    return 0.15, 0.35, 0.50, 45.0, 15.0  # Cameo


def build_expected_stats(
    role_csv_path: str = "data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv",
    archive_processed: str = "data/archive/2025-26/processed",
    players_parquet: str = "data/processed/players.parquet",
    output_csv_path: str = "data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv",
) -> pd.DataFrame:
    df_role = pd.read_csv(role_csv_path)
    shortlist = df_role[df_role["expected_role"].isin(XI_CONTENTION_ROLES)].copy()

    archive_dir = Path(archive_processed)
    df_arch_players = pd.read_parquet(archive_dir / "players.parquet")
    df_arch_perf = pd.read_parquet(archive_dir / "player_performances.parquet")
    df_arch_fixtures = pd.read_parquet(archive_dir / "fixtures.parquet")
    df_arch_clubs = pd.read_parquet(archive_dir / "clubs.parquet")
    df_curr = pd.read_parquet(players_parquet)
    gc_map, league_avg_gc = _destination_gc_map(df_arch_fixtures, df_arch_clubs)

    code_to_archive_id = (
        df_arch_players.set_index("code")["id"].to_dict()
        if "code" in df_arch_players.columns
        else {}
    )
    curr_code = df_curr.set_index("id")["code"].to_dict() if "code" in df_curr.columns else {}

    rows = []
    needs_research: list[str] = []

    for _, srow in shortlist.iterrows():
        pid = int(srow["player_id"])
        pos = str(srow["position"])
        role = str(srow["expected_role"])
        club_short = str(srow["club_short"])
        code = curr_code.get(pid)
        archive_pid = code_to_archive_id.get(code) if code is not None else None
        summary_path = Path(f"data/raw/element_summary_{pid}.json")

        seed = _archive_season_rates(df_arch_perf, archive_pid)
        if seed is None:
            seed = _history_past_season_rates(summary_path, LATEST_ARCHIVE_SEASON)

        base = POSITION_BASELINES.get(pos, POSITION_BASELINES["MID"])
        dest_gc = _lookup_destination_gc(club_short, gc_map, league_avg_gc)
        if seed is not None:
            per90_xg = seed["xg"]
            per90_xa = seed["xa"]
            per90_saves = seed["saves"]
            per90_gc = seed["gc"]
            per90_defcon, defcon_src = _fill_seed_defcon(seed, pid, pos)
            src = "prior_season_seed"
            note = f"Prior-Season Seed {LATEST_ARCHIVE_SEASON} ({seed['minutes']:.0f}m)"
            if defcon_src != "fpl_defcon":
                src = f"{src}+{defcon_src}"
                note = f"{note}; {defcon_src}"
            usable_mins = seed["minutes"]
            usable_count = 1
        else:
            career = _career_attack(pid, pos, summary_path)
            per90_gc = dest_gc
            if career is not None:
                attack, src, note = career
                per90_xg = attack["xg"]
                per90_xa = attack["xa"]
                per90_saves = attack["saves"]
                per90_defcon = attack["defcon"]
                src = f"{src}+destination_gc"
                note = f"{note}; dest GC {club_short}={per90_gc:.3f}"
                usable_mins = 0.0
                usable_count = 0
            else:
                per90_xg = float(base["xg"])
                per90_xa = float(base["xa"])
                per90_defcon = float(base["defcon"])
                per90_saves = float(base["saves"])
                src = "fallback_baseline+destination_gc"
                note = (
                    f"Position baseline ({pos}); dest GC {club_short}={per90_gc:.3f}; "
                    "no Prior-Season Seed and no Career Individual Rate"
                )
                usable_mins = 0.0
                usable_count = 0
                needs_research.append(f"{srow['web_name']} ({pid}, {pos}, {club_short})")

        p_start, p_sub, p_dnp, xmins_s, xmins_u = _default_priors(role)
        p_start = float(srow.get("p_start", p_start))
        p_sub = float(srow.get("p_sub_in", p_sub))
        p_dnp = float(srow.get("p_dnp", p_dnp))
        xmins_s = float(srow.get("mins_if_start", xmins_s))
        xmins_u = float(srow.get("mins_if_sub", xmins_u))

        rows.append({
            "player_id": pid,
            "player_code": int(code) if code is not None and not pd.isna(code) else None,
            "web_name": srow["web_name"],
            "club_short": srow["club_short"],
            "position": pos,
            "expected_role": role,
            "p_start": p_start,
            "p_sub_in": p_sub,
            "p_dnp": p_dnp,
            "xmins_if_start": xmins_s,
            "xmins_if_sub_in": xmins_u,
            "draft_availability": srow.get("draft_availability", "eligible"),
            "availability_override": srow.get("availability_override", ""),
            "usable_season_count": usable_count,
            "usable_mins_total": round(usable_mins, 1),
            "rate_source": src,
            "per90_xg": round(per90_xg, 4),
            "per90_xa": round(per90_xa, 4),
            "per90_defcon": round(per90_defcon, 4),
            "per90_defensive_contribution": round(per90_defcon, 4),
            "per90_saves": round(per90_saves, 4),
            "per90_goals_conceded": round(per90_gc, 4),
            "provenance_note": note,
        })

    out_df = pd.DataFrame(rows)
    Path(output_csv_path).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_csv_path, index=False)
    print(f"Exported {len(out_df)} XI Contention rows to {output_csv_path}")
    print("rate_source counts:\n", out_df["rate_source"].value_counts().to_string())
    if needs_research:
        print(f"\nNeeds external research package ({len(needs_research)} Rotation/Cameo):")
        for line in needs_research[:30]:
            print(f"  - {line}")
        if len(needs_research) > 30:
            print(f"  ... +{len(needs_research) - 30} more")
    raise_if_draft_on_fallback(out_df)
    return out_df


if __name__ == "__main__":
    build_expected_stats()
