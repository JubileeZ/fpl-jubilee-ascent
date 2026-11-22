"""Tests for sparse Champion confirmation calibration, parity, and certification."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from scipy import stats


def test_preregistration_manifest_pins_seeds_budgets_and_canonical_digest() -> None:
    from backtesting.promotion_evidence import MILP_SEGMENT_REGRESSION_TOLERANCES
    from backtesting.sparse_certification import (
        CERTIFICATION_SEED,
        DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT,
        DEFAULT_FPL_DELTA_SD_PER_GW,
        DEFAULT_NUM_SIMULATIONS,
        FALLBACK_ADVISORY_SEED,
        TUNING_SEED,
        build_preregistration_manifest,
        compute_canonical_digest,
    )

    manifest = build_preregistration_manifest()
    assert manifest["manifest_version"] == 2
    assert manifest["protocol_target_version"] == "v2.0"
    assert manifest["tuning_seed"] == TUNING_SEED == 21101
    assert manifest["certification_seed"] == CERTIFICATION_SEED == 21102
    assert manifest["fallback_seed"] == FALLBACK_ADVISORY_SEED == 21103
    assert manifest["num_simulations"] == DEFAULT_NUM_SIMULATIONS == 20_000
    assert DEFAULT_FPL_DELTA_SD_PER_GW == pytest.approx(8.5)
    assert DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT == pytest.approx(4.0 * MILP_SEGMENT_REGRESSION_TOLERANCES["cold_start"])
    assert DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT == pytest.approx(35.6)
    assert manifest["retry_budget"]["primary_max_retries"] == 0
    assert manifest["retry_budget"]["fallback_max_retries"] == 1
    assert manifest["acceptance_rules"]["max_false_full_pass_upper_95"] == pytest.approx(0.05)
    assert manifest["acceptance_rules"]["min_primary_gw38_power_lower_95"] == pytest.approx(1.0 / 3.0)
    assert manifest["acceptance_rules"]["max_statistical_false_exclusion_upper_95"] == pytest.approx(0.05)
    assert len(manifest["scenario_grid"]) >= 24

    body = {k: v for k, v in manifest.items() if k != "manifest_digest"}
    assert manifest["manifest_digest"] == compute_canonical_digest(body)
    assert len(manifest["manifest_digest"]) == 64

    # Deterministic across repeated calls
    assert manifest == build_preregistration_manifest()


def test_synthetic_path_generator_dependence_shocks_tails_and_ranks() -> None:
    from backtesting.sparse_certification import (
        DEFAULT_FPL_DELTA_SD_PER_GW,
        EMPIRICAL_GW_VARIANCE_PROFILE,
        ScenarioSpec,
        generate_synthetic_paths,
    )

    mild_m2 = ScenarioSpec(
        scenario_id="test_m2_mixed",
        category="mixed_null",
        slate_size=2,
        finalist_effects_sd=(0.40, 0.0),
        dependence_regime="mild",
        phi_ar=0.20,
        rho_champ=0.50,
        innovation_dist="gaussian",
        shock_gws=(15, 19, 30, 34),
        shock_multiplier=1.50,
        safeguards_pass_from_gw=15,
    )
    a = generate_synthetic_paths(mild_m2, num_simulations=3000, seed=1234)
    b = generate_synthetic_paths(mild_m2, num_simulations=3000, seed=1234)
    c = generate_synthetic_paths(mild_m2, num_simulations=3000, seed=1235)
    assert a.shape == (3000, 2, 38)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)

    # Check rank means (+0.40 SD * DEFAULT_FPL_DELTA_SD_PER_GW vs 0.0 pts/GW)
    assert float(a[:, 0, :].mean()) == pytest.approx(0.40 * DEFAULT_FPL_DELTA_SD_PER_GW, abs=0.25)
    assert float(a[:, 1, :].mean()) == pytest.approx(0.0, abs=0.25)

    # Fixed pts/yr + locked-GW1/GW2 empirical profile remain decoupled from fpl_delta_sd_per_gw
    emp_fixed = ScenarioSpec(
        scenario_id="test_emp_fixed",
        category="power",
        slate_size=1,
        finalist_effects_sd=(0.0,),
        finalist_effects_pts_per_year=(60.0,),
        gw_variance_profile=EMPIRICAL_GW_VARIANCE_PROFILE,
        dependence_regime="mild",
        phi_ar=0.10,
        rho_champ=0.50,
        innovation_dist="gaussian",
    )
    p_low_sd = generate_synthetic_paths(emp_fixed, num_simulations=4000, seed=2468, fpl_delta_sd_per_gw=4.0)
    p_hi_sd = generate_synthetic_paths(emp_fixed, num_simulations=4000, seed=2468, fpl_delta_sd_per_gw=11.0)
    assert np.all(p_low_sd[:, 0, :2] == 0.0)
    assert np.all(p_hi_sd[:, 0, :2] == 0.0)
    assert float(p_low_sd[:, 0, :].sum(axis=1).mean()) == pytest.approx(60.0, abs=1.5)
    assert float(p_hi_sd[:, 0, :].sum(axis=1).mean()) == pytest.approx(60.0, abs=3.0)

    gw14_fixed = ScenarioSpec(
        scenario_id="test_gw14_fixed",
        category="harmful",
        slate_size=1,
        finalist_effects_sd=(0.0,),
        gw1_4_effects_pts_total=(-40.0,),
        dependence_regime="mild",
        phi_ar=0.10,
        rho_champ=0.50,
        innovation_dist="gaussian",
    )
    g4_a = generate_synthetic_paths(gw14_fixed, num_simulations=4000, seed=1357, fpl_delta_sd_per_gw=4.0)
    g4_b = generate_synthetic_paths(gw14_fixed, num_simulations=4000, seed=1357, fpl_delta_sd_per_gw=11.0)
    assert float(g4_a[:, 0, :4].sum(axis=1).mean()) == pytest.approx(-40.0, abs=0.5)
    assert float(g4_b[:, 0, :4].sum(axis=1).mean()) == pytest.approx(-40.0, abs=1.5)

    # Check shared-Champion cross-finalist correlation on non-shock weeks (~rho_champ=0.50)
    corr = float(np.corrcoef(a[:, 0, 5], a[:, 1, 5])[0, 1])
    assert corr == pytest.approx(0.50, abs=0.06)

    # Check elevated dispersion on scheduled shock week (GW15 -> idx 14) vs non-shock week (GW10 -> idx 9)
    assert float(np.std(a[:, 0, 14])) > float(np.std(a[:, 0, 9])) * 1.15

    # Persistent Student-t(5) exhibits higher excess kurtosis & AR(1) lag-1 correlation
    pers_m1 = ScenarioSpec(
        scenario_id="test_m1_pers",
        category="null",
        slate_size=1,
        finalist_effects_sd=(0.0,),
        dependence_regime="persistent",
        phi_ar=0.55,
        rho_champ=0.50,
        innovation_dist="student_t5",
        shock_gws=(15, 19, 30, 34),
        shock_multiplier=2.00,
        safeguards_pass_from_gw=15,
    )
    p = generate_synthetic_paths(pers_m1, num_simulations=4000, seed=5678)
    assert p.shape == (4000, 1, 38)
    lag1 = float(np.corrcoef(p[:, 0, 5], p[:, 0, 6])[0, 1])
    assert lag1 == pytest.approx(0.55, abs=0.06)
    kurt = float(stats.kurtosis(p[:, 0, 6]))
    gauss_kurt = float(stats.kurtosis(a[:, 0, 6]))
    assert kurt > 0.3
    assert kurt > gauss_kurt + 0.3


def test_tune_enforced_gw1_4_limit_fails_closed_when_unsatisfied() -> None:
    from backtesting.sparse_certification import tune_enforced_gw1_4_limit

    extreme_losses = [np.full(200, -500.0, dtype=float)]
    with pytest.raises(RuntimeError, match="Failed to find enforced gw1_4_material_loss_limit"):
        tune_enforced_gw1_4_limit(extreme_losses, num_simulations=200, fpl_delta_sd_per_gw=8.5)


def test_vectorized_vs_scalar_parity_exceeds_500_prefixes_within_1e_10() -> None:
    from backtesting.sparse_certification import verify_vectorized_vs_scalar_parity

    report = verify_vectorized_vs_scalar_parity(num_prefixes=520, seed=999)
    assert report["num_prefixes_checked"] >= 500
    assert report["max_abs_numeric_diff"] <= 1e-10
    assert report["binary_agreement_rate"] == 1.0
    assert report["passed"] is True


def test_clopper_pearson_one_sided_95_bounds_exact() -> None:
    from backtesting.sparse_certification import clopper_pearson_one_sided_95

    b_zero = clopper_pearson_one_sided_95(0, 20_000)
    assert b_zero["k"] == 0
    assert b_zero["n"] == 20_000
    assert b_zero["lower_95"] == 0.0
    assert b_zero["upper_95"] == pytest.approx(1.0 - 0.05 ** (1.0 / 20_000), abs=1e-12)

    b_all = clopper_pearson_one_sided_95(50, 50)
    assert b_all["upper_95"] == 1.0
    assert b_all["lower_95"] == pytest.approx(0.05 ** (1.0 / 50), abs=1e-12)

    b_mid = clopper_pearson_one_sided_95(7000, 20_000)
    assert math.isclose(b_mid["lower_95"], float(stats.beta.ppf(0.05, 7000, 20_000 - 7000 + 1)), abs_tol=1e-12)
    assert math.isclose(b_mid["upper_95"], float(stats.beta.ppf(0.95, 7000 + 1, 20_000 - 7000)), abs_tol=1e-12)


def test_tuning_and_heldout_certification_fallback_state_machine() -> None:
    from backtesting.sparse_certification import (
        CERTIFICATION_SEED,
        FALLBACK_ADVISORY_SEED,
        TUNING_SEED,
        certify_sparse_confirmation,
        tune_sparse_protocol,
    )

    tuned = tune_sparse_protocol(num_simulations=400, seed=TUNING_SEED)
    assert tuned["tuning_seed"] == TUNING_SEED
    assert set(tuned["calibrated_superiority_alphas"]) == {"1", "2"}
    for m_key in ("1", "2"):
        assert set(tuned["calibrated_superiority_alphas"][m_key]) == {"15", "30", "38"}
        assert all(0.0 < v < 0.05 for v in tuned["calibrated_superiority_alphas"][m_key].values())
    assert tuned["gw1_4_material_loss_limit"] > 0.0

    # Full certification state machine with small N for fast test: runs TUNING -> CERTIFICATION, and FALLBACK only if needed
    result = certify_sparse_confirmation(num_simulations=400)
    assert result["tuning"]["tuning_seed"] == TUNING_SEED
    assert result["primary_run"]["seed"] == CERTIFICATION_SEED
    assert result["primary_run"]["statistical_early_harm_mode"] == "enforced"
    assert len(result["primary_run"]["scenarios"]) >= 24

    gates = result["primary_run"]["gates"]
    if gates["false_full_pass_ok"] and gates["primary_gw38_power_ok"] and not gates["statistical_false_exclusion_ok"]:
        assert result["fallback_run"] is not None
        assert result["fallback_run"]["seed"] == FALLBACK_ADVISORY_SEED
        assert result["fallback_run"]["statistical_early_harm_mode"] == "advisory"
        assert result["retries_used"] == 1
    elif not (gates["false_full_pass_ok"] and gates["primary_gw38_power_ok"]):
        # Fallback MUST NOT run if false-promotion or GW38 power failed on primary
        assert result["fallback_run"] is None
        assert result["certified"] is False
        assert result["retries_used"] == 0
    else:
        assert result["fallback_run"] is None
        assert result["certified"] is True
        assert result["retries_used"] == 0


def test_fallback_blocked_when_primary_power_or_fwer_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from backtesting import sparse_certification as sc

    called_seeds: list[int] = []

    def fake_tune(**kwargs: object) -> dict[str, object]:
        return {
            "tuning_seed": sc.TUNING_SEED,
            "num_simulations": 100,
            "fpl_delta_sd_per_gw": sc.DEFAULT_FPL_DELTA_SD_PER_GW,
            "gw1_4_material_loss_limit": sc.DEFAULT_ADVISORY_GW1_4_LOSS_LIMIT,
            "calibrated_superiority_alphas": {
                "1": {"15": 0.0004, "30": 0.008, "38": 0.032},
                "2": {"15": 0.0002, "30": 0.004, "38": 0.016},
            },
            "m1_scale_factor": 0.8,
            "m2_scale_factor": 0.8,
        }

    def fake_suite(*, seed: int, statistical_early_harm_mode: str, **kwargs: object) -> dict[str, object]:
        called_seeds.append(seed)
        return {
            "seed": seed,
            "statistical_early_harm_mode": statistical_early_harm_mode,
            "num_simulations": 100,
            "scenarios": [],
            "gates": {
                "false_full_pass_ok": False,  # Primary FWER failed!
                "primary_gw38_power_ok": True,
                "statistical_false_exclusion_ok": False,
                "terminal_false_exclusion_ok": False,
                "all_passed": False,
            },
        }

    monkeypatch.setattr(sc, "tune_sparse_protocol", fake_tune)
    monkeypatch.setattr(sc, "run_certification_suite", fake_suite)

    res = sc.certify_sparse_confirmation(num_simulations=100)
    assert called_seeds == [sc.CERTIFICATION_SEED]  # Never touched fallback seed when FWER failed!
    assert res["fallback_run"] is None
    assert res["certified"] is False
    assert res["live_adoption_blocked"] is True
    assert res["retries_used"] == 0


def test_certify_sparse_confirmation_cli_writes_companion_artifacts(tmp_path: Path) -> None:
    from commands.certify_sparse_confirmation import main

    out_dir = tmp_path / "cert-out"
    main(["--n-sims", "300", "--output-dir", str(out_dir)])

    expected_files = (
        "preregistration_manifest.json",
        "parity_check.json",
        "certification_summary.csv",
        "certification_result.json",
        "sparse-confirmation-certification.md",
    )
    for name in expected_files:
        path = out_dir / name
        assert path.is_file(), f"Missing output artifact {name}"
        assert path.stat().st_size > 0

    from backtesting.promotion_evidence import MANDATORY_GUARDS
    from backtesting.sparse_certification import build_certified_protocol_config, verify_certification_artifacts

    direct_cfg = build_certified_protocol_config(
        calibrated_superiority_alphas={"1": {"15": 0.0001, "30": 0.002, "38": 0.025}, "2": {"15": 0.00005, "30": 0.001, "38": 0.01}},
        gw1_4_material_loss_limit=35.6,
        statistical_early_harm_mode="advisory",
        certification_digest="c" * 64,
    )
    assert direct_cfg.development_season == "2025-26"
    assert direct_cfg.confirmation_season == "2026-27"
    assert direct_cfg.required_projection_guards == tuple(sorted(MANDATORY_GUARDS))
    assert direct_cfg.completed_segments is not None
    assert set(direct_cfg.completed_segments) == {"15", "30", "38"}

    payload = json.loads((out_dir / "certification_result.json").read_text(encoding="utf-8"))
    assert "parity_passed" in payload
    if payload["certified"]:
        diag_csv = out_dir / "empirical_power_diagnostics.csv"
        assert diag_csv.is_file() and diag_csv.stat().st_size > 0
        cfg = payload["certified_protocol_config"]
        assert cfg["development_season"] == "2025-26"
        assert cfg["confirmation_season"] == "2026-27"
        assert tuple(cfg["required_projection_guards"]) == tuple(sorted(MANDATORY_GUARDS))
        assert set(cfg["completed_segments"]) == {"15", "30", "38"}
        decl = payload["evaluation_protocol_v2_declaration"]
        assert decl["windows"][0]["season"] == "2026-27"
        assert payload["empirical_power_diagnostics"] is not None
        ver = verify_certification_artifacts(out_dir, expected_digest=payload["certification_digest"])
        assert ver["passed"] is True
        assert ver["evaluator_revisions_match"] is True

    note = (out_dir / "sparse-confirmation-certification.md").read_text(encoding="utf-8")
    metrics_section = note.split("## Project interpretation")[0]
    assert "`statistical_false_exclusion_flag_upper95`" in metrics_section
    for metric_col in ("gw15_power", "gw30_power", "single_season_gw38_power", "two_season_76gw_power"):
        assert metric_col in metrics_section


def test_verify_certification_artifacts_passes_repo_and_detects_drift_and_tamper(tmp_path: Path) -> None:
    from backtesting.promotion_evidence import statistical_protocol_config_from_dict
    from backtesting.sparse_certification import verify_certification_artifacts
    from commands.manage_champion_adoption import CERTIFICATION_DIGEST_EXPECTED

    missing_ver = verify_certification_artifacts(tmp_path / "missing_cert_dir")
    assert missing_ver["passed"] is False
    assert missing_ver["statistical_protocol_hash"] is None

    repo_cert_dir = Path("docs/research/sparse-confirmation-certification")
    repo_ver = verify_certification_artifacts(repo_cert_dir, expected_digest=CERTIFICATION_DIGEST_EXPECTED)
    assert repo_ver["passed"] is True
    assert repo_ver["manifest_digest_match"] is True
    assert repo_ver["canonical_digest_match"] is True
    assert repo_ver["evaluator_revisions_match"] is True

    # Copy to tmp_path and inject evaluator_revisions drift
    copy_dir = tmp_path / "cert"
    copy_dir.mkdir()
    for fname in ("certification_result.json", "preregistration_manifest.json"):
        (copy_dir / fname).write_bytes((repo_cert_dir / fname).read_bytes())

    manifest = json.loads((copy_dir / "preregistration_manifest.json").read_text(encoding="utf-8"))
    manifest["evaluator_revisions"]["backtesting/sparse_certification.py"] = "0" * 64
    (copy_dir / "preregistration_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    drift_ver = verify_certification_artifacts(copy_dir, expected_digest=CERTIFICATION_DIGEST_EXPECTED)
    assert drift_ver["passed"] is False
    assert drift_ver["manifest_digest_match"] is False
    assert drift_ver["evaluator_revisions_match"] is False
    assert "backtesting/sparse_certification.py" in drift_ver["drifted_files"]

    # Tampered certification_digest fails canonical check
    (copy_dir / "preregistration_manifest.json").write_bytes((repo_cert_dir / "preregistration_manifest.json").read_bytes())
    cert_res = json.loads((copy_dir / "certification_result.json").read_text(encoding="utf-8"))
    cert_res["certification_digest"] = "f" * 64
    (copy_dir / "certification_result.json").write_text(json.dumps(cert_res), encoding="utf-8")
    tamper_ver = verify_certification_artifacts(copy_dir)
    assert tamper_ver["passed"] is False
    assert tamper_ver["canonical_digest_match"] is False

    # Tampered certified_protocol_config fails even when statistical_protocol_hash is recomputed
    cert_res = json.loads((repo_cert_dir / "certification_result.json").read_text(encoding="utf-8"))
    cert_res["certified_protocol_config"]["gw1_4_material_loss_limit"] = 99.0
    cert_res["statistical_protocol_hash"] = statistical_protocol_config_from_dict(
        cert_res["certified_protocol_config"]
    ).compute_hash()
    (copy_dir / "certification_result.json").write_text(json.dumps(cert_res), encoding="utf-8")
    cfg_tamper_ver = verify_certification_artifacts(copy_dir, expected_digest=CERTIFICATION_DIGEST_EXPECTED)
    assert cfg_tamper_ver["passed"] is False
    assert any("certified_protocol_config mismatch" in err for err in cfg_tamper_ver["errors"])

