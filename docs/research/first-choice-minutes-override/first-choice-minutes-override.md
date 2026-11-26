# First-choice goalkeeper minutes override

## Verdict

Proposed rule improved three-fixture minutes MAE: Confirmed Champion **40.95 → 37.65** and Participation State Hybrid **48.73 → 42.68**. First-fixture MAE **28.50 → 18.60** and **43.36 → 25.20**, respectively. 75/15 sensitivity also improved three-fixture MAE in both models (**39.80**, **44.83**). Source: [results.jsonl](results.jsonl), summary rows keyed by model, `mae` by arm and fixture count.

Three added overrides, zero false overrides. Donnarumma, Areola and Johnstone each started all three scored fixtures. No extra override for either injured rival or for Pope's uncertain GW19 return. Pope started all three scored fixtures after returning. Repeated injury-cover starts would have pointed to Ramsdale at that deadline. Keep live automation gated; surface proposed rule for manual GK review with source links.

## Method

Seven documented 2025–26 club/deadline cases. Two keepers per case, next three league fixtures, same pre-deadline histories for both arms. Current arm reconstructs conservative judgment: native xMins unless club explicitly expects a named starter. Proposed arm also writes 90/0 xMins for first fixture after two consecutive league starts while rival was available on bench both times. Later fixtures retain native forecasts. Sensitivity writes 75/15 instead. Injury and return uncertainty stay outside new role override.

**Minutes MAE** = mean absolute difference between forecast and Official FPL minutes per keeper-fixture. Lower ↓. Ideal 0 minutes. **False override** = added pair override where promoted keeper does not start or displaced keeper starts in first scored fixture. Lower ↓. Ideal 0, alongside reporting count of added overrides.

Run `uv run --locked python docs/research/first-choice-minutes-override/runner.py` from repository root. JSON lines contain actual starts, minutes, forecasts, case verdicts, and model summaries. Archive performance checks cover uniqueness by player/fixture, 0–90 minutes, binary starts, and valid kickoff timestamps. Models fit on pre-deadline rows. Archived feature reconstruction excludes terminal availability fields. Prior-season seed uses 2024–25.

## Frozen evidence

- **GW6, Donnarumma / Trafford.** Donnarumma started both league matches. Trafford listed on bench both times. [Manchester derby lineup](https://www.mancity.com/news/mens/manchester-city-v-manchester-united-team-news-september-2025-63893455) · [Arsenal match report](https://www.mancity.com/news/mens/arsenal-v-manchester-city-match-report-21-september-63894065)
- **GW6, Darlow / Perri.** Perri ruled out for first two Darlow starts and still sidelined before Bournemouth. [Out for two fixtures](https://www.leedsunited.com/en/news/daniel-farke-provides-update-on-ampadu-tanaka-and-more) · [Bournemouth injury update](https://www.leedsunited.com/en/news/daniel-farke-gives-injury-update-ahead-of-bournemouth-clash)
- **GW7, Areola / Hermansen.** Areola started against Palace and Everton. Hermansen on bench both times. [Palace match lineup](https://www.whufc.com/en/news/starting-xi-wilson-starts-areola-returns-for-crystal-palace-visit) · [Everton match sheet](https://fbref.com/en/matches/1163f46d/Everton-West-Ham-United-Septe)
- **GW8, Johnstone / Sá.** Johnstone started against Spurs and Brighton. Sá on bench both times. [Spurs match report](https://www.wolves.co.uk/news/mens-first-team/20250927-report-tottenham-1-1-wolves/) · [Brighton match report](https://www.wolves.co.uk/news/mens-first-team/20251005-report-wolves-1-1-brighton/)
- **GW12, Alisson / Mamardashvili.** Reused positive control. Club expected Alisson to start, so both arms apply same first-fixture override. [Forest team news](https://www.liverpoolfc.com/news/liverpool-v-nottingham-forest-team-news-2)
- **GW15, Ramsdale / Pope.** Injury forced change. Two starts fail available-rival criterion. [Everton lineup](https://www.newcastleunited.com/en/news/team-news-six-changes-at-everton-as-ramsdale-handed-start)
- **GW19, Ramsdale / Pope.** Pope returned to squad after injury. Howe said he still needed to decide which goalkeeper to start. [Burnley team news](https://www.newcastleunited.com/en/news/eddie-howes-team-news-update-ahead-of-burnley)

## Scope

Purposeful case sample. Bench selection provides evidence of eligibility, with fitness evaluated from public reporting. Shared current arm approximates manual policy. Deadline-stamped availability, actual historical manual override sheets, User Squad, outfield overrides, and transfer actions outside test. Neither arm simulates newly published evidence at following deadlines. No model promotion, holdout use, or live preflight change.

Additional reversal check outside MAE sample: Woodman started GW34–35 while Mamardashvili was injured. Mamardashvili returned to training before GW36 and reclaimed starting spot. Two starts alone would have carried Woodman into GW36. [April injury briefing](https://www.liverpoolfc.com/news/injury-news-updates-alisson-mamardashvili-gomez-and-endo) · [May return briefing](https://www.liverpoolfc.com/news/injury-update-alisson-isak-mamardashvili-salah-and-more)
