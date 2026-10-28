"""Adaptive LOO Assist Challenger Model (Track A ablation winner vs def_xg_shrink_challenger).

Isolates Group B (calibrated leave-one-out teammate assist finishing) from AdaptiveCausalChallengerModel,
disabling all minutes ML heads (H1, H3) and goals ML (Group A) to avoid over-inflation and short-turnaround
regressions under the ADR 0064 £83.5m Constrained Formation XI gate.
"""

from __future__ import annotations

from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel


class AdaptiveAssistsChallengerModel(AdaptiveCausalChallengerModel):
    """Adaptive Causal ML Challenger with Group B assists ML only (H1, H2, H3, goals disabled)."""

    def __init__(self, *, min_ml_gw: int = 20, ramp_span: float = 5.0) -> None:
        super().__init__(
            min_ml_gw=min_ml_gw,
            ramp_span=ramp_span,
            enable_mins_h1=False,
            enable_mins_h2=False,
            enable_mins_h3=False,
            enable_goals=False,
            enable_assists=True,
            enable_defense=False,
            enable_bonus=False,
        )

    @property
    def name(self) -> str:
        return "adaptive_assists_challenger"
