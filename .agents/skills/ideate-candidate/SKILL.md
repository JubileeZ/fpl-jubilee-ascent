---
name: ideate-candidate
description: Generates point-in-time candidate ideation prompts for frontier language models and ingests candidate hypotheses into idea_queue.csv for explore-candidate. Use when seeking new FPL model ideas, building focused ideation briefs, or parsing external proposals into the work queue.
---

# Ideate Candidate

Orchestrates external frontier model ideation for FPL projection candidates. Dynamically constructs point-in-time prompt briefs reflecting current Champion state, ADR 0066 backtesting and promotion foundation standards, and the Candidate Ledger. Ingests structured proposals directly into the primary work queue for [`explore-candidate`](../explore-candidate/SKILL.md).

## Quickstart

```bash
# Generate general ideation prompt (with optional UI artifact dual-write)
uv run python .agents/skills/ideate-candidate/generate_prompt.py
uv run python .agents/skills/ideate-candidate/generate_prompt.py --artifact-out path/to/artifact_prompt.md

# Generate targeted subsystem prompt (e.g. minutes, assists, budget-enablers, fixtures)
uv run python .agents/skills/ideate-candidate/generate_prompt.py --focus minutes
uv run python .agents/skills/ideate-candidate/generate_prompt.py --focus budget-enablers
uv run python .agents/skills/ideate-candidate/generate_prompt.py --focus fixtures

# Web-browsing model 1-line dispatch (paste directly into external frontier model):
# "Read and execute the complete FPL candidate model ideation brief at https://raw.githubusercontent.com/JubileeZ/fpl-jubilee-ascent/main/docs/research/candidate-ideation/candidate_model_ideation_prompt.md. Output 5 to 7 structured candidate models adhering strictly to its 9-section format and dead-lever constraints."

# CLI ingest for external model response file (optional; direct chat paste preferred)
uv run python .agents/skills/ideate-candidate/ingest_ideas.py path/to/external_response.md
```

---

## Workflow

### 1. Generate Point-in-Time Prompt Brief

Run `generate_prompt.py` to assemble fresh prompt reflecting active repo reality:
- Active Champion from `config/model_selection.json`
- Active dead levers dynamically filtered from `docs/research/candidate-ledger/candidate_ledger.csv` by subsystem focus area (`revisit_after > today` or `never`), enforcing 1-year retest moratorium
- Promotion Gate standards from `backtesting/rolling_replay.py` and `backtesting/evidence_statistics.py` (ADR 0066: actual rolling transfer plan net score primary on 15-player £100.0m squad, paired non-wrapping MBB $L=5$ with $\text{FWER} \le 0.05$, substantive projection non-inferiority guards, and £100.0m 15-player Squad + Formation XI with bench auto-subs supporting screen)

Supported `--focus` modes:
- `general`: Comprehensive architectural sweep across minutes and event rates, with cross-cutting structural dead levers and active dead summary counts.
- `minutes`: Focuses on participation hazards, early substitution exits, and starter duration with minutes-subsystem dead levers.
- `events`: Focuses on rate decomposition conditioned on minutes ($xG/90$, $xA/90$, $xCS$) with match event dead levers.
- `assists`: Focuses on recipient finishing skill and key pass conversion with assist dead levers.
- `goalkeepers`: Focuses on shot threat distance vs. save volume and clean-sheet variance with goalkeeper/defensive dead levers.
- `budget-enablers`: Focuses on £4.5m–£5.5m asset valuation under the 15-player £100.0m squad rolling replay (ADR 0066) to fund premium talismans without squad churn.
- `fixtures`: Focuses on fixture difficulty context, venue gradients, and opponent strength elasticity ($M_{\text{events}} / M_{\text{mins}}$) to ensure fixtures impact player projections without over-inflating green matches (ARCH-05).

Generated output written to [`docs/research/candidate-ideation/candidate_model_ideation_prompt.md`](docs/research/candidate-ideation/candidate_model_ideation_prompt.md) (and optional `--artifact-out` path / native UI Artifact in interactive sessions).

### 2. Dispatch to External Model

Dispatch prompt via either:
- **1-Line URL Dispatch (Recommended for browsing models)**: Paste:
  `Read and execute the complete FPL candidate model ideation brief at https://raw.githubusercontent.com/JubileeZ/fpl-jubilee-ascent/main/docs/research/candidate-ideation/candidate_model_ideation_prompt.md. Output 5 to 7 structured candidate models adhering strictly to its 9-section format and dead-lever constraints.`
- **1-Click Artifact Copy**: Copy full text directly from Antigravity UI Artifact panel (single unified document, no nested code fences).

Prompt characteristics:
- **Critical Operational Directive**: Opens with strict directive commanding external model to execute immediately in one turn without conversational preambles or clarifying questions.
- **Public Repository Ground Truth**: Codebase public at `https://github.com/JubileeZ/fpl-jubilee-ascent`. Includes direct GitHub permalinks to active Champion, Feature Contract, Candidate Ledger, and ADRs for web-browsing models. 100% self-contained for offline models.
- **Sealed Window Boundary**: Explicitly bars browsing models from reading or mining `data/archive/2026-27/`, protecting 2026-27 GW6+ sealed evaluation window.
- **Model Neutrality**: Reusable prompts, report titles, filenames, and documentation stay model-neutral (no provider/version names; identify by specialist role, date, source artifact; exact FPL projection identifiers unchanged).

### 3. Ingest Proposals into `idea_queue.csv` and `ideas/` Dossiers

#### Path A: Direct Chat Pasting (Zero Terminal / Primary Path)
Paste raw model response directly into conversation chat. Handling:
1. Parse 9 candidate sections and hyperparameter grids.
2. Validate input covariates against the Operational Data Catalog (`features.<col>` and `history.<col>`), flagging unobserved telemetry as `status: blocked`.
3. Check against `candidate_ledger.csv` active dead levers (tagging `dead-match` when matching known archetypes).
4. Auto-scaffold Python code skeletons if Section 9 omitted.
5. Atomically dual-write markdown dossiers to [`docs/research/candidate-ideation/ideas/<idea_id>-<slug>.md`](docs/research/candidate-ideation/ideas/).
6. Append rows (`status: untested`, `status: dead-match`, or `status: blocked`) to [`docs/research/candidate-ideation/idea_queue.csv`](docs/research/candidate-ideation/idea_queue.csv).

#### Path B: Headless CLI Ingest (Scripted)
Save raw response to file and run:
```bash
uv run python .agents/skills/ideate-candidate/ingest_ideas.py path/to/external_response.md
```

### 4. Automated Execution via `explore-candidate`

Once `idea_queue.csv` holds untested rows, invoking [`/explore-candidate`](../explore-candidate/SKILL.md) automatically consumes this queue by default, smoke-testing variants and evaluating winners against the ADR 0066 Historical Promotion Gate.
