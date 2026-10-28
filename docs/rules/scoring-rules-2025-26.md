# FPL scoring rules — 2025/26

Authoritative source: [Premier League — FPL basics explained: Scoring points](https://www.premierleague.com/en/news/2174909).

Captured: 2026-07-26. Re-verify when FPL rules change.

## Rules used by scoring matrix

- Minutes: 1 point up to 60 minutes; 2 points at 60 minutes or more.
- Goals: GK 10, DEF 6, MID 5, FWD 4.
- Assists: 3 points.
- Clean sheets: GK/DEF 4, MID 1, FWD 0; eligibility requires at least 60 minutes.
- Saves: 1 point per 3 goalkeeper saves.
- Penalty saves: 5 points.
- Defensive contributions: DEF 2 points at 10 CBIT; MID/FWD 2 points at 12 CBIRT; GK ineligible.
- Goals conceded: GK/DEF -1 point per 2 goals conceded.
- Penalty misses: -2 points.
- Yellow cards: -1 point.
- Red cards: -3 points.
- Own goals: -2 points.
- Bonus: 1–3 points through the match-level Bonus Points System.

The model treats thresholded events as probability or count-distribution
expectations. It does not apply `floor` to a fractional expected count.
