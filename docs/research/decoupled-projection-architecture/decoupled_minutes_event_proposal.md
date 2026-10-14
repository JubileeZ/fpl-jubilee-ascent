# Decoupled Projection Architecture: Separating Minutes & Event Rates

**Document version**: 1.0.0  
**Updated**: 2026-10-14  
**Status**: Architectural Proposal & Feasibility Blueprint  
**Purpose**: Detailed design for decoupling Minutes Projection from Event Rate Projection, enabling independent modeling, dedicated evaluation gates, and composable promotion.

---

## 1. Executive Summary & Core Feasibility

### User Question
> *"Can we separate Minutes projection and Event projection? I want to separate event projection if we know the minutes for sure to see if it is accurate, and use a separate model to project minutes with separate models and gates. Can we do that?"*

### Direct Answer
**Yes, absolutely.** Not only is it feasible, but **it is the statistically correct architecture** for fantasy sports forecasting. 

In fact, preliminary evidence in this repository already proved this separation is overwhelmingly advantageous:
- In the October 2026 research diagnostic (`docs/research/multi-component-ladder/multi-component-ladder.md`), the team ran an **"Oracle Minutes Test"** (conditioning event predictions on actual match minutes played across GW1–6).
- **Result**: Model signed bias collapsed from **$-1.11$ pts down to $-0.08$ pts**, and correlation jumped by **$+52\%$** ($0.177 \to 0.270$).
- **Insight**: The underlying per-minute event engine (goals, assists, clean sheets, defensive contributions) is **already well-calibrated**. The primary source of prediction variance, signed bias, and false demotions during candidate research stems from **minutes uncertainty and participation misclassification**.

---

## 2. The Confounding Problem in Coupled Models

Currently, almost all candidate models in the repository evaluate total projected points $xP$, where:
$$xP = \mathbb{E}[\text{Points}] \approx \mathbb{E}[\text{Minutes}] \times \text{Rate}(\text{Events} \mid \text{Player, Opponent})$$

When an end-to-end model is evaluated on total points ($xP$ vs. Actual Points):
1. **Confounded Feedback**: If a candidate improves the assist GLM by $+15\%$ but mispredicts whether a winger starts in Gameweek 12, the entire candidate fails the Promotion Gate. The researcher falsely concludes that the assist GLM failed.
2. **Optimizer's Curse on Minutes**: A player projected for 85 minutes who actually plays 12 minutes receives massive regret, penalizing the lineup optimizer even if their per-minute scoring rate was spot on.
3. **Research Deadlock**: As seen in the Candidate Ledger, 29+ ideas across defensive and attacking rates were rejected because end-to-end Formation Regret was dragged down by minutes noise.

---

## 3. Decoupled System Architecture

```
                             ┌───────────────────────────────┐
                             │       Feature Contract        │
                             │  (Historical Match Features)  │
                             └──────────────┬────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
     ┌─────────────────────────────┐                 ┌─────────────────────────────┐
     │   Minutes Projection Model  │                 │      Event Rate Model       │
     │      M_mins (Player/Club)   │                 │     M_events (Matchup/Per90)│
     ├─────────────────────────────┤                 ├─────────────────────────────┤
     │ Predicts:                   │                 │ Predicts per 90 / per min:  │
     │ - P(DNP), P(Start), P(Sub)  │                 │ - Goal Expectancy (xG/90)   │
     │ - xMins|Start, xMins|Sub    │                 │ - Assist Expectancy (xA/90) │
     │ - P(60+ mins)               │                 │ - Goals Conceded (xGC/90)   │
     │ - Total Expected Minutes    │                 │ - Saves, Cards, Defcon      │
     └──────────────┬──────────────┘                 └──────────────┬──────────────┘
                    │                                               │
                    │         ┌───────────────────────────┐         │
                    └────────►│   Composite Scoring Engine│◄────────┘
                              │   (Exact Scoring Matrix)  │
                              └─────────────┬─────────────┘
                                            ▼
                              ┌───────────────────────────┐
                              │    Projection Contract    │
                              │(xP, xMins, 13 Components) │
                              └───────────────────────────┘
```

### Module 1: The Minutes Model ($M_{\text{mins}}$)
- **Responsibility**: Predict match participation and pitch duration.
- **Key Features**:
  - Availability news, injury flags, press conference status codes.
  - Historical start persistence (rolling 3-GW, 6-GW lags).
  - Club squad depth, bench competition, and managerial rotation tendencies.
  - Schedule congestion (days since prior kickoff, midweek European matches).
- **Outputs**:
  - Discrete states: $p_{\text{dnp}}, p_{\text{start}}, p_{\text{sub_in}}$ (where sum = 1.0).
  - Durations: $m_{\text{start}} \in [45, 90], m_{\text{sub}} \in [5, 35]$.
  - $P(60+\text{ mins}) \in [0.0, 1.0]$.
  - Expected scalar minutes: $\hat{m} = p_{\text{start}} m_{\text{start}} + p_{\text{sub}} m_{\text{sub}}$.

### Module 2: The Event Rate Model ($M_{\text{events}}$)
- **Responsibility**: Predict player productivity and defensive rates *conditioned on pitch duration*.
- **Key Features**:
  - Opponent defensive vulnerability (Matchup Share).
  - Player underlying talent (re-centered xG, xA, creativity, set-piece involvement).
  - Positional defensive baselines (clean sheet rate, tackles/interceptions).
- **Outputs**:
  - Pure rates per 90 minutes (or rate intensities $\lambda$ per minute), independent of whether the player plays 10 or 90 minutes.

### Module 3: Composite Scoring Engine
- Computes expected fantasy points through the mutually exclusive participation states:
  $$\mathbb{E}[\text{Points}] = p_{\text{start}} \cdot \text{Points}(M_{\text{events}} \mid m_{\text{start}}) + p_{\text{sub}} \cdot \text{Points}(M_{\text{events}} \mid m_{\text{sub}})$$
- Calculates appearance points directly: $p_{\text{start}} (1 + P(60+\mid \text{start})) + p_{\text{sub}} (1 + P(60+\mid \text{sub}))$.
- Populates the full 13-component `ProjectionContract`.

---

## 4. The Three-Tier Gating Framework

To make this operational, we establish **independent validation gates** for each module, plus an integrated gate for final promotion:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THREE-TIER GATING SYSTEM                        │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 1: MINUTES MODEL GATE (Standalone M_mins)                         │
│ - Evaluated on actual minutes and participation ground truth           │
│ - Primary: Minutes MAE & RMSE on playable pool                         │
│ - Classification: Brier Score on (p_dnp, p_start, p_sub)               │
│ - Decision capture: 60+ min classification precision/recall            │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 2: EVENT RATE GATE (Standalone M_events under Oracle Minutes)     │
│ - Evaluated on actual points given actual match minutes (m = actual)   │
│ - Primary: Oracle Formation XI Regret (Δ_oracle > 0)                   │
│ - Event accuracy: Poisson deviance & MSE share across 13 components    │
│ - Rate bias: Signed bias bounded within ±0.10 pts                      │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 3: INTEGRATED PROMOTION GATE (Composite Model)                    │
│ - Full walk-forward backtest on 2025-26 dev + 2024-25 confirmation     │
│ - Standard ADR 0054 Formation XI Regret (Δ > 0, Boot P ≥ 0.60)         │
│ - All 5 Champion guardrails must pass                                  │
└────────────────────────────────────────────────────────────────────────┘
```

### Gate A: Standalone Minutes Gate
When developing a new minutes model:
1. **Target**: `actual_minutes` from `player_performances.parquet`.
2. **Primary Metric**: Minutes MAE ($\downarrow$) on the active player pool:
   $$\text{MAE}_{\text{mins}} = \frac{1}{N} \sum | \hat{m}_i - m^{\text{actual}}_i |$$
3. **Classification Brier Score**:
   $$\text{Brier} = \frac{1}{N} \sum \left( (p_{\text{start}} - y_{\text{start}})^2 + (p_{\text{sub}} - y_{\text{sub}})^2 + (p_{\text{dnp}} - y_{\text{dnp}})^2 \right)$$
4. **Starter Discrimination (AUC / Precision-Recall)**: Ability to correctly separate $60+$ minute starters from sub/cameo players.
- **Promotion criterion for $M_{\text{mins}}$**: Statistically significant reduction in Minutes MAE and Brier score vs. Champion's minutes model without regressing starter recall.

### Gate B: Standalone Event Rate Gate (Oracle Minutes)
When developing a new scoring or event model (e.g. set pieces, finishing, clean sheet models):
1. **Method**: **Oracle Minutes Evaluation**. The backtesting harness injects the actual played minutes ($m_i = m^{\text{actual}}_i$) into `predict()`.
2. **Primary Metric**: **Oracle Formation XI Regret**:
   $$\Delta_{\text{oracle}} = \text{Regret}_{\text{Champ}}(\text{actual\_mins}) - \text{Regret}_{\text{Cand}}(\text{actual\_mins})$$
3. **Component MSE Share**: Verifies whether the candidate reduces error in specific components (e.g. `xp_goals`, `xp_assists`, `xp_clean_sheet`).
- **Promotion criterion for $M_{\text{events}}$**: Candidate event engine makes superior lineup selections when minutes are held constant ($\Delta_{\text{oracle}} > 0$).

### Gate C: Integrated Production Promotion Gate
Once a winning $M_{\text{mins}}$ or $M_{\text{events}}$ passes its component gate:
1. Pair it with the Champion counterpart to create a composite model.
2. Run standard walk-forward backtest via `commands.backtest` under ADR 0054.
3. Must satisfy:
   - Combined Formation Regret $\Delta > 0.0$.
   - Block Bootstrap $P(\Delta > 0) \ge 0.60$.
   - Segment wins $\ge 2/3$.
   - All 5 hard guardrails respected.

---

## 5. Existing Repository Seams & Implementation Path

The codebase is already partially prepared for this architecture:

1. **`external_xmins` in `features/builder.py`**:
   - Commit `371d9f7` added support for injecting external minutes via `df_feat["external_xmins"]`.
   - `ParticipationStateHybridModel.predict()` already contains logic to parse external minutes into participation states via `target_to_states()`.
2. **Seam to add**:
   - **`OracleMinutesBacktestRunner`**: A CLI / test flag in `backtesting/walkforward.py` (`--oracle-minutes`) that passes `df_perf["minutes"]` directly into `df_feat["external_xmins"]`.
   - **`BaseMinutesModel` and `BaseEventModel` interfaces**: Explicit Python protocol/abstract base classes allowing plug-and-play swapping of minutes and rate engines.
