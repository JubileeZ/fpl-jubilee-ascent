"""Tests for ideate-candidate skill scripts (generate_prompt.py and ingest_ideas.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "ideate-candidate"


def _load_skill_module(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SKILL_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_clean_markdown_field_preserves_underscores() -> None:
    ingest = _load_skill_module("ingest_ideas", "ingest_ideas.py")
    raw = "**Point-in-Time**: `history.minutes`; `features.position_id`; `p_start`"
    cleaned = ingest.clean_markdown_field(raw)
    assert "features.position_id" in cleaned
    assert "p_start" in cleaned
    assert "`" not in cleaned
    assert "**" not in cleaned


def test_parse_markdown_response_extracts_structured_fields() -> None:
    ingest = _load_skill_module("ingest_ideas", "ingest_ideas.py")
    sample_md = """
### Candidate 1: Asymmetric Substitution Hazard Model
1. **Concept & Football Hypothesis**: Wingers sub out early at 65' while center-backs play 90'.
2. **Mathematical Formulation**: Weibull hazard $h(t)$ conditioned on `position_id`.
3. **Decoupled Architecture Placement**: Operates in $M_{\\text{mins}}$ (`xp_minutes`).
4. **Replaces / Integration Hook**: `LearnedStartChallengerModel._state_probabilities` duration offset.
5. **Parameter Sweep Grid**: `K=600; K=1200; K=1800`
6. **Small-Sample & Cold-Start Strategy**: Blends via $N_{\\text{eff}}$.
7. **Budget-Constrained Optimizer Interaction**: Improves £4.5m defender xMins accuracy.
8. **Point-in-Time Feature Requirements**: `history.minutes`; `features.position_id`; `history.starts`
9. **Python Code Skeleton**: `class AsymmetricSubModel(BaseModel): pass`

## 2. Club Starting Mass Conservation
1. **Concept & Football Hypothesis**: Enforce club starting probability sum to 11.0 using mass conservation.
3. **Decoupled Architecture Placement**: $M_{\\text{mins}}$
8. **Point-in-Time Feature Requirements**: `features.club_id`; `p_start`
"""
    parsed = ingest.parse_markdown_response(sample_md)
    assert len(parsed) == 2

    first = parsed[0]
    assert first["idea_id"] == "EXT-01"
    assert first["name"] == "Asymmetric Substitution Hazard Model"
    assert first["component"] == "xp_minutes"
    assert "Wingers sub out early" in first["mechanism"]
    assert "Weibull hazard" in first["mechanism"]
    assert first["replaces"] == "LearnedStartChallengerModel._state_probabilities duration offset."
    assert first["grid"] == "K=600; K=1200; K=1800"
    assert first["inputs"] == "history.minutes; features.position_id; history.starts"

    second = parsed[1]
    assert second["idea_id"] == "EXT-02"
    assert second["name"] == "Club Starting Mass Conservation"
    assert "features.club_id" in second["inputs"]
    assert "p_start" in second["inputs"]


def test_ingest_file_flags_dead_levers_and_writes_queue(tmp_path: Path) -> None:
    ingest = _load_skill_module("ingest_ideas", "ingest_ideas.py")
    response_file = tmp_path / "response.md"
    queue_file = tmp_path / "idea_queue.csv"

    response_file.write_text(
        """
### Candidate MIN-09: Asymmetric Substitution Hazard
1. **Concept & Football Hypothesis**: Position-conditioned substitution hazard for wingers vs CBs.
3. **Decoupled Architecture Placement**: `xp_minutes`
4. **Replaces / Integration Hook**: `MLComponentChallengerModel._predict_minutes`
5. **Parameter Sweep Grid**: `alpha=0.1; alpha=0.2`
8. **Point-in-Time Feature Requirements**: `history.minutes`; `features.position_id`

### Candidate 2: Club 11-Man Starting Mass Conservation
1. **Concept & Football Hypothesis**: Force sum of club p_start to 11.0 via mass conservation.
3. **Decoupled Architecture Placement**: `xp_minutes`
""",
        encoding="utf-8",
    )

    rc = ingest.ingest_file(response_file, queue_path=queue_file)
    assert rc == 0
    assert queue_file.exists()

    df = pd.read_csv(queue_file)
    assert list(df.columns) == ingest.QUEUE_COLUMNS
    assert len(df) == 2

    assert df.loc[0, "order"] == 1
    assert df.loc[0, "idea_id"] == "MIN-09"
    assert df.loc[0, "status"] == "untested"
    assert df.loc[0, "grid"] == "alpha=0.1; alpha=0.2"
    assert df.loc[0, "inputs"] == "history.minutes; features.position_id"

    assert df.loc[1, "order"] == 2
    assert df.loc[1, "status"] == "dead-match"
    assert "ARCH-01" in str(df.loc[1, "nearest_ledger_row"])


def test_ingest_file_dual_writes_dossier_with_yaml_and_full_body(tmp_path: Path) -> None:
    ingest = _load_skill_module("ingest_ideas", "ingest_ideas.py")
    response_file = tmp_path / "response.md"
    queue_file = tmp_path / "idea_queue.csv"
    ideas_dir = tmp_path / "ideas"

    response_file.write_text(
        r"""
### Candidate 1: Asymmetric Substitution Hazard Model
1. **Concept & Football Hypothesis**: Wingers sub out early at 65' while center-backs play 90'.
2. **Mathematical Formulation**:
   $$P(60+ \mid \text{Start}) = \beta \cdot \theta$$
3. **Decoupled Architecture Placement**: Operates in $M_{\text{mins}}$ (`xp_minutes`).
4. **Replaces / Integration Hook**: `ParticipationStateHybridModel._compute_participation_states`.
5. **Parameter Sweep Grid**: `K=600; K=1200`
6. **Small-Sample & Cold-Start Strategy**: Regularized via $N_{\text{eff}}$.
7. **Budget-Constrained Optimizer Interaction**: Elevates £4.5m center-backs.
8. **Point-in-Time Feature Requirements**: `features.position`; `history.minutes`
9. **Python Code Skeleton**:
```python
class AsymmetricSubModel(BaseModel):
    def evaluate(self):
        return True
```

### Candidate 2: Club 11-Man Starting Mass Conservation
1. **Concept & Football Hypothesis**: Force sum of club p_start to 11.0 via mass conservation.
3. **Decoupled Architecture Placement**: `xp_minutes`
""",
        encoding="utf-8",
    )

    rc = ingest.ingest_file(response_file, queue_path=queue_file, ideas_dir=ideas_dir)
    assert rc == 0
    assert queue_file.exists()
    assert ideas_dir.exists()

    df = pd.read_csv(queue_file)
    assert "spec_path" in df.columns
    assert len(df) == 2

    # Verify first dossier
    spec_path_1 = df.loc[0, "spec_path"]
    assert spec_path_1.endswith("EXT-01-asymmetric-substitution-hazard-model.md")
    dossier_1 = ideas_dir / Path(spec_path_1).name
    assert dossier_1.exists()

    content_1 = dossier_1.read_text(encoding="utf-8")
    assert content_1.startswith("---\n")
    assert "idea_id: EXT-01\n" in content_1
    assert "name: Asymmetric Substitution Hazard Model\n" in content_1
    assert "component: xp_minutes\n" in content_1
    assert "status: untested\n" in content_1
    assert "spec_path: ideas/" in content_1
    assert "## 1. Concept & Football Hypothesis" in content_1
    assert "## 2. Mathematical Formulation" in content_1
    assert "$$P(60+ \\mid \\text{Start}) = \\beta \\cdot \\theta$$" in content_1
    assert "class AsymmetricSubModel(BaseModel):" in content_1

    # Verify second dossier with dead-lever audit section
    spec_path_2 = df.loc[1, "spec_path"]
    dossier_2 = ideas_dir / Path(spec_path_2).name
    assert dossier_2.exists()
    content_2 = dossier_2.read_text(encoding="utf-8")
    assert "status: dead-match\n" in content_2
    assert "ARCH-01" in content_2
    assert "## Ledger Audit & Revisit Justification" in content_2
    assert "ARCH-01: Club 11-man mass conservation" in content_2


def test_generate_prompt_incorporates_focus_and_gate_constants() -> None:
    gen = _load_skill_module("generate_prompt", "generate_prompt.py")
    for focus in ("general", "minutes", "budget-enablers"):
        md = gen.build_prompt_markdown(focus)
        assert "# FPL Candidate Model Ideation Prompt Brief" in md
        assert gen.FOCUS_PROMPTS[focus] in md
        assert "BOOTSTRAP_BLOCK_GWS = 5" in md
        assert "POOLED_BOOTSTRAP_MIN_P = 0.85" in md
        assert "### Candidate <N>: <Concise Name>" in md
