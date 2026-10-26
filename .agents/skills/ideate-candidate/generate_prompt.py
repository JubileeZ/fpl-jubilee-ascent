"""Generate point-in-time candidate ideation prompts for external frontier models.

Assembles current Champion state, ADR 0064 Promotion Gate rules, and
Candidate Ledger constraints into a prompt brief.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

import pandas as pd


def find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for p in [current, *current.parents]:
        if (p / "pyproject.toml").exists():
            return p
    return Path(__file__).resolve().parents[3]


REPO_ROOT = find_repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backtesting.promotion import (  # noqa: E402
    BIAS_ABS_TOL,
    BOOTSTRAP_BLOCK_GWS,
    BOOTSTRAP_DRAWS,
    BOOTSTRAP_MIN_P,
    CAPTAIN_REGRET_ABS_TOL,
    CHURN_GUARDRAIL_TOL,
    COLD_START_PARITY_TOL,
    CONFIRMATION_BOOTSTRAP_MIN_P,
    GUARDRAIL_REL_TOL,
    LATE_SEGMENT_REGRESSION_TOL,
    POOLED_BOOTSTRAP_MIN_P,
    SEGMENT_REGRESSION_TOL,
    SPEARMAN_ABS_TOL,
)

DEFAULT_OUT = REPO_ROOT / "docs" / "research" / "candidate-ideation" / "candidate_model_ideation_prompt.md"
MODEL_SELECTION_PATH = REPO_ROOT / "config" / "model_selection.json"
LEDGER_PATH = REPO_ROOT / "docs" / "research" / "candidate-ledger" / "candidate_ledger.csv"

FOCUS_PROMPTS: dict[str, str] = {
    "general": (
        "Focus on comprehensive architectural breakthroughs across both participation/minutes ($M_{\\text{mins}}$) "
        "and event rates conditioned on minutes ($M_{\\text{events}}$)."
    ),
    "minutes": (
        "Focus specifically on the Participation Engine ($M_{\\text{mins}}$). Investigate position-specific "
        "early substitution hazard functions, yellow-card substitution risks, and duration offset priors "
        "without destabilizing $p_{\\text{start}}$."
    ),
    "events": (
        "Focus specifically on the Event Rate Engine ($M_{\\text{events}}$). Propose principled Bayesian shrinkage "
        "and decomposition mechanisms for underlying match events ($xG/90$, $xA/90$, $xCS$) that avoid "
        "small-sample variance spikes."
    ),
    "assists": (
        "Focus specifically on Key Pass and Assist modeling ($M_{\\text{events}}$). Explore receiver conversion "
        "quality, recipient finishing offsets, and passing danger profiles that outperform uncalibrated xA."
    ),
    "goalkeepers": (
        "Focus specifically on Goalkeeper and Defensive dynamics. Explore decoupled save intensity conditioned on "
        "opponent shot distance / volume-to-danger ratios, separating high-volume mid-table shot stoppers from elite low-event GKs."
    ),
    "budget-enablers": (
        "Focus specifically on Budget Enabler Pricing Efficiency (£4.5m–£5.5m outfield starters). Under our £83.5m "
        "Constrained Legal Formation XI budget cap, identifying accurate budget starters with high points-per-million "
        "yields massive primary delta over premium-heavy models."
    ),
}


def load_champion_info() -> tuple[str, str]:
    if not MODEL_SELECTION_PATH.exists():
        return "adaptive_causal_challenger", "provisional"
    with open(MODEL_SELECTION_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("champion", "adaptive_causal_challenger"), data.get("promotion_status", "provisional")


def load_ledger_stats() -> tuple[int, int]:
    """Return (total_trials, dead_count) from candidate_ledger.csv."""
    if not LEDGER_PATH.exists():
        return 93, 82
    df = pd.read_csv(LEDGER_PATH)
    total = len(df)
    dead = int((df["status"] == "dead").sum())
    return total, dead


def classify_dead_lever(lever_name: str, tried_as: str = "") -> str:
    """Classify a candidate ledger dead lever into its target subsystem."""
    text = f"{lever_name} {tried_as}".lower()

    # 1. Structural / cross-cutting triggers
    if any(k in text for k in (
        "schedule congestion", "congestion shift", "early ml", "early-gw",
        "ridge g/a refit", "in-season ridge", "unregularized", "ensemble",
        "continuous-n_eff", "mass conservation", "fixture swing", "matchup multiplier",
        "neutral fixture scale", "shrinkage toward neutral"
    )):
        return "structural"

    # 2. Budget enablers & pricing
    if any(k in text for k in ("price", "budget", "cost", "now_cost", "tier", "enabler", "transfer market", "transfer churn")):
        return "budget"

    # 2. Bonus system
    if any(k in text for k in ("bonus", "bps", "plackett")):
        return "bonus"

    # 3. Saves & Goalkeepers
    if any(k in text for k in ("save", "sot", "goalkeeper", "gkp")):
        return "saves_gkp"

    # 4. Clean sheets, GC, Defcon
    if any(k in text for k in ("defcon", "clean sheet", "cs/", "/cs", "per90 gc", "defence link", "post-link cs")):
        return "defense_cs"

    # 5. Assists & Key Passes
    if any(k in text for k in ("assist", "xa", "creativity", "pass")):
        return "assists"

    # 6. Minutes & Participation
    if any(k in text for k in ("p(60", "p_60", "start", "sub", "mins", "minute", "participation", "nailed", "tenure", "dnp", "play-prob")):
        return "minutes"

    # 7. Goals, Finishing, xG
    if any(k in text for k in ("goal", "xg", "finish", "attack", "cameo", "sharp")):
        return "goals"

    return "structural"


def load_active_dead_levers(today: str | None = None) -> list[dict[str, str]]:
    """Return active dead levers from candidate_ledger.csv locked by revisit_after date."""
    if not LEDGER_PATH.exists():
        return []
    df = pd.read_csv(LEDGER_PATH, dtype=str, keep_default_na=False)
    dead_df = df[df["status"] == "dead"].copy()
    if dead_df.empty:
        return []

    if today is None:
        today = date.today().isoformat()

    active: list[dict[str, str]] = []
    for _, row in dead_df.iterrows():
        revisit = str(row.get("revisit_after", "")).strip()
        if revisit == "never" or revisit > today:
            lever = str(row.get("lever", "")).strip()
            tried_as = str(row.get("tried_as", "")).strip()
            subsystem = classify_dead_lever(lever, tried_as)
            active.append({
                "status": "dead",
                "lever": lever,
                "tried_as": tried_as,
                "baseline": str(row.get("baseline", "")).strip(),
                "result": str(row.get("result", "")).strip(),
                "evidence_date": str(row.get("evidence_date", "")).strip(),
                "revisit_after": revisit,
                "evidence_path": str(row.get("evidence_path", "")).strip(),
                "subsystem": subsystem,
            })
    return active


def format_dead_levers_for_prompt(active_dead: list[dict[str, str]], focus: str) -> str:
    """Format dead levers filtered by subsystem into markdown negative constraints."""
    mins_levers = [r for r in active_dead if r["subsystem"] == "minutes"]
    goals_levers = [r for r in active_dead if r["subsystem"] == "goals"]
    assists_levers = [r for r in active_dead if r["subsystem"] == "assists"]
    saves_levers = [r for r in active_dead if r["subsystem"] == "saves_gkp"]
    def_levers = [r for r in active_dead if r["subsystem"] == "defense_cs"]
    bonus_levers = [r for r in active_dead if r["subsystem"] == "bonus"]
    budget_levers = [r for r in active_dead if r["subsystem"] == "budget"]
    structural_levers = [r for r in active_dead if r["subsystem"] == "structural"]

    def _render_list(items: list[dict[str, str]]) -> str:
        if not items:
            return "- None currently locked in this subsystem."
        lines = []
        for it in items:
            revisit_str = f"locked until {it['revisit_after']}" if it["revisit_after"] != "never" else "permanently locked"
            lines.append(f"- **{it['lever']}** (tried as: `{it['tried_as']}`, result: `{it['result']}`, {revisit_str})")
        return "\n".join(lines)

    lines: list[str] = []
    lines.append("### Strict Negative Constraints (Cross-Cutting Structural Dead Levers — DO NOT PROPOSE)")
    lines.append(
        "1. **Club 11-Man Mass Conservation** ($\\sum_{{\\text{{club}}}} p_{{\\text{{start}}}} = 11.0$): Rotating squads rotate ~12.5 starting mass across competitions; forcing 11.0 starves elite starters while inflating unplayable bench fodder ($\\Delta = -3.14 \\dots -4.13$ pts/GW, 0/3 segs).\n"
        "2. **Unregularized In-Season Ridge / Direct G/A Refits**: Small-sample cameo hauls cause unregularized regression weights to fluctuate wildly, degrading out-of-sample prediction ($\\Delta = -0.96$ pts/GW).\n"
        "3. **Relaxing Defender xG Shrinkage** ($K_{{\\text{{DEF}}}} < 2400$ pseudo-minutes): Defender xG split-half reliability is $r \\approx 0.15$; relaxing shrinkage inflates fluke header noise and induces the Optimizer's Curse ($\\Delta = -0.39 \\dots -0.84$ pts/GW).\n"
        "4. **Bonus Pool Saturation Caps** ($B_{{\\max}} \\in [1.2, 1.5]$): Compresses the expected return of talisman forwards (Haaland, Salah), distorting captaincy allocation ($\\Delta = -0.16 \\dots -0.38$ pts/GW).\n"
        "5. **Raw / Unshrunk Opponent Matchup Multipliers**: Raw Poisson multipliers or FDR tables drastically over-project returns in green fixtures and breach playable pool bias ($\\Delta = -0.68$ pts/GW).\n"
        "6. **Static Schedule Congestion Shifts** (e.g. flat $-0.20$ logit on $p_{{\\text{{start}}}}$ for $<3.5$ days rest): Penalizes nailed stamina outliers (Bruno Fernandes, Saliba) who play every 3 days without performance decay; failed confirmation ($-0.105$ pts/GW).\n"
        "7. **Discrete Step-Function Early ML Activation** (e.g. activating causal ML at GW8 or GW10, even with $[-10\\%, +10\\%]$ clamps): Early-season ML over-regularizes talisman hauls and degrades captaincy regret ($\\Delta = -2.28$ to $-5.78$ pts/GW, $P_{{\\text{{pooled}}}} = 0.000$). Early ML must use continuous $N_{{\\text{{eff}}}}$ shrinkage, not discrete early switches.\n"
        "8. **Latent HMM Participation Modeling**: Discrete role transition matrices are noisy in 38-game samples; destroys minutes MAE guardrails ($\\Delta = -0.90 \\dots -3.70$ pts/GW).\n"
        "9. **Transfer Market Churn / Price Momentum as DNP Hazard**: Casual manager selling reflects lagged sentiment and fixture swings, not manager benching hazard ($\\Delta = -0.20 \\dots -1.34$ pts/GW).\n"
        "10. **Zero-Sum Teammate Absence xG Redistribution**: Sidelined talisman volume is absorbed by tactical shape changes and lower team quality, not linearly captured by remaining teammates ($\\Delta = -0.72 \\dots -2.28$ pts/GW).\n"
        "11. **Empirical Bayes Yellow Card Rates / Venue Card Hazards**: Card rates add noise to baseline expected points without improving lineup discrimination ($\\Delta = -0.20 \\dots -0.87$ pts/GW).\n"
        "12. **Defcon Dispersion Mixtures & Beta-Binomial Hit Rates**: Over-dispersion parameter estimation noise degrades defensive points ($\\Delta = -0.13 \\dots -1.22$ pts/GW).\n"
        "13. **Natural Rate Calibration / Slope Flattening**: Addresses elite rate inflation in dev (+0.355) but collapses in confirmation ($-0.449$ pts/GW).\n"
        "14. **Goalkeeper Fixture Slot Softmax**: Softmaxing GKP start probabilities per club fixture degrades minutes discrimination ($\\Delta = -0.11 \\dots -1.21$ pts/GW).\n"
        "15. **Fitted Plackett-Luce BPS Ridge Utility on Observed BPS**: Directly regressing observed BPS introduces severe overfitting ($\\Delta = -1.44 \\dots -1.81$ pts/GW)."
    )

    if focus == "minutes":
        lines.append("\n### Active Dead Levers (Participation & Minutes Subsystem — Locked Until 1-Year Revisit Date)")
        lines.append("The following participation mechanisms were empirically evaluated and failed promotion or guardrails. They are under a mandatory 1-year freeze and MUST NOT be proposed:")
        lines.append(_render_list(mins_levers))
    elif focus == "assists":
        lines.append("\n### Active Dead Levers (Key Passes & Assists Subsystem — Locked Until 1-Year Revisit Date)")
        lines.append("The following assist mechanisms were empirically evaluated and failed promotion or guardrails. They are under a mandatory 1-year freeze and MUST NOT be proposed:")
        lines.append(_render_list(assists_levers))
    elif focus == "events":
        lines.append("\n### Active Dead Levers (Match Event Rates Subsystem — Locked Until 1-Year Revisit Date)")
        lines.append("The following event rate mechanisms were empirically evaluated and failed promotion or guardrails. They are under a mandatory 1-year freeze and MUST NOT be proposed:")
        lines.append("\n#### Goals & Finishing Dead Levers:")
        lines.append(_render_list(goals_levers))
        lines.append("\n#### Assists & Key Passes Dead Levers:")
        lines.append(_render_list(assists_levers))
        lines.append("\n#### Defensive Points & Clean Sheets Dead Levers:")
        lines.append(_render_list(def_levers))
        lines.append("\n#### Goalkeeper Saves Dead Levers:")
        lines.append(_render_list(saves_levers))
        lines.append("\n#### Bonus Point System Dead Levers:")
        lines.append(_render_list(bonus_levers))
    elif focus == "goalkeepers":
        lines.append("\n### Active Dead Levers (Goalkeepers & Defensive Contributions Subsystem — Locked Until 1-Year Revisit Date)")
        lines.append("The following goalkeeper and defensive mechanisms were empirically evaluated and failed promotion or guardrails. They are under a mandatory 1-year freeze and MUST NOT be proposed:")
        lines.append("\n#### Goalkeeper Saves Dead Levers:")
        lines.append(_render_list(saves_levers))
        lines.append("\n#### Clean Sheets & Defensive Expectations Dead Levers:")
        lines.append(_render_list(def_levers))
    elif focus == "budget-enablers":
        lines.append("\n### Active Dead Levers (Budget Enablers & Valuation Subsystem — Locked Until 1-Year Revisit Date)")
        lines.append("The following valuation and enabler mechanisms were empirically evaluated and failed promotion or guardrails. They are under a mandatory 1-year freeze and MUST NOT be proposed:")
        lines.append(_render_list(budget_levers or structural_levers))
    else:  # general
        lines.append(f"\n### Active Dead Levers by Subsystem Summary ({len(active_dead)} Locked Levers)")
        lines.append(
            f"Over {len(active_dead)} candidate levers are currently locked under the 1-year moratorium. Proposals matching any of these archetypes will be rejected:\n"
            f"- **Participation & Minutes ({len(mins_levers)} dead levers)**: e.g. Beta-Binomial P(60|state), starter tenure decay, naive nailed-starter multipliers.\n"
            f"- **Goals & Finishing ({len(goals_levers)} dead levers)**: e.g. high-K finishing pools ($K \\ge 3600$), unsharp xG slope flattening, flat position goal scales.\n"
            f"- **Key Passes & Assists ({len(assists_levers)} dead levers)**: e.g. pooled assist finishing offsets, uncalibrated raw xA.\n"
            f"- **Goalkeepers & Saves ({len(saves_levers)} dead levers)**: e.g. club SoT volume x pooled save rate, slot probability softmax.\n"
            f"- **Defense & Clean Sheets ({len(def_levers)} dead levers)**: e.g. defcon venue/opposition pressure, post-link CS inflation, club-pooled per90 GC.\n"
            f"- **Bonus Points / BPS ({len(bonus_levers)} dead levers)**: e.g. BPS pool saturation caps, softmax temperature retuning."
        )

    return "\n".join(lines)


def build_prompt_markdown(focus: str) -> str:
    champ_name, champ_status = load_champion_info()
    total_trials, dead_count = load_ledger_stats()
    active_dead = load_active_dead_levers()
    focus_guidance = FOCUS_PROMPTS.get(focus, FOCUS_PROMPTS["general"])
    mae_mult = 1.0 + GUARDRAIL_REL_TOL
    dead_constraints_block = format_dead_levers_for_prompt(active_dead, focus)

    return f"""# FPL Candidate Model Ideation Prompt Brief

```markdown
You are a Principal Quantitative Sports Modeler and Machine Learning Engineer specializing in association football (soccer) analytics and combinatorial lineup optimization for Fantasy Premier League (FPL).

### Context & System Environment
You are advising the core quantitative modeling team of `fpl-jubilee-ascent`, an open-source FPL projection and combinatorial optimization engine. The engine runs on Python 3.14, using an expanding-window causal feature store, empirical Bayes scoring models, and a vendored HiGHS Mixed-Integer Linear Programming (MILP) solver.

We operate under strict empirical model governance:
- **Active Model Champion**: `{champ_name}` ({champ_status}). It builds upon `def_xg_shrink_challenger` with 100% Champion stability across Gameweeks 1–19, activating stacked zero-leakage Causal Panel ML models (Ridge logistic $p_{{\\text{{start}}}}$, Ridge duration offset, shrunk xG goals residual, leave-one-out assist finishing) from Gameweek 20 onward.
- **Critical ADR 0064 Finding**: Under our reformed **Constrained Legal Formation XI** (£83.5m starting budget cap, $\\le 3$ per club), `def_xg_shrink_challenger` actually outperformed `adaptive_causal_challenger` on the 2025–26 Dev season ($\\Delta = +0.8947$ pts/GW). The apparent unconstrained margin of `adaptive_causal_challenger` was an artifact of selecting £100m+ illegal squads. True predictive alpha requires accurately valuing budget enablers under strict team constraints, rather than over-indexing on expensive premium assets.
- **Downstream Consumer**: Multi-period HiGHS MILP solver optimizing transfer paths and lineups over a 5–10 GW horizon subject to 5 "Strategic" variance constraints (ADR 0061: paid hit hurdle, starter minutes floors, bench coverage, defensive stack caps, and GK transfer friction).
- **Promotion Gate (ADR 0064)**: Any new model ("Candidate") must pass our reformed two-season gate: Constrained Legal Formation XI (£83.5m cap, $\\le 3$ per club), rolling squad churn guardrail ($\\le \\text{{Champ}} + {CHURN_GUARDRAIL_TOL:.2f}$ players/GW), warm-seeded confirmation (2023–24 seed for 2024–25 conf, matching live deployment $N_{{\\text{{prior}}}}=1$), non-wrapping Moving Block Bootstrap ($L={BOOTSTRAP_BLOCK_GWS}$, $B={BOOTSTRAP_DRAWS:,}$), three bootstrap bars (Dev $P \\ge {BOOTSTRAP_MIN_P:.2f}$, Warm Conf $P \\ge {CONFIRMATION_BOOTSTRAP_MIN_P:.2f}$, Pooled Stratified $P \\ge {POOLED_BOOTSTRAP_MIN_P:.2f}$), $\\sqrt{{n_s}}$-scaled segment floors (cold_start $\\ge -{COLD_START_PARITY_TOL:.2f}$, early_mid $\\ge -{SEGMENT_REGRESSION_TOL:.2f}$, late $\\ge -{LATE_SEGMENT_REGRESSION_TOL:.2f}$), and dual-window safety guardrails across both full season and active gameweeks.
- **Historical Ledger**: Over {total_trials} candidate model levers have been empirically evaluated. {dead_count} have failed or been logged dead ({len(active_dead)} currently locked under 1-year moratorium). We maintain an authoritative taxonomy of proven dead levers that must NOT be proposed.

### Your Mission
Generate an actionable, innovative, and mathematically sound slate of 5 to 7 NEW Candidate Projection Models (or component mechanisms) that can defeat `{champ_name}` and `def_xg_shrink_challenger` under the ADR 0064 Historical Promotion Gate.

**Focus Area**: {focus_guidance}

{dead_constraints_block}

### Required Output Structure for Each Candidate Idea
Format each proposed candidate with a level-3 markdown heading `### Candidate <N>: <Concise Name>` followed by these exact numbered sections (parsed directly by our queue ingestion tool):
1. **Concept & Football Hypothesis**: Concrete statement of the physical football phenomenon or market inefficiency captured, and why existing Champion mechanisms miss it.
2. **Mathematical Formulation**: Exact equations, prior distributions, likelihoods, shrinkage parameters ($K$, $\\lambda$), and link functions.
3. **Decoupled Architecture Placement**: State whether this operates in $M_{{\\text{{mins}}}}$ (`xp_minutes`) or $M_{{\\text{{events}}}}$ (`xp_goals`, `xp_assists`, `xp_clean_sheets`, `xp_saves`, `xp_defcon`, `xp_bonus`).
4. **Replaces / Integration Hook**: Exact Champion method or component hook this mechanism replaces or modifies.
5. **Parameter Sweep Grid**: Semicolon-separated list of $\\le 6$ concrete hyperparameter variants for smoke testing (e.g. `K=600; K=1200; K=1800`).
6. **Small-Sample & Cold-Start Strategy**: How does it integrate with warm historical seeding ($N_{{\\text{{prior}}}}=1$) and continuous $N_{{\\text{{eff}}}}$ sample shrinkage ($N_{{\\min}}=3500, N_{{\\text{{full}}}}=7500$), avoiding Nickell bias and early-season over-regularization?
7. **Budget-Constrained Optimizer Interaction**: Why does this proposed profile resist the Optimizer's Curse under the £83.5m Constrained Legal Formation XI and rolling squad churn guardrail ($\\le {CHURN_GUARDRAIL_TOL:.2f}$ players/GW)?
8. **Point-in-Time Feature Requirements**: Semicolon-separated manifest of point-in-time covariates needed (`features.<col>` / `history.<col>`, strictly pre-match deadline $\\mathcal{{H}}_{{<g}}$; zero terminal leakage).
9. **Python Code Skeleton (Optional)**: Class definition stub conforming to `AdaptiveCausalChallengerModel` or `BaseModel`. If response length is constrained, this can be an abbreviated stub or omitted if mathematical formulation and parameter sweep grid are fully specified; our tooling will auto-scaffold class skeletons.

### 1-Shot Concrete Exemplar

### Candidate 1: Continuous Game-Pace & Match-State Elasticity
1. **Concept & Football Hypothesis**: Trailing scorelines and match tempo significantly alter shot generation, transition volume, and defensive block depth. Center-backs face fewer defensive clearances/tackles when leading comfortably, while attacking wingers gain high-xG counter-attack opportunities in trailing game states.
2. **Mathematical Formulation**:
   $$\\lambda_{{xG, i}}(g) = \\lambda_{{xG, i}}^0 \\cdot \\exp\\left(\\alpha_{{\\text{{pace}}}} \\cdot (\\bar{{P}}_{{\\text{{pace}}, o}} - 1.0) + \\beta_{{\\text{{margin}}}} \\cdot \\mathbb{{E}}[\\Delta \\text{{Score}}_{{c, o}}]\\right)$$
   $$\\lambda_{{xA, i}}(g) = \\lambda_{{xA, i}}^0 \\cdot \\exp\\left(\\alpha_{{\\text{{pace}}}} \\cdot (\\bar{{P}}_{{\\text{{pace}}, o}} - 1.0) + \\beta_{{\\text{{margin}}}} \\cdot \\mathbb{{E}}[\\Delta \\text{{Score}}_{{c, o}}]\\right)$$
   where $\\bar{{P}}_{{\\text{{pace}}, o}}$ is opponent match-pace factor shrunk toward 1.0, and $\\Delta \\text{{Score}}_{{c, o}}$ is expected scoreline margin from bookmaker spreads.
3. **Decoupled Architecture Placement**: Operates in $M_{{\\text{{events}}}}$ (`xp_goals`, `xp_assists`).
4. **Replaces / Integration Hook**: `CalibratedMatchupHybridModel._project_event_components`
5. **Parameter Sweep Grid**: `alpha_pace=0.15,beta_margin=-0.08; alpha_pace=0.25,beta_margin=-0.08; alpha_pace=0.20,beta_margin=-0.12; alpha_pace=0.15,beta_margin=-0.05`
6. **Small-Sample & Cold-Start Strategy**: Opponent pace and margin coefficients are anchored to zero at season start ($N_{{\\text{{eff}}}} < 3500$) and smoothly ramped to full weight via continuous $N_{{\\text{{eff}}}}$ sample shrinkage, preventing early-season over-reaction.
7. **Budget-Constrained Optimizer Interaction**: Rewards counter-attacking £5.0m midfielders against high-possession heavy favorites without triggering erratic squad churn.
8. **Point-in-Time Feature Requirements**: `features.opponent_id`; `history.opp_pace_per90_eb`; `history.exp_goal_diff_eb`
9. **Python Code Skeleton (Optional)**:
```python
from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel

class GamePaceElasticityChallengerModel(AdaptiveCausalChallengerModel):
    def __init__(self, alpha_pace: float = 0.20, beta_margin: float = -0.08, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.alpha_pace = float(alpha_pace)
        self.beta_margin = float(beta_margin)
```

Review the complete technical specification below before generating candidate recommendations.
```

---

## Part 2: Technical Architecture & System Specification

```mermaid
flowchart TD
    API["Official FPL API / Archive Parquet"] --> Processor["features/processor.py (Point-in-Time Parquet)"]
    Processor --> Features["features/builder.py (FeatureContract)"]
    Features --> Decoupled["Decoupled Projection Architecture"]
    
    subgraph Decoupled ["Decoupled Projection Engine"]
        Mins["M_mins: Participation Engine\\n(p_start, p_sub, p_dnp, xmins)"]
        Events["M_events: Event Rate Engine\\n(xG/90, xA/90, xCS, xGC, xSaves, xDefcon)"]
        Matchup["Calibrated Matchup Share (ADR 0040)\\n(s=0.40 shrinkage toward neutral)"]
        Matrix["Scoring Matrix Reconstruct (ADR 0003)\\n(13 FPL scoring rules + NegBin + Plackett-Luce)"]
        
        Mins --> Matrix
        Events --> Matchup --> Matrix
    end
    
    Matrix --> Contract["projections/contract.py (ProjectionContract: xP, xP/GW)"]
    Contract --> Gate["Reformed Promotion Gate (ADR 0064)\\nConstrained XI (£83.5m) + Non-wrapping Bootstrap (L=5)"]
    Contract --> Solver["solver/solver.py (HiGHS MILP 5 Strategic Constraints)"]
    Solver --> Output["Transfer Plans (data/solution.json) & Lineup Cards"]
```

### 1. The Active Model Champion: `{champ_name}` ({champ_status})

The active Champion uses an object-oriented inheritance lineage terminating in `AdaptiveCausalChallengerModel`:

```
BaseModel (models/base.py)
  └── ComponentBaselineModel (models/component_baseline.py)
        └── MetricsComponentHybridModel (models/metrics_component_hybrid.py)
              └── ParticipationStateHybridModel (models/participation_state_hybrid.py)
                    └── CalibratedMatchupHybridModel (models/calibrated_matchup_hybrid.py)
                          └── HoldChaseChallengerModel (models/hold_chase_challenger.py)
                                └── FaceValueChallengerModel (models/face_value_challenger.py)
                                      └── MultiFeatureAssistChallengerModel (models/multi_feature_assist_challenger.py)
                                            └── LearnedStartChallengerModel (models/learned_start_challenger.py)
                                                  └── DefXgShrinkChallengerModel (models/def_xg_shrink_challenger.py)
                                                        └── MLComponentChallengerModel (models/ml_component_challenger.py)
                                                              └── AdaptiveCausalChallengerModel [CHAMPION] (models/adaptive_causal_challenger.py)
```

#### Lineage Mechanism Breakdown:
1. **Event-Level Empirical Bayes & Scoring Matrix Reconstruct (ADR 0003)**:
   - Projections do not predict raw fantasy points directly. They project underlying match events and pass them through exact FPL rule calculations:
     - Goals: Position-weighted (GK/DEF: 6, MID: 5, FWD: 4).
     - Clean Sheets: Pitch clean sheet probability $e^{{-\\lambda_{{\\text{{pitch}}}}}} \\times P(60+\\text{{ mins}})$ (GK/DEF: 4, MID: 1).
     - Goals Conceded: Negative Binomial expectation $\\mathbb{{E}}[\\lfloor X/2 \\rfloor]$ with dispersion $r=3.0$ ($-1$ pt per 2 GC for GK/DEF).
     - Defensive Contributions (Defcon): Negative Binomial probability of $\\ge 10$ (DEF) or $\\ge 12$ (MID/FWD) CBI/tackles (+2 pts).
     - Saves: Poisson expectation $\\mathbb{{E}}[\\lfloor \\text{{saves}}/3 \\rfloor]$ (+1 pt per 3 saves for GK).
     - Bonus Points System (xBPS): Synthetic BPS score modeled via Plackett-Luce rank choice.
2. **Three-State Participation Engine**:
   - For every player and fixture:
     $$P(\\text{{DNP}}) + P(\\text{{Start}}) + P(\\text{{Sub-in}}) = 1.0$$
   - Expected minutes: $\\mathbb{{E}}[\\text{{Mins}}] = P(\\text{{Start}}) \\cdot xMins_{{\\text{{start}}}} + P(\\text{{Sub-in}}) \\cdot xMins_{{\\text{{sub}}}}$ (where baseline $xMins_{{\\text{{start}}}} \\approx 78.0$, $xMins_{{\\text{{sub}}}} \\approx 18.0$).
   - $P(60+\\mid \\text{{state}}) = \\text{{clip}}\\left(\\frac{{\\text{{minutes}} - 45.0}}{{30.0}}, 0.0, 1.0\\right)$.
   - Operational Hard DNP (ADR 0056): FPL injury status $\\in \\{{'i', 's', 'u', 'n'\\}}$ or `chance_of_playing == 0` forces $P(\\text{{DNP}}) = 1.0$.
3. **Calibrated Matchup Share (ADR 0040)**:
   - Eliminates volatile FDR tables. Multipliers scale club attacking and defensive strength relative to league averages, shrunk by $s = 0.40$ toward neutral ($1.0$).
4. **Face-Value Attack & Minute-Pooled Goal Finishing (ADR 0045)**:
   - Fixed weights: $1.0 \\times xG$ and $1.0 \\times xA$ (raw threat/creativity zeroed out).
   - Finishing skill offset over $K=1800$ pseudo-minutes:
     $$\\text{{Offset}}_i = \\frac{{\\sum (\\text{{Goals}}_i - xG_i) \\cdot 90}}{{\\sum \\text{{Minutes}}_i + 1800.0}}$$
5. **Defender xG Shrinkage (ADR 0055)**:
   - Defenders exhibit split-half xG reliability of $r \\approx 0.15$. The Champion shrinks defender xG/90 toward the position mean using $K_{{\\text{{DEF}}}}=2400$ pseudo-minutes (attackers use $K=360$):
     $$\\hat{{\\lambda}}_{{xG, \\text{{DEF}}}} = \\frac{{\\sum xG_{{\\text{{observed}}}} \\cdot 90 + K_{{\\text{{DEF}}}} \\cdot \\bar{{\\lambda}}_{{\\text{{pos}}}}}}{{\\sum \\text{{Minutes}} + K_{{\\text{{DEF}}}}}}$$
   - Prevents the optimizer from loading up on center-backs who head home early fluke goals.
6. **Adaptive Causal ML Activation (ADR 0063)**:
   - **GW 1–19**: Evaluates purely through `def_xg_shrink_challenger`.
   - **GW 20+**: Activates stacked Causal Panel ML models via a 5-GW Bayesian ramp ($w_{{\\text{{ML}}}} = \\min(1.0, \\frac{{\\text{{GW}} - 19}}{{5}})$):
     - **Tier 1 Minutes**: Ridge logistic regression on $p_{{\\text{{start}}}}$ ($H_1$) + Ridge linear regression on starter duration offset ($H_3$). Sub-in classifier ($H_2$) disabled.
     - **Tier 2 Events**: Group A Shrunk xG Goals Residual + Group B Calibrated Leave-One-Out (LOO) Assist Finishing ($\\omega = 0.95^{{\\Delta \\text{{GW}}}}$ exponential decay, bounded $[0.88, 1.15]$). Defensive and Bonus ML heads disabled.
7. **Empirical Bayes Priors & Continuous $N_{{\\text{{eff}}}}$ Shrinkage (ADR 0064 / Issue #168)**:
   - In `models/ml_panel_features.py`, short-panel features are regularized with Empirical Bayes positional price-tier priors ($K_{{\\text{{prior}}}} = 12.0$).
   - Continuous sample-size shrinkage replaces discrete gameweek thresholds:
     $$\\alpha_g = \\text{{clip}}\\left(\\frac{{N_{{\\text{{eff}}, g}} - N_{{\\min}}}}{{N_{{\\text{{full}}}} - N_{{\\min}}}}, 0.0, 1.0\\right)$$
     where $N_{{\\text{{eff}}, g}} = 0.5 N_{{\\text{{seed}}}} + N_{{\\text{{in\\_season}}, <g}}$, with $N_{{\\min}} = 3500$, $N_{{\\text{{full}}}} = 7500$.

---

### 2. Downstream Optimization: HiGHS MILP Solver & Strategic Constraints (ADR 0061)

The solver does not pick an isolated 11-man team; it solves a multi-period Mixed-Integer Linear Program over horizon $W \\in [5, 10]$ gameweeks, balancing squad transfers, bank value, captaincy, and bench order:

$$\\max_{{\\mathbf{{x}}, \\mathbf{{c}}, \\mathbf{{b}}, \\mathbf{{t}}_{{\\text{{in}}}}, \\mathbf{{t}}_{{\\text{{out}}}}}} \\sum_{{w=1}}^W \\gamma^{{w-1}} \\left( \\sum_{{p=1}}^P \\left( x_{{p,w}} \\hat{{y}}_{{p,w}} + c_{{p,w}} \\hat{{y}}_{{p,w}} + b_{{p,w}} v_b \\hat{{y}}_{{p,w}} \\right) - \\text{{Cost}}(w) - \\text{{Penalties}}(w) \\right)$$

Where:
- $x_{{p,w}} \\in \\{{0, 1\\}}$: Starting lineup indicator (exactly 11 players, 1 GKP, 3–5 DEF, 2–5 MID, 1–3 FWD).
- $c_{{p,w}} \\in \\{{0, 1\\}}$: Captain indicator ($\\sum_p c_{{p,w}} = 1$, $c_{{p,w}} \\le x_{{p,w}}$).
- $b_{{p,w}} \\in \\{{0, 1\\}}$: Bench players ($v_b \\approx 0.10$ expected autosub weight).
- $\\text{{Cost}}(w)$: Transfer hit cost ($4.0$ pts per paid transfer above free transfer limit).

#### The 5 Strategic Variance Constraints (ADR 0061)
Because optimizers aggressively exploit uncalibrated variance (The Optimizer's Curse), unconstrained solves select fragile, rotation-prone assets. ADR 0061 embeds 5 linear constraints with continuous slack variables:

1. **Hit Friction Buffer**:
   $$\\text{{Penalty}}_{{\\text{{hit}}}}(w) = 1.8 \\cdot \\text{{PaidHits}}(w)$$
   Raises the effective hurdle for an immediate transfer hit from $4.0$ to $5.8$ projected points, eliminating speculative -4 point churn.
2. **Starter Expected Minutes Floor**:
   $$\\forall p \\in \\text{{Outfield Starters}}, \\quad xMins_{{p,w}} + s^{{\\text{{mins}}}}_{{p,w}} \\ge 65.0, \\quad s^{{\\text{{mins}}}}_{{p,w}} \\ge 0$$
   Objective penalty: $-10.0 \\cdot s^{{\\text{{mins}}}}_{{p,w}}$. Prevents fielding 50-minute high-upside wingers as core starters.
3. **First-Bench Cover Nailedness**:
   $$\\sum_{{p \\in \\text{{Squad}}}} \\mathbb{{I}}(xMins_{{p,w}} \\ge 65.0) + s^{{\\text{{bench}}}}_w \\ge 12, \\quad s^{{\\text{{bench}}}}_w \\ge 0$$
   Objective penalty: $-1.5 \\cdot s^{{\\text{{bench}}}}_w$. Ensures at least 1 bench outfielder is a guaranteed 65+ minute starter.
4. **Defensive Stack Limiter**:
   $$\\forall c \\in \\text{{Clubs}}, \\quad \\sum_{{p \\in \\text{{DEF}} \\cup \\text{{GKP}}, \\text{{club}}(p)=c}} x_{{p,w}} - s^{{\\text{{stack}}}}_{{c,w}} \\le 2, \\quad s^{{\\text{{stack}}}}_{{c,w}} \\ge 0$$
   Objective penalty: $-1.2 \\cdot s^{{\\text{{stack}}}}_{{c,w}}$. Prevents triple-defense correlation wipeouts on single match outcomes.
5. **Goalkeeper Transfer Friction**:
   $$-1.5\\text{{ pt objective penalty on any non-wildcard GKP transfer-in}}.$$
   Goalkeeper variance is dominated by Poisson save/CS noise; burning FTs on lateral GK moves is mathematically negative.

---

### 3. The Reformed Historical Promotion Gate (ADR 0064 Standards)

A Candidate must pass all criteria across both Development (2025–26, seeded with 2024–25) and Confirmation (2024–25, warm-seeded with 2023–24) seasons:

```python
# backtesting/promotion.py gate constants
BOOTSTRAP_DRAWS = {BOOTSTRAP_DRAWS:_}
BOOTSTRAP_BLOCK_GWS = {BOOTSTRAP_BLOCK_GWS}  # Non-wrapping Moving Block Bootstrap (L={BOOTSTRAP_BLOCK_GWS})
BOOTSTRAP_MIN_P = {BOOTSTRAP_MIN_P}  # Dev season threshold
CONFIRMATION_BOOTSTRAP_MIN_P = {CONFIRMATION_BOOTSTRAP_MIN_P}  # Warm-seeded confirmation threshold
POOLED_BOOTSTRAP_MIN_P = {POOLED_BOOTSTRAP_MIN_P}  # Pooled 2-season stratified threshold
CHURN_GUARDRAIL_TOL = {CHURN_GUARDRAIL_TOL}  # Max excess squad churn players/GW
```

#### Requirement 1: Constrained Legal Formation XI Primary Delta
Primary metric is **Constrained Legal Formation XI Regret** (`select_legal_formation_xi`), solved via HiGHS/scipy MILP enforcing:
- $\\le 3$ players per club.
- Starting XI budget cap: $B_{{\\text{{XI}}}} \\le £83.5\\text{{m}}$ ($835.0$ in FPL 0.1m units).
- Deterministic tie-breaking: `[pred DESC, cost ASC, id ASC]`.
- Combined Primary Delta: $\\bar{{\\Delta}} = \\overline{{\\text{{Regret}}}}_{{\\text{{champ}}}} - \\overline{{\\text{{Regret}}}}_{{\\text{{cand}}}} > 0.0$ pts/GW.

#### Requirement 2: Squad Churn Guardrail (Issue #169)
Rolling top-15 budget-feasible squad churn prevents models from generating thrashing lineups that degrade rolling MILP transfer plans:
$$\\text{{Churn}}_g = 15 - |\\mathcal{{S}}_g \\cap \\mathcal{{S}}_{{g-1}}|, \\quad \\overline{{\\text{{Churn}}}}_{{\\text{{cand}}}} \\le \\overline{{\\text{{Churn}}}}_{{\\text{{champ}}}} + {CHURN_GUARDRAIL_TOL:.2f} \\text{{ players/GW}}$$

#### Requirement 3: Non-Wrapping Moving Block Bootstrap & Pooled Stratified Gate (Issue #171)
Evaluates complete blocks of length $L={BOOTSTRAP_BLOCK_GWS}$ consecutive gameweeks (spanning 4–6 week fixture swings) with start indices $0 \\le s \\le n - L$, without boundary wrapping:
- Dev Season: $P_{{\\text{{dev}}}}(\\bar{{\\Delta}}^* > 0) \\ge {BOOTSTRAP_MIN_P:.2f}$
- Confirmation Season (warm-seeded): $P_{{\\text{{conf}}}}(\\bar{{\\Delta}}^* > 0) \\ge {CONFIRMATION_BOOTSTRAP_MIN_P:.2f}$
- Pooled 2-Season Stratified: $P_{{\\text{{pooled}}}}(\\bar{{\\Delta}}^* > 0) \\ge {POOLED_BOOTSTRAP_MIN_P:.2f}$

#### Requirement 4: $\\sqrt{{n_s}}$-Scaled Seasonal Segment Loss Floors (Issue #172)
Standardized to uniform stringency ($z \\approx -0.25 \\times \\text{{SE}}$):
- `cold_start` ($n=4$): $\\Delta_{{\\text{{cold\\_start}}}} \\ge -{COLD_START_PARITY_TOL:.2f}$ pts/GW (max $-{COLD_START_PARITY_TOL * 4:.2f}$ cumulative pt)
- `early_mid` ($n=15$): $\\Delta_{{\\text{{early\\_mid}}}} \\ge -{SEGMENT_REGRESSION_TOL:.2f}$ pts/GW (max $-{SEGMENT_REGRESSION_TOL * 15:.2f}$ cumulative pts)
- `late` ($n=19$): $\\Delta_{{\\text{{late}}}} \\ge -{LATE_SEGMENT_REGRESSION_TOL:.2f}$ pts/GW (max $-{LATE_SEGMENT_REGRESSION_TOL * 19:.2f}$ cumulative pts)
- Active in-season win: $\\max(\\Delta_{{\\text{{early\\_mid}}}}, \\Delta_{{\\text{{late}}}}) > 0.0$ pts/GW.

#### Requirement 5: Dual-Window Hard Safety Guardrails (Issue #170)
Evaluated across both full season (38 GWs) and active gameweeks $\\mathcal{{G}}_{{\\text{{active}}}} = \\{{g : \\max_i |\\hat{{y}}^{{\\text{{cand}}}}_{{i,g}} - \\hat{{y}}^{{\\text{{champ}}}}_{{i,g}}| > 10^{{-6}}\\}}$:
- **Playable Pool MAE**: $\\text{{MAE}}_{{\\text{{cand}}}} \\le \\text{{MAE}}_{{\\text{{champ}}}} \\times {mae_mult:.2f}$
- **Playable Pool Bias**: $|\\text{{Bias}}_{{\\text{{cand}}}}| \\le |\\text{{Bias}}_{{\\text{{champ}}}}| + {BIAS_ABS_TOL:.2f}$
- **Captaincy Regret**: $\\text{{CapRegret}}_{{\\text{{cand}}}} \\le \\text{{CapRegret}}_{{\\text{{champ}}}} + {CAPTAIN_REGRET_ABS_TOL:.2f}$ pts/GW
- **Minutes MAE**: $\\text{{xMinsMAE}}_{{\\text{{cand}}}} \\le \\text{{xMinsMAE}}_{{\\text{{champ}}}} \\times {mae_mult:.2f}$
- **Spearman Correlation**: $\\rho_{{\\text{{cand}}}} \\ge \\rho_{{\\text{{champ}}}} - {SPEARMAN_ABS_TOL:.3f}$

---

### 4. Verified Dead-Lever Archetypes (from {total_trials} Historical Trials)

| Archetype ID | Tested Hypotheses | Empirical Fate | Mathematical Cause of Failure |
|---|---|---|---|
| **ARCH-01** | Club 11-Man Mass Conservation ($\\sum p_{{\\text{{start}}}} = 11.0$) | Dev $\\Delta = -3.14 \\dots -4.13$, 0/3 segs. | Pep/Arteta squads rotate ~12.5 starting mass across competitions; forcing 11.0 starves elite assets while inflating unplayable bench fodder. |
| **ARCH-02** | In-Season Unregularized Ridge / Direct G/A Refits | Dev $\\Delta = -0.13 \\dots -1.41$, bias up. | Small-sample cameo hauls cause regression weights to fluctuate wildly; explodes out-of-sample prediction error. |
| **ARCH-03** | Relaxing Defender xG Shrinkage ($K < 2400$) | Dev $\\Delta = -0.39 \\dots -0.84$, 0/3 segs. | Defender attacking split-half reliability is $r \\approx 0.15$. Relaxing shrinkage causes optimizer to bench reliable mids for fluke-scoring center backs. |
| **ARCH-04** | Bonus Pool Saturation ($B_{{\\max}} \\in [1.2, 1.5]$) | Dev $\\Delta = -0.16 \\dots -0.38$, boot $P \\le 0.37$. | Cap compresses expected return of talisman forwards (Haaland/Salah), distorting captaincy allocation. |
| **ARCH-05** | Raw / Unshrunk Opponent Matchup Multipliers | Dev $\\Delta = -0.68$, Easy bias $+0.75$. | Jensen's inequality and over-dispersion cause multiplicative swings to drastically over-project returns in green fixtures. |
| **ARCH-06** | Static Schedule Congestion Logit Shifts (-0.20 logit) | Dev $+0.063$, Confirmation $-0.105$. | Flat shifts misclassify nailed stamina outliers (Bruno Fernandes, Saliba) who play 90 mins every 3 days without decay. |
| **ARCH-07** | Latent-Role HMM Participation Modeling | Dev $\\Delta = -0.90 \\dots -3.70$, 0/3 segs. | Discrete role transition matrices are noisy in 38-game samples; severe degradation of minutes MAE guardrails. |
| **ARCH-08** | Step-Function Early ML Activation (GW8–12) | Confirm $\\Delta = -2.28$, $P_{{\\text{{pooled}}}} = 0.000$. | Early ML without sufficient panel samples distorts captaincy allocation and causes catastrophic early-mid collapse. |
| **ARCH-09** | Transfer Churn / Price Velocity as DNP Hazard | Dev $\\Delta = -0.20 \\dots -1.34$. | Casual manager selling activity reflects lagged sentiment and fixture swings, not manager benching hazard. |
| **ARCH-10** | Teammate Absence Share Redistribution | Dev $\\Delta = -0.72 \\dots -2.28$. | Sidelined talisman volume is absorbed by tactical shape changes and lower team quality, not linearly captured by teammates. |
| **ARCH-11** | Empirical Bayes Yellow Card Rates / Multipliers | Dev $\\Delta = -0.20 \\dots -0.87$, 0/3 segs. | Booking noise degrades point discrimination without improving lineup selection. |
| **ARCH-12** | Defcon Over-Dispersion Mixtures & Beta-Binomial | Dev $\\Delta = -0.13 \\dots -1.22$, 0/3 segs. | Parametric mixture fitting on sparse defensive event counts introduces high estimation variance. |
| **ARCH-13** | Natural Rate Slope / Untrimmed Low-xG Calibration | Dev PASS $+0.355$, Conf FAIL $-0.449$. | Rate adjustments on elite assets fail to replicate out-of-sample across different seasonal scoring baselines. |

---

### 5. High-Priority Exploration Vectors (Grounded in Technical Feasibility)

Candidates are strongly encouraged to explore mechanisms within these unreserved design spaces:
1. **Continuous Match-Pace & Transition Threat Elasticity ($M_{{\\text{{events}}}}$)**:
   - Trailing game-state margins and opponent match-tempo significantly alter shot generation, counter-attack frequency, and defensive block depth. Modeling continuous scoreline pace elasticity conditioned on game-state expectation without static logit shifts.
2. **Dynamic Defensive Block Depth & Tackles Demand ($M_{{\\text{{events}}}}$)**:
   - High-possession clubs suppress opponent tackle volume while conceding transition counters. Modeling possession-adjusted defensive contribution elasticity without inflating fluke clean sheets.
3. **Continuous Teammate Tactical Synergy & Space Creation ($M_{{\\text{{events}}}}$)**:
   - Gravity of talisman creators opens space for secondary runners. Modeling synergy effects without zero-sum talisman absence redistribution.
4. **Position-Conditioned Micro-Cycle Fatigue Recovery ($M_{{\\text{{mins}}}}$)**:
   - Nailed outfielders face non-linear stamina decay across dense 3-day fixture turnarounds. Modeling continuous exponential recovery dynamics rather than discrete static logit congestion penalties.
5. **Budget Enabler Efficiency & Marginal Value Modeling ($M_{{\\text{{events}}}} / M_{{\\text{{mins}}}}$ under £83.5m cap)**:
   - The £83.5m starting budget cap elevates the importance of accurate projections for £4.5m–£5.5m outfield starters. Models that eliminate residual bias and accurately rank budget enablers gain substantial legal formation XI points over models tuned solely for premium assets.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate point-in-time candidate ideation prompt.")
    parser.add_argument(
        "--focus",
        choices=["general", "minutes", "events", "assists", "goalkeepers", "budget-enablers"],
        default="general",
        help="Subsystem focus area for targeted ideation.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output path for prompt brief markdown.",
    )
    args = parser.parse_args()

    content = build_prompt_markdown(args.focus)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(content, encoding="utf-8")
    print(f"Candidate ideation prompt generated at: {args.out} (focus: {args.focus})")


if __name__ == "__main__":
    main()
