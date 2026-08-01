# FPL 2026/27 — First-Half Chip Strategy

**Updated**: 2026-08-02T01:10:00+07:00  
**Data stamp**: FPL Focal article published 2026-07-30; source snapshot reviewed 2026-07-31  
**Season**: 2026/27 · first-half horizon GW1–19  
**Status**: Source synthesis · not independently validated  
**Purpose**: Convert one published chip-strategy guide into reusable first-half decision rules  
**Scope**: Wildcard, Free Hit, Triple Captain, and Bench Boost before GW19  
**Related**: [`research-note.md`](template/research-note.md) · [GW1–5 Chip Simulation](../gw1-5-chip-simulation/gw1-5-chip-simulation.md) · [Expected Stats GW1–5](../expected-stats-gw1-5/expected-stats-gw1-5.md)

> Source-derived claims remain separate from Project interpretation. Article fixture projections, player roles, prices, historical splits, and chip-rule statements are not verified here.

## Sources

- **Primary**: [FPL 2026/27 Chip Strategy Guide — Where Should You Use Your Chips?](https://fpl.page/article/fpl-chip-strategy-guide-2627) — Oscar / FPL Focal; published 2026-07-30; accessed 2026-07-31; role: primary strategy source

**Source boundary**: Article only. No FPL API refresh, fixture recalculation, projection-model run, official-rules check, or account-specific squad analysis performed.

## Agent Prompt

```text
Full redo docs/research/fpl-first-half-chip-strategy.md

1. Re-read https://fpl.page/article/fpl-chip-strategy-guide-2627.
2. Confirm article title, author, publication date, and first-half chip claims.
3. Keep Source synthesis separate from Project interpretation.
4. Do not present article projections as repo-validated facts.
5. If adding FPL API, fixture, or model evidence, record commands, cutoff, and validation boundary under Sources and Method.
6. Update Updated, Data stamp, Season, Findings, Decision, and Risks.
7. Keep filename stable; delete .tmp/agent/ scratch before finishing.
```

## Method

**Method type**: Primary-source synthesis

**Inputs**:
- Supplied FPL Focal article
- Article examples, fixture windows, chip definitions, and stated rationale

**Procedure**:
1. Extract source claims by chip.
2. Record candidate gameweeks, opponents, and player examples.
3. Preserve source uncertainty and conditional language.
4. Translate claims into conditional Project interpretation without adding independent evidence.

**Definitions and assumptions**:
- **First half**: GW1–19, matching source scope.
- **Early Bench Boost**: GW1 or GW2 activation.
- **Post-Wildcard Bench Boost**: activation shortly after a Wildcard rebuild.
- **Source-led**: extracted from article; not an independent project recommendation.

**Validation boundary**: Descriptive synthesis only. Article fixture and projection inputs may change or contain errors.

## Source synthesis

### Chip rules stated by source

- Wildcard: unlimited transfers for a lasting squad rebuild.
- Free Hit: unlimited transfers for one Gameweek; squad reverts afterward.
- Triple Captain: captain scores triple instead of double.
- Bench Boost: bench points count for the Gameweek.
- Source states that all chips must be used before the GW19 deadline and that two chips cannot be played in one Gameweek.

### Triple Captain

Source shortlist:

- **Players**: Haaland and Bruno as obvious candidates; Saka and Palmer as possible alternatives if form and output justify inclusion.
- **Candidate Gameweeks**: GW1, GW2, GW3, GW4, GW7, GW15, GW16, GW19.
- **Opponent pool**: promoted Coventry, Ipswich, and Hull.
- **Preferred source angle**: Hull home fixtures, especially Haaland against promoted clubs at home in GW3, GW7, or GW16.
- **Alternative**: Bruno away to Hull in GW1; Saka may retain a GW19 Ipswich home route if Haaland is not the best late option.

Source rationale:

- Hull is described as the standout target because of weak Championship defensive indicators. Article cites 13 clean sheets in 46 matches, an approximate −18.2 xG difference, +4 actual goal difference, and possibly second-worst expected goals conceded.
- Home fixtures are preferred.
- Haaland's August scoring history is cited in favor of early deployment.
- GW16 carries winter-period fatigue and fixture-density risk; December is described as a quieter scoring month.

### Bench Boost

Source decision tree:

1. Bench Boost in GW1.
2. Bench Boost in GW2.
3. Save until shortly after Wildcard.
4. Use another Gameweek only when both goalkeepers and the full bench are genuinely playable.

Source example — GW1:

- XI: Raya, Williams, Shaw, Mosquera, Bruno, Szoboszlai, Anderson, Gross, Schade, Haaland, João Pedro.
- Bench: Verbruggen, DCL, O'Shea, Ajer.
- Rationale: cheap playable bench, favorable fixtures, and limited attacker-versus-defender conflict.
- Risk: Schade minutes may be shared with Anthony; Ndiaye and other late transfer news can change the cheap-forward pool.

Source example — GW2:

- XI: Raya, Shaw, Gvardiol, Mosquera, Bruno, Szoboszlai, Anderson, Schade, Haaland, João Pedro, Brobbey.
- Bench: Petrović, Slater, Thomas, Kayode.
- Rationale: Coventry home to Hull makes cheap Coventry defenders attractive; source considers GW2 more appealing than GW1.
- Alternative: double Coventry defence, including Maguire and Van Ewijk, is presented as viable.

Source also highlights Gvardiol as a possible high-value Man City defender, based on reported squad status and a speculative Maresca back four. This remains a source hypothesis, not a verified lineup.

### Wildcard

Source windows:

- **GW4**: early window after three Gameweeks of information; attractive fixture runs for Man City, Arsenal, Chelsea, Liverpool, Man Utd, and possibly Newcastle. GW5 may provide a good post-Wildcard Bench Boost.
- **GW6**: alternative after a three-week international break; more information, possible price movement, and injury reaction time. Bournemouth is added to the target pool; Fulham face the three promoted clubs consecutively from this point.
- **GW7, GW13, GW16**: later windows if the squad remains healthy and structurally sound.

Source operating principle: do not pre-commit to one Gameweek. Activate when squad problems accumulate and a favorable fixture window arrives.

### Free Hit

| Candidate | Source case | Main condition |
| --- | --- | --- |
| GW3 | Liverpool–Ipswich, Aston Villa–Hull, Brighton–Leeds, Man City–Coventry, Brentford–Sunderland; Chelsea–Arsenal can punish existing ownership | Useful when existing Chelsea/Arsenal exposure is awkward |
| GW4 | Chelsea–Hull, Arsenal–Sunderland, Palace–Ipswich, Liverpool–Fulham, Leeds–Newcastle, Brighton–Coventry | Stronger than GW3 when Chelsea/Arsenal are under-owned |
| GW13 | Good fixtures and emergency value; source author's current preference | Save if no earlier problem forces use |
| GW16 | Man City–Hull and similar appeal | Conflicts with a Haaland Triple Captain plan |

Example source differentials include Watkins, Thiago, Vuskovic, Semenyo, and selected Arsenal, Chelsea, Liverpool, and Man City players. Player inclusion depends on the article's then-current ownership, lineup, and projection views.

## Project interpretation

### Decision rules

- **Triple Captain**: prefer a high-ceiling attacker with a home fixture against a promoted club; apply minutes, form, and fixture gates before choosing among GW3, GW7, and GW16.
- **Bench Boost**: use GW2 when all 15 players have credible minutes and favorable fixtures; otherwise target the first strong bench immediately after Wildcard.
- **Wildcard**: use GW4 when an early fixture turn and squad deterioration coincide; use GW6 when the squad can survive the longer hold and the international break adds useful information.
- **Free Hit**: preserve GW13 as emergency option when early fixtures do not force a chip; use GW3 or GW4 only when fixture concentration and current ownership create a material mismatch.
- **Chip conflict**: never plan Free Hit and Triple Captain for the same Gameweek.

### Practical implications

- Chip timing should respond to squad state plus fixture window, not calendar date alone.
- Early Bench Boost requires bench quality, not merely four active players.
- Later Free Hit retains option value for leaks, unexpected benchings, injuries, or a strong fixture slate.
- A GW16 Haaland Triple Captain plan removes that Gameweek as a Free Hit candidate.

## Findings

### Evidence

- Source prioritizes promoted-club fixtures as the central first-half chip signal.
- Source presents GW2 as the preferred early Bench Boost route when cheap players have playable fixtures.
- GW4 and GW6 are the main Wildcard windows; later activation remains valid if squad structure holds.
- Source author leans toward saving Free Hit for GW13 while retaining GW3/GW4 as ownership-dependent alternatives.
- Source does not prescribe one universal chip calendar; every recommendation is conditional on squad composition, fixture projections, and late team news.

### Alternatives

- Early aggressive path: BB GW1/GW2, then WC GW4 or GW6.
- Flexible path: hold BB and WC until a clear fixture or squad problem appears; retain FH for GW13 emergency value.
- Triple Captain path: early Bruno in GW1, early Haaland in GW3/GW7, or later Haaland in GW16; selection depends on minutes and fixture gates.

## Decision

**Verdict**: Use a conditional first-half chip plan; avoid locking every chip to a calendar Gameweek before team news and squad state are known.

**Source-led baseline**:

- BB: GW2 if 15-player bench quality passes; otherwise post-Wildcard.
- WC: GW4 or GW6, selected by squad deterioration and fixture turn.
- FH: GW13 reserve unless GW3/GW4 ownership or an emergency creates a stronger one-week slate.
- TC: Haaland against a promoted club at home if minutes and form gates pass; Bruno GW1 is the main early alternative.

**Trigger / kill switch**:

- Trigger BB only when the full bench has credible minutes and favorable fixtures.
- Kill a promoted-club Triple Captain plan if expected minutes, fixture status, or player availability deteriorates.
- Move WC later if the squad remains structurally sound and no favorable information window is lost.
- Spend FH early only for a clear fixture/ownership edge or emergency; do not spend it merely to repair one ordinary transfer.

**Validation status**: Source-derived framework; no independent validation.

**Repo simulation cross-check** (2026-08-02, not source validation): [GW1–5 chip sim](../gw1-5-chip-simulation/gw1-5-chip-simulation.md) on grill-lock projections — early BB1/BB2 + WC4 beats Standard WC4 by **+13.9 to +15.9 $xP$** over GW1–5; BB1 edges BB2 by ~2.0 $xP$. Supports source early-BB angle; TC not modeled in sim.

## Risks and unknowns

- Article is a secondary strategy source, not an official FPL rules or fixture source.
- Hull defensive statistics and historical monthly scoring claims include approximate or uncited statements.
- Fixture projections, promoted-club strength, player prices, ownership, injuries, transfers, and lineups can change before each deadline.
- Maresca backline and several player-start claims are speculative.
- GW19 chip deadline and one-chip-per-Gameweek rule should be checked against official FPL rules before operational use.
- No current User Squad, model projection, or repo fixture calculation is incorporated.

## Refresh checklist

- [ ] Re-read source and confirm publication metadata.
- [ ] Check official chip rules and deadline.
- [ ] Verify fixture list and promoted-club status.
- [ ] If adding repo data, record commands and cutoff under Sources.
- [ ] Keep source claims separate from project interpretation.
- [ ] Update `Updated`, `Data stamp`, and validation status.
- [ ] Recheck GW1–19 candidates after injuries, transfers, and lineup news.
- [ ] Delete `.tmp/agent/` scratch before finishing.
