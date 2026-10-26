---
name: ideate-candidate
description: Generates point-in-time candidate ideation prompts for external frontier models and ingests candidate hypotheses into idea_queue.csv for explore-candidate. Use when seeking new FPL model ideas from Claude/GPT/Gemini, building focused ideation briefs, or parsing external model proposals into the work queue.
---

# Ideate Candidate

Orchestrates external frontier model ideation for FPL projection candidates. Dynamically constructs point-in-time prompt briefs reflecting current Champion state, ADR 0064 promotion gate standards, and the Candidate Ledger. Ingests structured proposals directly into the primary work queue for [`explore-candidate`](../explore-candidate/SKILL.md).

## Quickstart

```bash
# Generate general ideation prompt
uv run python .agents/skills/ideate-candidate/generate_prompt.py

# Generate targeted subsystem prompt (e.g. minutes, assists, budget-enablers)
uv run python .agents/skills/ideate-candidate/generate_prompt.py --focus minutes
uv run python .agents/skills/ideate-candidate/generate_prompt.py --focus budget-enablers

# Ingest external model ideas from raw response markdown into idea_queue.csv
uv run python .agents/skills/ideate-candidate/ingest_ideas.py path/to/external_response.md
```

---

## Workflow

### 1. Generate Point-in-Time Prompt Brief

Run `generate_prompt.py` to assemble a fresh prompt reflecting active repo reality:
- Active Champion from `config/model_selection.json`
- Dead levers from `docs/research/candidate-ledger/candidate_ledger.csv`
- Reformed Promotion Gate standards from `backtesting/promotion.py` (ADR 0064: £83.5m Constrained Formation XI, non-wrapping Moving Block Bootstrap $L=5$, $\sqrt{n_s}$-scaled segment floors, squad churn limit)

Supported `--focus` modes:
- `general`: Comprehensive architectural sweep across minutes and event rates.
- `minutes`: Focuses on participation hazards, early substitution exits, and starter duration.
- `events`: Focuses on rate decomposition conditioned on minutes ($xG/90$, $xA/90$, $xCS$).
- `assists`: Focuses on recipient finishing skill and key pass conversion.
- `goalkeepers`: Focuses on shot threat distance vs. save volume and clean-sheet variance.
- `budget-enablers`: Focuses on £4.5m–£5.5m asset valuation under the £83.5m team cap.

Generated output is written to [`docs/research/candidate-ideation/candidate_model_ideation_prompt.md`](file:///Users/jubilee/fpl-jubilee-ascent/docs/research/candidate-ideation/candidate_model_ideation_prompt.md).

### 2. Dispatch to External Model

Copy the generated prompt block from `candidate_model_ideation_prompt.md` into your external frontier model of choice (Claude 3.5 Sonnet, GPT-4o, Gemini 2.0/1.5 Pro).

### 3. Ingest Proposals into `idea_queue.csv`

Save the raw model response into a text/markdown file (e.g. `docs/research/candidate-ideation/raw_response.md`) and run:

```bash
uv run python .agents/skills/ideate-candidate/ingest_ideas.py docs/research/candidate-ideation/raw_response.md
```

`ingest_ideas.py`:
1. Parses candidate mechanisms, parameter grids, and affected components.
2. Checks each proposal against dead levers in `candidate_ledger.csv`. If a mechanism matches a known dead archetype (e.g. 11-man mass conservation, unseeded defender xG relaxation), it warns and tags the entry.
3. Appends validated rows to [`docs/research/candidate-ideation/idea_queue.csv`](file:///Users/jubilee/fpl-jubilee-ascent/docs/research/candidate-ideation/idea_queue.csv) with `status=untested`.

### 4. Automated Execution via `explore-candidate`

Once `idea_queue.csv` holds untested rows, invoking [`/explore-candidate`](../explore-candidate/SKILL.md) automatically consumes this queue by default, smoke-testing variants and evaluating winners against the ADR 0064 Historical Promotion Gate.
