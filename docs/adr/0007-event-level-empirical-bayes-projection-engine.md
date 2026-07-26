# 0007: Statistical Overhaul of Projection Engine (Event-Level Empirical Bayes)

## Context

The initial `metrics_component_hybrid` baseline backtest over GW1–38 exhibited a severe positive point bias (+1.8220) and non-positive rank correlation (-0.0023). Unweighted OLS per-90 rate fitting inflated sparse low-minute estimates, continuous sigmoid minutes distorted substitution vs starting risk, and pure Poisson goal conceded assumptions under-predicted multi-goal penalties.

## Decision

We update `metrics_component_hybrid` and `features/builder.py` with an event-level statistical overhaul:

1. **xMins Mixture & Starter Mins Shrinkage**: Replace continuous sigmoid curve with a 2-state starter/sub mixture model. Expected starting minutes shrink toward the position/league average ($E_{\text{league}} = 78.0$) via dynamic weight $w_{\text{ind}} = \frac{N_{\text{starts}}}{N_{\text{starts}} + 4}$.
2. **Two-Stage Empirical Bayes Attacking GLM**: Replace per-90 OLS with a two-stage event-level GLM using offset $\log(\text{mins} / 90)$ across fixture rows. Stage 1 estimates league-wide $(\beta_{\text{xG}}, \beta_{\text{Threat}})$, and Stage 2 applies Empirical Bayes shrinkage $u_i = \frac{N_i}{N_i + 15} \cdot \bar{r}_i$ to player residual conversion rates.
3. **Defcon Pearson Dispersion Diagnostics**: Measure Pearson chi-square dispersion ratio $\hat{\phi}$ on defensive action residuals to dynamically select between Poisson ($0.85 \le \hat{\phi} \le 1.15$), Negative Binomial ($\hat{\phi} > 1.15$), and quasi-Poisson ($\hat{\phi} < 0.85$).
4. **Minutes-Aware Team Defensive Model**: Model goals conceded as a team-level defensive event from opponent attack expectations $\lambda_{\text{team}}$. Scale individual player exposure via $\lambda_{\text{player}} = \lambda_{\text{team}} \cdot \left(\frac{\text{mins}}{90}\right)$ for Negative Binomial conceded penalties $NB(\lambda_{\text{player}}, r=3.0)$ and clean sheet eligibility $P(\text{CS}) = P(\text{start}) \cdot P(\ge 60\text{m} \mid \text{start}) \cdot NB(0; \lambda_{\text{start}}, r)$.
5. **Calibrated Bonus Tier Allocation**: Allocate all 6 match bonus points (+3, +2, +1) across eligible players ($\ge 45$ mins) using Softmax temperature $T = 6.0$.

## Consequences

- Systematic positive bias (+1.8220) is eliminated by overdispersed Negative Binomial conceded penalties.
- Short-appearance low-minute noise no longer skews attacking projections.
- Spearman rank correlation becomes positive and top-pick shortlist overlap improves.
