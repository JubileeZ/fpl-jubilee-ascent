# EXT-38 development backtest

**Disposition.** Both fixed variants missed preregistered xG advancement criterion. Weekly squad and legal XI screen complete. Certified rolling replay stopped after 12 successful Champion deadlines once forecast screen closed. Historical Filter unused. Development diagnostic scope.

## Common inputs

2025–26 GW1–38. Seed 2024–25. Use manifest-bound bootstrap and fixture snapshots dated before each deadline. Fit from newest immutable settled-performance receipt strictly before origin deadline. Apply earlier-Gameweek, kickoff-time, and completed-fixture filters. Preserve admitted GW1–7 training parity. At GW24, latest receipt contains results through GW9. At GW38, latest receipt contains results through GW29. Forecast histories are conservative subsets of information available at issue.

Mutating 20 target-or-later rows per origin leaves staged fits identical at all 38 origins. Prototype independently passed static audit, zero-correction Champion parity, target mutation, and delayed-settlement checks. Variant source SHA-256 `44096462e95c2f0e28570b4ecbbfb8251291a60883f64430d152bc9e3a4cde9d`. Join official historical outcomes after predictions.

[Receipt timestamps and source digests](deadline-research-issue-provenance.csv) · [Protocol runner](run_deadline_research.py).

## Forecast comparison

- **xG MSE** = mean squared difference between exposure-scaled forecast xG and settled fixture xG. Lower is better. Benchmark Champion and matched single-mean control on identical keys. All six available leads pooled. Both variants score 144,524 outfield issue/player/fixture rows, including 85,704 recorded zero-minute outcomes. 959 issued outfield rows per arm lack matching settled keys and are excluded consistently.
- Champion MSE **0.01728126**. `k08/d16` **0.01723745** with control **0.01625590**. `k16/d32` **0.01724788** with control **0.01632673**. Both improve Champion by under 0.3%. Both trail their matched single-mean options by over 5%. DEF xG MSE rises slightly in both variants. MID and FWD xG MSE falls slightly against Champion.
- **Fixture FPL points MSE** = mean squared difference from settled official points over 153,643 common issue/player/fixture rows with positive Champion projected minutes. Lower is better. Champion **4.50838**, `k08/d16` **4.50647**, `k16/d32` **4.50684**. Signed bias uses mean forecast minus outcome, ideal zero.

[xG comparison by lead and position](ext38-deadline-xg-comparison.csv) · [xG coverage](ext38-deadline-xg-coverage.csv).

## Weekly lineup comparison

Independent 15-player £100m squad each Gameweek, max 3 per club, legal formation XI and official auto-subs. Selection uses pre-deadline market and forecasts. **Credited XI points** = sum of official points scored by credited starters over 38 Gameweeks, before captain multipliers. Higher is better. Fresh squad each week gives lineup diagnostic. Transfer hits and ownership carryover belong to rolling replay.

- Champion **2,018** credited XI points, 146 defender starts.
- `k08/d16` **2,022** (+4), 147 defender starts. Different starting XI in 14 Gameweeks.
- `k16/d32` **2,014** (−4), 148 defender starts. Different starting XI in 12 Gameweeks.

[XI summary](ext38-deadline-forecast-xi-summary.csv) · [Per-issue XI evidence](ext38-deadline-forecast-xi-by-issue.csv).

## Reproduction

Run from repo root. Add repo root and this topic directory to `PYTHONPATH`. Use `.tmp/agent/ext38-ext39` as work path.

1. Run `fetch_deadline_research_inputs.py` to recover SHA-256-pinned public development inputs.
2. Run `run_deadline_research.py .tmp/agent/ext38-ext39 stage`.
3. Run `run_deadline_research.py .tmp/agent/ext38-ext39 diagnostic` for Champion forecasts and EXT-39 comparisons.
4. Run `prototypes/ext_38/diagnostic.py --work .tmp/agent/ext38-ext39 --out .tmp/agent/ext38-ext39/ext38-diagnostic --workers 4`.
5. Run `evaluate_deadline_formation_xi.py .tmp/agent/ext38-ext39`.

[EXT-39 evidence and disposition](ideas/EXT-39-lagged-bps-and-ict-signal-check.md#10-development-results).
