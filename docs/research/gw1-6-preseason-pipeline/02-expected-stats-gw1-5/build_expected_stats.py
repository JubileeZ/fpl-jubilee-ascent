"""Expected Stats GW1–5 builder — Prior-Season Seed + Career Individual Rate.

Rules (ADR-0014):
- Resolve archive history via FPL `code` (ADR 0004), never raw cross-season player_id.
- Prior-Season Seed = latest archive season (2025/26) with minutes >= 900.
- No seed: Career Individual Rate (xG/xA/Defcon/saves) from last-season research
  package, else most recent older FPL history_past >= 900.
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

MIN_USABLE_MINUTES = 900  # 900 — Prior-Season Seed floor (ADR-0014)
LATEST_ARCHIVE_SEASON = "2025/26"
XI_CONTENTION_ROLES = ("Nailed Starter", "Regular Starter", "Rotation", "Cameo", "Out of Contention")

POSITION_BASELINES = {
    "GKP": {"xg": 0.00, "xa": 0.00, "defcon": 0.00, "saves": 2.78, "gc": 1.38},
    "DEF": {"xg": 0.06, "xa": 0.06, "defcon": 4.25, "saves": 0.00, "gc": 1.39},
    "MID": {"xg": 0.15, "xa": 0.15, "defcon": 3.10, "saves": 0.00, "gc": 1.37},
    "FWD": {"xg": 0.41, "xa": 0.13, "defcon": 1.50, "saves": 0.00, "gc": 1.41},
}

# External packages: xG/xA/saves/gc from research.
# Defcon: use researched CBIT/CBITR when defcon_cbit=True (includes best-guess partial sources).
# If defcon_cbit=False → position baseline Defcon.
EXTERNAL_RESEARCH_RATES: dict[int, dict] = {}

CAREER_INDIVIDUAL_RATES: dict[int, dict] = {
    7: {"xg": 0.013, "xa": 0.026, "saves": 0.00, "defcon": 3.23, "defcon_cbit": True,
          "note": "Prior-Season Seed 2025/26 (697m)"},
    10: {"xg": 0.058, "xa": 0.089, "saves": 0.00, "defcon": 6.82, "defcon_cbit": True,
          "note": "Prior-Season Seed 2025/26 (699m)"},
    20: {"xg": 0.690, "xa": 0.190, "saves": 0.00, "defcon": 9.41, "defcon_cbit": False, "minutes": 153,
          "note": "2025/26 PL Arsenal MID; 153m THIN; FotMob; U18 2024/25 no Opta"},
    26: {"xg": 0.516, "xa": 0.100, "saves": 0.00, "defcon": 4.99, "defcon_cbit": True,
          "note": "Prior-Season Seed 2025/26 (577m)"},
    46: {"xg": 0.169, "xa": 0.134, "saves": 0.00, "defcon": 7.89, "defcon_cbit": True,
          "note": "Prior-Season Seed 2025/26 (844m)"},
    53: {"xg": 0.150, "xa": 0.150, "saves": 0.00, "defcon": 3.10, "defcon_cbit": True,
          "note": "Position baseline (MID); dest GC AVL=1.289; no Prior-Season Seed and no Career Individual Rate"},
    81: {"xg": 0.410, "xa": 0.130, "saves": 0.00, "defcon": 1.50, "defcon_cbit": True,
          "note": "Position baseline (FWD); dest GC BOU=1.421; no Prior-Season Seed and no Career Individual Rate"},
    99: {"xg": 0.150, "xa": 0.150, "saves": 0.00, "defcon": 3.10, "defcon_cbit": True,
          "note": "Position baseline (MID); dest GC BRE=1.368; no Prior-Season Seed and no Career Individual Rate"},
    100: {"xg": 0.150, "xa": 0.150, "saves": 0.00, "defcon": 3.10, "defcon_cbit": True,
          "note": "Position baseline (MID); dest GC BRE=1.368; no Prior-Season Seed and no Career Individual Rate"},
    110: {"xg": 0.000, "xa": 0.000, "saves": 3.11, "defcon": 0.00, "defcon_cbit": True,
          "note": "2023/24 Championship Swansea GKP; 4140m; FBref 143 saves/46.0 90s"},
    137: {"xg": 0.410, "xa": 0.130, "saves": 0.00, "defcon": 1.50, "defcon_cbit": True,
          "note": "Position baseline (FWD); dest GC BHA=1.211; no Prior-Season Seed and no Career Individual Rate"},
    152: {"xg": 0.050, "xa": 0.104, "saves": 0.00, "defcon": 3.50, "defcon_cbit": True,
          "note": "2025/26 Serie A Cagliari; ~3084m; FotMob"},
    157: {"xg": 0.380, "xa": 0.280, "saves": 0.00, "defcon": 4.20, "defcon_cbit": True,
          "note": "2024/25 Brasileirão Palmeiras; 2154m; FBref"},
    158: {"xg": 0.280, "xa": 0.220, "saves": 0.00, "defcon": 3.80, "defcon_cbit": True,
          "note": "2024/25 Bundesliga Dortmund; 1480m; FBref"},
    163: {"xg": 0.040, "xa": 0.060, "saves": 0.00, "defcon": 10.50, "defcon_cbit": True,
          "note": "2024/25 La Liga Las Palmas; 1950m; FBref"},
    173: {"xg": 0.089, "xa": 0.104, "saves": 0.00, "defcon": 8.56, "defcon_cbit": True,
          "note": "2025/26 Championship Coventry; ~2924m; FotMob"},
    174: {"xg": 0.050, "xa": 0.040, "saves": 0.00, "defcon": 8.75, "defcon_cbit": True,
          "note": "2024/26 Championship Coventry; 2450m; FBref/FotMob"},
    175: {"xg": 0.026, "xa": 0.141, "saves": 0.00, "defcon": 6.42, "defcon_cbit": True,
          "note": "2025/26 Championship Coventry; ~3784m; FotMob"},
    182: {"xg": 0.041, "xa": 0.047, "saves": 0.00, "defcon": 8.97, "defcon_cbit": True,
          "note": "2025/26 Bundesliga Eintracht Frankfurt; ~1676m; FotMob"},
    184: {"xg": 0.038, "xa": 0.199, "saves": 0.00, "defcon": 9.58, "defcon_cbit": True,
          "note": "CHA 2025/26 Coventry 4125m; FotMob Opta"},
    185: {"xg": 0.153, "xa": 0.193, "saves": 0.00, "defcon": 6.13, "defcon_cbit": True,
          "note": "CHA 2025/26 Coventry 2494m; FotMob Opta"},
    186: {"xg": 0.291, "xa": 0.166, "saves": 0.00, "defcon": 5.00, "defcon_cbit": True,
          "note": "2025/26 Championship Coventry; ~2989m; FotMob"},
    187: {"xg": 0.090, "xa": 0.160, "saves": 0.00, "defcon": 8.20, "defcon_cbit": True,
          "note": "2024/26 Championship Coventry; 2890m; FBref/FotMob"},
    188: {"xg": 0.180, "xa": 0.198, "saves": 0.00, "defcon": 7.95, "defcon_cbit": True,
          "note": "2025/26 Championship Coventry; ~2320m; FotMob"},
    192: {"xg": 0.180, "xa": 0.120, "saves": 0.00, "defcon": 5.40, "defcon_cbit": True,
          "note": "2024/26 Championship Coventry; 1250m; FBref/FotMob"},
    193: {"xg": 0.610, "xa": 0.070, "saves": 0.00, "defcon": 4.47, "defcon_cbit": True,
          "note": "CHA 2025/26 Coventry 2594m; FootyStats"},
    194: {"xg": 0.610, "xa": 0.170, "saves": 0.00, "defcon": 6.21, "defcon_cbit": True,
          "note": "CHA 2025/26 Coventry 1865m; FootyStats"},
    205: {"xg": 0.060, "xa": 0.240, "saves": 0.00, "defcon": 6.80, "defcon_cbit": True,
          "note": "2024/25 Eredivisie/Serie A; 1650m; FBref"},
    206: {"xg": 0.030, "xa": 0.020, "saves": 0.00, "defcon": 9.10, "defcon_cbit": True,
          "note": "2024/25 La Liga Real Betis; 2300m; FBref"},
    215: {"xg": 0.120, "xa": 0.140, "saves": 0.00, "defcon": 6.50, "defcon_cbit": True,
          "note": "Airdrieonians/Palace U21 MID proxy"},
    220: {"xg": 0.040, "xa": 0.060, "saves": 0.00, "defcon": 7.50, "defcon_cbit": True,
          "note": "Palace U21/senior DEF proxy"},
    235: {"xg": 0.050, "xa": 0.150, "saves": 0.00, "defcon": 7.80, "defcon_cbit": True,
          "note": "Bayern II/Morocco U23 DEF; 1550m"},
    244: {"xg": 0.420, "xa": 0.180, "saves": 0.00, "defcon": 3.20, "defcon_cbit": True,
          "note": "2024/25 PL/Championship Southampton; 2800m; FBref"},
    246: {"xg": 0.160, "xa": 0.140, "saves": 0.00, "defcon": 7.40, "defcon_cbit": True,
          "note": "2024/25 Bundesliga Freiburg; 1800m; FBref"},
    247: {"xg": 0.150, "xa": 0.233, "saves": 0.00, "defcon": 8.83, "defcon_cbit": True,
          "note": "CHA 2025/26 Middlesbrough 3314m; FotMob"},
    259: {"xg": 0.050, "xa": 0.020, "saves": 0.00, "defcon": 7.90, "defcon_cbit": True,
          "note": "Fulham / West Ham PL CB (812m in 25/26, 1720m in 24/25); confirmed £8.5m signing"},
    272: {"xg": 0.450, "xa": 0.100, "saves": 0.00, "defcon": 2.10, "defcon_cbit": True,
          "note": "Bayern U19/Fulham striker; 1100m"},
    274: {"xg": 0.000, "xa": 0.000, "saves": 2.33, "defcon": 0.00, "defcon_cbit": True,
          "note": "External SPFL 2023-26: Jack Butland Rangers proxy (no Hull mins yet); mins~9180"},
    277: {"xg": 0.050, "xa": 0.030, "saves": 0.00, "defcon": 8.50, "defcon_cbit": True,
          "note": "Prior Championship / Sheff Utd career stats: 0.05 xG, 0.03 xA, 8.50 defcon"},
    278: {"xg": 0.075, "xa": 0.055, "saves": 0.00, "defcon": 8.14, "defcon_cbit": True,
          "note": "External Preston/Wigan; FBref CBIT Defcon 8.14/90 (Andrew Hughes)"},
    279: {"xg": 0.040, "xa": 0.030, "saves": 0.00, "defcon": 8.50, "defcon_cbit": True,
          "note": "External best-guess: Ajayi CHA/PL CB; CBIT-style Defcon proxy"},
    280: {"xg": 0.010, "xa": 0.091, "saves": 0.00, "defcon": 6.18, "defcon_cbit": True,
          "note": "CHA 2025/26 Hull 3187m; xG/xA/defcon FotMob Opta"},
    281: {"xg": 0.040, "xa": 0.110, "saves": 0.00, "defcon": 6.80, "defcon_cbit": True,
          "note": "External Leeds/Hull CHA FBref full-back proxy"},
    282: {"xg": 0.025, "xa": 0.220, "saves": 0.00, "defcon": 6.50, "defcon_cbit": True,
          "note": "CHA 2025/26 Hull / Luton PL: key crossing & set piece creator"},
    283: {"xg": 0.040, "xa": 0.050, "saves": 0.00, "defcon": 8.00, "defcon_cbit": True,
          "note": "External best-guess: Jacob Hull DEF; CBIT Defcon proxy"},
    285: {"xg": 0.060, "xa": 0.040, "saves": 0.00, "defcon": 7.50, "defcon_cbit": True,
          "note": "Middlesbrough / Sunderland / NI veteran defensive proxy"},
    286: {"xg": 0.228, "xa": 0.157, "saves": 0.00, "defcon": 10.89, "defcon_cbit": True,
          "note": "CHA 2025/26 Hull 934m; xG/xA/defcon FotMob Opta"},
    287: {"xg": 0.210, "xa": 0.120, "saves": 0.00, "defcon": 7.45, "defcon_cbit": True,
          "note": "Hull CHA 2025/26; 1848 min; FootyStats xG + FotMob; CBITR proxy"},
    288: {"xg": 0.180, "xa": 0.150, "saves": 0.00, "defcon": 4.50, "defcon_cbit": True,
          "note": "Rangers / Norwich attacking midfielder proxy"},
    289: {"xg": 0.130, "xa": 0.070, "saves": 0.00, "defcon": 9.18, "defcon_cbit": False,
          "note": "2025/26 Championship Hull MID; 2509m; FotMob xG/xA; CBITR"},
    290: {"xg": 0.056, "xa": 0.054, "saves": 0.00, "defcon": 10.24, "defcon_cbit": True,
          "note": "CHA 2025/26 Hull 3156m; xG/xA/defcon FotMob Opta"},
    292: {"xg": 0.043, "xa": 0.031, "saves": 0.00, "defcon": 8.32, "defcon_cbit": True,
          "note": "External 2023-26: Abdülkadir Ömür; best-guess CBITR 8.32/90 from Hull CHA FBref"},
    293: {"xg": 0.180, "xa": 0.160, "saves": 0.00, "defcon": 5.50, "defcon_cbit": True,
          "note": "Portsmouth / Hull CHA 2024-26 winger proxy"},
    294: {"xg": 0.050, "xa": 0.080, "saves": 0.00, "defcon": 7.20, "defcon_cbit": True,
          "note": "LDU Quito / Maribor CM proxy"},
    295: {"xg": 0.480, "xa": 0.110, "saves": 0.00, "defcon": 3.20, "defcon_cbit": True,
          "note": "Hull CHA 2025/26 (18 goals) / Las Palmas / Sheff Utd PL"},
    296: {"xg": 0.150, "xa": 0.100, "saves": 0.00, "defcon": 4.50, "defcon_cbit": True,
          "note": "Adana Demirspor / Rizespor winger proxy"},
    297: {"xg": 0.060, "xa": 0.080, "saves": 0.00, "defcon": 6.80, "defcon_cbit": True,
          "note": "Plymouth Argyle / Leeds CHA CM proxy"},
    298: {"xg": 0.380, "xa": 0.080, "saves": 0.00, "defcon": 2.20, "defcon_cbit": True,
          "note": "Trabzonspor ST proxy"},
    299: {"xg": 0.350, "xa": 0.090, "saves": 0.00, "defcon": 2.50, "defcon_cbit": True,
          "note": "Sunderland / Chelsea youth FWD proxy"},
    303: {"xg": 0.050, "xa": 0.020, "saves": 0.00, "defcon": 8.80, "defcon_cbit": True,
          "note": "WBA / Reims CB defensive proxy"},
    304: {"xg": 0.060, "xa": 0.070, "saves": 0.00, "defcon": 8.20, "defcon_cbit": True,
          "note": "Burnley PL / Ipswich starting CB/RB (2880m across senior leagues)"},
    305: {"xg": 0.040, "xa": 0.320, "saves": 0.00, "defcon": 6.80, "defcon_cbit": True,
          "note": "Ipswich CHA (18 assists, 3012m) / PL elite set-piece creator"},
    306: {"xg": 0.070, "xa": 0.050, "saves": 0.00, "defcon": 9.10, "defcon_cbit": True,
          "note": "Hull / Ipswich dominant aerial & tackling CB (2980m)"},
    308: {"xg": 0.050, "xa": 0.060, "saves": 0.00, "defcon": 7.80, "defcon_cbit": True,
          "note": "External best-guess: Furlong CHA RB/CB; CBIT Defcon proxy"},
    309: {"xg": 0.270, "xa": 0.360, "saves": 0.00, "defcon": 7.50, "defcon_cbit": True,
          "note": "Ipswich CHA 2025/26; 2234 min; FootyStats xG/xA; CBITR proxy"},
    310: {"xg": 0.024, "xa": 0.032, "saves": 0.00, "defcon": 13.57, "defcon_cbit": True,
          "note": "External 2023-26: Azor Matusiwa; best-guess CBITR 13.57/90 from Ligue 1 FBref"},
    311: {"xg": 0.190, "xa": 0.160, "saves": 0.00, "defcon": 5.40, "defcon_cbit": True,
          "note": "Ipswich League One/Championship winger proxy"},
    315: {"xg": 0.240, "xa": 0.280, "saves": 0.00, "defcon": 6.50, "defcon_cbit": True,
          "note": "Leicester City / Sporting CP explosive winger (confirmed £20m transfer)"},
    316: {"xg": 0.440, "xa": 0.110, "saves": 0.00, "defcon": 2.78, "defcon_cbit": True,
          "note": "Toulouse Ligue 1 2025/26; 1526 min; Goalazo xG/xA; CBITR Sporting Life"},
    317: {"xg": 0.350, "xa": 0.120, "saves": 0.00, "defcon": 2.50, "defcon_cbit": True,
          "note": "Ipswich CHA/PL striker proxy (850m in 25/26)"},
    318: {"xg": 0.320, "xa": 0.220, "saves": 0.00, "defcon": 6.20, "defcon_cbit": True,
          "note": "Hull CHA 2023-25 / Aston Villa winger proxy"},
    320: {"xg": 0.450, "xa": 0.120, "saves": 0.00, "defcon": 2.50, "defcon_cbit": True,
          "note": "Middlesbrough CHA / Ajax forward proxy"},
    321: {"xg": 0.330, "xa": 0.160, "saves": 0.00, "defcon": 2.40, "defcon_cbit": False,
          "note": "2024/25 Danish Superliga Nordsjælland FWD; 2205m; FootyStats/FBref; CBITR partial"},
    322: {"xg": 0.380, "xa": 0.100, "saves": 0.00, "defcon": 2.50, "defcon_cbit": True,
          "note": "AFC Wimbledon / Ipswich forward proxy"},
    323: {"xg": 0.170, "xa": 0.110, "saves": 0.00, "defcon": 4.50, "defcon_cbit": True,
          "note": "Leicester City winger proxy"},
    324: {"xg": 0.180, "xa": 0.140, "saves": 0.00, "defcon": 5.50, "defcon_cbit": True,
          "note": "External best-guess: Mehmeti Bristol City/CHA attacking MID proxy"},
    329: {"xg": 0.030, "xa": 0.020, "saves": 0.00, "defcon": 8.50, "defcon_cbit": True,
          "note": "Leeds Championship / Wales CB defensive anchor proxy"},
    330: {"xg": 0.110, "xa": 0.090, "saves": 0.00, "defcon": 6.80, "defcon_cbit": True,
          "note": "Sheffield Utd PL / Leeds CHA attacking RB proxy"},
    331: {"xg": 0.040, "xa": 0.050, "saves": 0.00, "defcon": 6.15, "defcon_cbit": False,
          "note": "External 3-season: Lille / Leeds; Defcon baseline"},
    334: {"xg": 0.100, "xa": 0.140, "saves": 0.00, "defcon": 11.56, "defcon_cbit": True,
          "note": "Sassuolo Serie A 2025/26; 2835 min; FootyStats xG/xA; CBIT Tkl+Int+Clr+Blk"},
    335: {"xg": 0.090, "xa": 0.140, "saves": 0.00, "defcon": 5.71, "defcon_cbit": False,
          "note": "External 3-season: Hoffenheim / Leeds; Defcon baseline"},
    336: {"xg": 0.330, "xa": 0.110, "saves": 0.00, "defcon": 1.40, "defcon_cbit": False,
          "note": "External 3-season: Milan / Leeds; Defcon baseline"},
    338: {"xg": 0.030, "xa": 0.040, "saves": 0.00, "defcon": 7.90, "defcon_cbit": True,
          "note": "Leeds CHA captain & DM; Wales international proxy"},
    340: {"xg": 0.280, "xa": 0.140, "saves": 0.00, "defcon": 4.20, "defcon_cbit": True,
          "note": "Leeds youth / Sunderland loan forward proxy"},
    341: {"xg": 0.290, "xa": 0.210, "saves": 0.00, "defcon": 4.50, "defcon_cbit": True,
          "note": "Leeds CHA / Italy international winger proxy (640m in 25/26)"},
    343: {"xg": 0.240, "xa": 0.220, "saves": 0.00, "defcon": 5.10, "defcon_cbit": True,
          "note": "Leeds CHA / Wales winger speedster proxy"},
    344: {"xg": 0.040, "xa": 0.060, "saves": 0.00, "defcon": 7.50, "defcon_cbit": True,
          "note": "Werder Bremen / Leeds CHA DM proxy"},
    345: {"xg": 0.150, "xa": 0.120, "saves": 0.00, "defcon": 7.20, "defcon_cbit": True,
          "note": "Fortuna Düsseldorf / Leeds CHA CM progressive proxy"},
    347: {"xg": 0.400, "xa": 0.090, "saves": 0.00, "defcon": 2.20, "defcon_cbit": True,
          "note": "Wolfsburg Bundesliga / Man City forward proxy"},
    348: {"xg": 0.420, "xa": 0.110, "saves": 0.00, "defcon": 2.80, "defcon_cbit": True,
          "note": "Swansea / Leeds CHA prolific goalscorer proxy"},
    357: {"xg": 0.200, "xa": 0.250, "saves": 0.00, "defcon": 2.81, "defcon_cbit": False,
          "note": "External 3-season: Leverkusen / Liverpool DEF; Defcon baseline"},
    362: {"xg": 0.040, "xa": 0.110, "saves": 0.00, "defcon": 8.39, "defcon_cbit": True,
          "note": "Rennes Ligue 1 2025/26; 1673 min; FootyStats xG/xA; CBIT Tkl+Int+Clr+Blk"},
    369: {"xg": 0.280, "xa": 0.220, "saves": 0.00, "defcon": 4.50, "defcon_cbit": True,
          "note": "Liverpool academy breakout winger proxy (547m in 25/26)"},
    370: {"xg": 0.350, "xa": 0.240, "saves": 0.00, "defcon": 3.80, "defcon_cbit": True,
          "note": "Juventus / Italy international winger proxy (317m in 25/26)"},
    374: {"xg": 0.060, "xa": 0.050, "saves": 0.00, "defcon": 8.20, "defcon_cbit": True,
          "note": "Stuttgart / Liverpool DM veteran proxy"},
    377: {"xg": 0.260, "xa": 0.180, "saves": 0.00, "defcon": 3.50, "defcon_cbit": True,
          "note": "Real Madrid Castilla / Spain winger proxy"},
    379: {"xg": 0.690, "xa": 0.120, "saves": 0.00, "defcon": 1.80, "defcon_cbit": True,
          "note": "Newcastle / Liverpool talisman striker (694m in 25/26 due to injuries; 2758m in 24/25, 23 goals)"},
    383: {"xg": 0.220, "xa": 0.320, "saves": 0.00, "defcon": 4.10, "defcon_cbit": True,
          "note": "Liverpool attacking midfielder / winger proxy (110m in 25/26)"},
    385: {"xg": 0.000, "xa": 0.000, "saves": 3.45, "defcon": 0.00, "defcon_cbit": True,
          "note": "Burnley PL 2023/24 (2520m, 107 saves = 3.82 saves/90); confirmed £45m Leeds #1 GK"},
    395: {"xg": 0.070, "xa": 0.120, "saves": 0.00, "defcon": 6.50, "defcon_cbit": True,
          "note": "Man City fullback / DM utility proxy (401m in 25/26, 1888m in 24/25)"},
    401: {"xg": 0.420, "xa": 0.180, "saves": 0.00, "defcon": 3.20, "defcon_cbit": True,
          "note": "Eintracht Frankfurt / Man City forward proxy (691m in 25/26, 1174m in 24/25)"},
    403: {"xg": 0.280, "xa": 0.320, "saves": 0.00, "defcon": 4.80, "defcon_cbit": True,
          "note": "Girona / Man City winger proxy (817m in 25/26, 1760m in 24/25)"},
    406: {"xg": 0.080, "xa": 0.130, "saves": 0.00, "defcon": 6.80, "defcon_cbit": True,
          "note": "Man City / Chelsea veteran CM proxy (125m in 25/26, 2194m in 24/25)"},
    412: {"xg": 0.000, "xa": 0.000, "saves": 3.47, "defcon": 0.00, "defcon_cbit": True,
          "note": "External 3-season: Antwerp / Man Utd GKP saves"},
    445: {"xg": 0.110, "xa": 0.020, "saves": 0.00, "defcon": 8.78, "defcon_cbit": False,
          "note": "External 3-season: Milan / Newcastle; Defcon baseline"},
    461: {"xg": 0.260, "xa": 0.170, "saves": 0.00, "defcon": 4.80, "defcon_cbit": True,
          "note": "Hoffenheim Bundesliga 2025/26; 2327 min; FootyStats xG/xA; CBITR proxy"},
    462: {"xg": 0.120, "xa": 0.140, "saves": 0.00, "defcon": 5.80, "defcon_cbit": True,
          "note": "2025/26 Eredivisie Ajax MID; 1135m; FotMob; CBITR"},
    464: {"xg": 0.420, "xa": 0.120, "saves": 0.00, "defcon": 1.80, "defcon_cbit": False,
          "note": "Brentford / Newcastle career PL rates (~0.42 xG/90)"},
    474: {"xg": 0.060, "xa": 0.030, "saves": 0.00, "defcon": 8.65, "defcon_cbit": True,
          "note": "2024/25 Brasileirão Santos; 2100m; FBref"},
    496: {"xg": 0.000, "xa": 0.000, "saves": 3.15, "defcon": 0.00, "defcon_cbit": True,
          "note": "Spurs / Slavia Prague GKP saves (~3.15/90)"},
    504: {"xg": 0.188, "xa": 0.101, "saves": 0.00, "defcon": 12.46, "defcon_cbit": True,
          "note": "2025/26 Bundesliga Hamburger SV; ~2441m; FootyStats"},
    514: {"xg": 0.370, "xa": 0.170, "saves": 0.00, "defcon": 2.40, "defcon_cbit": False,
          "note": "External 3-season: Bayern / Spurs; Defcon baseline"},
    523: {"xg": 0.220, "xa": 0.160, "saves": 0.00, "defcon": 4.10, "defcon_cbit": True,
          "note": "2025/26 Scottish Premiership Rangers loan MID; 2163m; FotMob; CBITR"},
    529: {"xg": 0.000, "xa": 0.000, "saves": 3.27, "defcon": 0.00, "defcon_cbit": True,
          "note": "External 3-season: NEC / Sunderland GKP saves"},
    532: {"xg": 0.080, "xa": 0.020, "saves": 0.00, "defcon": 9.50, "defcon_cbit": True,
          "note": "Sunderland Championship / PL 2025/26; 2144m; FBref CBIT proxy"},
    533: {"xg": 0.090, "xa": 0.080, "saves": 0.00, "defcon": 8.42, "defcon_cbit": False,
          "note": "External 3-season: PSG / Leverkusen / Sunderland; Defcon baseline"},
    534: {"xg": 0.060, "xa": 0.120, "saves": 0.00, "defcon": 9.10, "defcon_cbit": True,
          "note": "Sunderland 2025/26; 3032m; FBref CBITR tackle/interception proxy"},
    535: {"xg": 0.060, "xa": 0.020, "saves": 0.00, "defcon": 9.82, "defcon_cbit": False,
          "note": "External 3-season: Getafe / Sunderland; Defcon baseline"},
    536: {"xg": 0.040, "xa": 0.020, "saves": 0.00, "defcon": 7.24, "defcon_cbit": False,
          "note": "External 3-season: Atletico / Sunderland; Defcon baseline"},
    539: {"xg": 0.050, "xa": 0.060, "saves": 0.00, "defcon": 8.80, "defcon_cbit": True,
          "note": "Sunderland Championship / PL; 565m 25/26; FBref CBIT leader proxy"},
    541: {"xg": 0.040, "xa": 0.080, "saves": 0.00, "defcon": 8.80, "defcon_cbit": True,
          "note": "2025/26 Ligue 1 Lille DEF; 1910m; FootyStats; CBIT Tkl+Int+Blk+Clr/90"},
    542: {"xg": 0.140, "xa": 0.200, "saves": 0.00, "defcon": 5.31, "defcon_cbit": False,
          "note": "External 3-season: Rennes / Roma / Sunderland; Defcon baseline"},
    545: {"xg": 0.070, "xa": 0.080, "saves": 0.00, "defcon": 6.25, "defcon_cbit": False,
          "note": "External 3-season: Union SG / Sunderland; Defcon baseline"},
    551: {"xg": 0.170, "xa": 0.030, "saves": 0.00, "defcon": 7.86, "defcon_cbit": True,
          "note": "2025/26 Belgian Pro League Anderlecht MID; 1902m; FootyStats; CBITR no recoveries"},
    554: {"xg": 0.000, "xa": 0.000, "saves": 3.30, "defcon": 0.00, "defcon_cbit": True,
          "note": "FC Volendam / Eredivisie GKP proxy"},
    556: {"xg": 0.020, "xa": 0.090, "saves": 0.00, "defcon": 7.10, "defcon_cbit": True,
          "note": "PL veteran Newcastle / Aston Villa full-back proxy"},
    557: {"xg": 0.417, "xa": 0.467, "saves": 0.00, "defcon": 6.06, "defcon_cbit": True,
          "note": "2025/26 Belgian Pro League Club Brugge; ~3072m; FotMob"},
    558: {"xg": 0.085, "xa": 0.100, "saves": 0.00, "defcon": 12.30, "defcon_cbit": True,
          "note": "External RB Leipzig; FBref CBITR Defcon 12.30/90 (Schlager)"},
    559: {"xg": 0.080, "xa": 0.120, "saves": 0.00, "defcon": 7.50, "defcon_cbit": True,
          "note": "Monaco Ligue 1 2025/26; 1850 min; FBref CBITR proxy"},
    562: {"xg": 0.460, "xa": 0.190, "saves": 0.00, "defcon": 7.58, "defcon_cbit": True,
          "note": "Celtic SPFL 2025/26; 2837 min; FootyStats xG/xA; CBITR proxy"},
    563: {"xg": 0.090, "xa": 0.120, "saves": 0.00, "defcon": 7.80, "defcon_cbit": True,
          "note": "Sporting CP / Liga Portugal CM proxy (free transfer to Hull)"},
    564: {"xg": 0.000, "xa": 0.000, "saves": 1.90, "defcon": 0.00, "defcon_cbit": True,
          "note": "Union SG Belgian Pro League 2025/26; 2835 min; FotMob 60 saves (1.90/90)"},
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
    """Most recent FPL history_past season other than the latest archive, if ≥900 mins."""
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
