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
- Active dead levers dynamically filtered from `docs/research/candidate-ledger/candidate_ledger.csv` by subsystem focus area (`revisit_after > today` or `never`), enforcing the 1-year retest moratorium
- Reformed Promotion Gate standards from `backtesting/promotion.py` (ADR 0064: £83.5m Constrained Formation XI, non-wrapping Moving Block Bootstrap $L=5$, $\sqrt{n_s}$-scaled segment floors, squad churn limit)

Supported `--focus` modes:
- `general`: Comprehensive architectural sweep across minutes and event rates, with cross-cutting structural dead levers and active dead summary counts.
- `minutes`: Focuses on participation hazards, early substitution exits, and starter duration with minutes-subsystem dead levers.
- `events`: Focuses on rate decomposition conditioned on minutes ($xG/90$, $xA/90$, $xCS$) with match event dead levers.
- `assists`: Focuses on recipient finishing skill and key pass conversion with assist dead levers.
- `goalkeepers`: Focuses on shot threat distance vs. save volume and clean-sheet variance with goalkeeper/defensive dead levers.
- `budget-enablers`: Focuses on £4.5m–£5.5m asset valuation under the £83.5m team cap with structural/valuation dead levers.

Generated output is written to [`docs/research/candidate-ideation/candidate_model_ideation_prompt.md`](file:///home/jubileez/fpl-jubilee-ascent/docs/research/candidate-ideation/candidate_model_ideation_prompt.md).

### 2. Dispatch to External Model

Copy the generated prompt block from `candidate_model_ideation_prompt.md` into your external frontier model of choice (Claude 3.5 Sonnet, GPT-4o, Gemini 2.0/1.5 Pro).

### 3. Ingest Proposals into `idea_queue.csv` and `ideas/` Dossiers

Save the raw model response into a text/markdown file (e.g. `docs/research/candidate-ideation/raw_response.md`).

#### Path A: Fast Deterministic Ingest (CLI)
For structured model outputs adhering to the 1-shot exemplar:
```bash
uv run python .agents/skills/ideate-candidate/ingest_ideas.py docs/research/candidate-ideation/raw_response.md
```

`ingest_ideas.py`:
1. Parses candidate mechanisms, parameter grids, and affected components.
2. Checks each proposal against dead levers in `candidate_ledger.csv`. If a mechanism matches a known dead archetype, it tags the entry as `dead-match` and embeds an explicit `## Ledger Audit & Revisit Justification` block.
3. If Section 9 (Python Code Skeleton) is omitted or lacks code, automatically synthesizes a valid `AdaptiveCausalChallengerModel` subclass skeleton with typed `__init__` arguments derived from the parameter grid.
4. Atomically dual-writes the candidate specification dossier to [`docs/research/candidate-ideation/ideas/<idea_id>-<slug>.md`](file:///home/jubileez/fpl-jubilee-ascent/docs/research/candidate-ideation/ideas/) with YAML frontmatter, complete LaTeX formulations, and Python code skeletons.
5. Appends index rows with `status: untested` (or `status: dead-match` if matching an active dead lever) to [`docs/research/candidate-ideation/idea_queue.csv`](file:///home/jubileez/fpl-jubilee-ascent/docs/research/candidate-ideation/idea_queue.csv) with relative `spec_path` pointers for consumption by `explore-candidate`.

#### Path B: Agent-Assisted Fallback Ingest (Unstructured / Conversational)
Free-form, conversational, or zero-regex-match response:
1. Read raw response in `docs/research/candidate-ideation/raw_response.md` or chat transcript.
2. Normalize mechanisms into standard 9 sections:
   - Extract football hypothesis + LaTeX mathematical formulation.
   - Map decoupled component (`xp_minutes`, `xp_goals`, `xp_assists`, `xp_clean_sheets`, `xp_saves`, `xp_defcon`, `xp_bonus`).
   - Identify integration hook + parameter sweep grid ($\le 6$ variants).
   - Screen dead-lever matches against `candidate_ledger.csv`.
   - Write normalized markdown and run `ingest_ideas.py`, or dual-write dossier (`ideas/`) and append row to `idea_queue.csv`.

### 4. Automated Execution via `explore-candidate`

Once `idea_queue.csv` holds untested rows, invoking [`/explore-candidate`](../explore-candidate/SKILL.md) automatically consumes this queue by default, smoke-testing variants and evaluating winners against the ADR 0064 Historical Promotion Gate.
