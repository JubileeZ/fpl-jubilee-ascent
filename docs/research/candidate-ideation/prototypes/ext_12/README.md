# EXT-12: Sequential Attacking Opportunity Change Detection

Implementation and verification of sequential attacking opportunity change detection prototypes.
Fixed grid:
- `ext_12_h48_phi05`: `change_hazard=0.0208333333, dispersion=0.5`
- `ext_12_h48_phi10`: `change_hazard=0.0208333333, dispersion=1.0`
- `ext_12_h24_phi05`: `change_hazard=0.0416666667, dispersion=0.5`
- `ext_12_h24_phi10`: `change_hazard=0.0416666667, dispersion=1.0`

Audit and checks:
- `uv run python .agents/skills/explore-candidate/smoke.py docs/research/candidate-ideation/prototypes/ext_12/prototypes.py --audit_only`: PASS
- `uv run python docs/research/candidate-ideation/prototypes/ext_12/checks.py`: PASS
