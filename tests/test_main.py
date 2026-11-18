"""Tests for QuantumMeasurement-Lab: POVM, Neumark, pointer, weak values."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main as lab


# ---------------- POVM ----------------

def test_povm_sums_to_identity():
    total = lab.trine_povm()[0]
    for e in lab.trine_povm()[1:]:
        total = lab.madd(total, e)
    for i in range(2):
        for j in range(2):
            assert abs(total[i][j] - lab.eye(2)[i][j]) < 1e-12


def test_povm_elements_positive_rank_one():
    for e in lab.trine_povm():
        hi, lo = lab.eigvals_hermitian_2x2(e)
        assert abs(hi - 2 / 3) < 1e-12
        assert abs(lo) < 1e-12


def test_povm_probabilities_ground_state():
    probs = lab.povm_probabilities(lab.ket(1, 0))
    assert probs == [2 / 3, 1 / 6, 1 / 6] or all(
        abs(a - b) < 1e-12 for a, b in zip(probs, (2 / 3, 1 / 6, 1 / 6)))


def test_povm_probabilities_normalised():
    for state in lab.neumark_test_states():
        assert abs(sum(lab.povm_probabilities(state)) - 1.0) < 1e-12


def test_povm_discrimination_two_thirds():
    report = lab.povm_discrimination()
    assert abs(report["success"] - 2 / 3) < 1e-12
    assert abs(report["error"] - 1 / 3) < 1e-12


def test_projective_aligned_strategy():
    report = lab.projective_discrimination()
    assert abs(report["aligned_basis_strategy_success"] - 7 / 12) < 1e-9


def test_projective_scan_between_aligned_and_povm():
    report = lab.projective_discrimination()
    assert report["best_scan_success"] > 0.62
    assert report["best_scan_success"] < 2 / 3


# ---------------- Neumark ----------------

def test_neumark_isometry():
    W = lab.neumark_isometry()
    wdw = lab.mmul(lab.dagger(W), W)
    for i in range(2):
        for j in range(2):
            assert abs(wdw[i][j] - lab.eye(2)[i][j]) < 1e-12


def test_neumark_unitary():
    U = lab.neumark_unitary()
    udu = lab.mmul(lab.dagger(U), U)
    for i in range(4):
        for j in range(4):
            assert abs(udu[i][j] - lab.eye(4)[i][j]) < 1e-12


def test_neumark_statistics_match():
    for state in lab.neumark_test_states():
        pv = lab.povm_probabilities(state)
        nv = lab.neumark_probabilities(state)
        for k in range(3):
            assert abs(pv[k] - nv[k]) < 1e-9
        assert nv[3] < 1e-12


# ---------------- pointer / tradeoff ----------------

def test_pointer_normalised():
    amp = lab.pointer_state(0.7)
    assert abs(sum(abs(t) ** 2 for t in amp) * lab.GRID_STEP - 1.0) < 1e-9


def test_overlap_matches_analytic():
    for g in (0.25, 0.5, 1.0, 2.0, 3.0):
        assert abs(lab.pointer_overlap(g)
                   - lab.pointer_overlap_analytic(g)) < 1e-6


def test_readout_success_zero_and_cdf():
    assert abs(lab.readout_success(0.0) - 0.5) < 1e-9
    for g in (0.5, 1.0, 2.0):
        cdf = 0.5 * (1 + math.erf(g / math.sqrt(2)))
        assert abs(lab.readout_success(g) - cdf) < 0.005


def test_information_endpoints():
    assert abs(lab.information_bits(0.0)) < 1e-9
    assert lab.information_bits(3.0) > 0.98


def test_fidelity_identity():
    for g in (0.5, 1.0, 2.0):
        assert abs(lab.fidelity_kept(g)
                   - (1 + lab.pointer_overlap(g)) / 2) < 1e-9


def test_tradeoff_monotone():
    rows = lab.tradeoff_table()
    for a, b in zip(rows, rows[1:]):
        assert a["pointer_overlap"] > b["pointer_overlap"]
        assert a["fidelity_kept"] > b["fidelity_kept"]
        assert a["information_bits"] < b["information_bits"]


# ---------------- weak values ----------------

def test_weak_value_controls():
    assert abs(lab.weak_value(lab.ket(1, 0)) - 1.0) < 1e-12
    assert abs(lab.weak_value(lab.PRE_STATE)) < 1e-12


def test_weak_value_orthogonal_undefined():
    minus = lab.ket(1 / math.sqrt(2), -1 / math.sqrt(2))
    assert lab.weak_value(minus) is None
    assert lab.postselection_probability(minus) < 1e-15


def test_weak_value_anomalous():
    wv = lab.weak_value(lab.post_state())
    assert abs(wv - 21.0) < 1e-9
    assert abs(wv) > 1.0  # outside the eigenvalue range [-1, 1]
    assert abs(lab.postselection_probability(lab.post_state())
               - 0.002262) < 1e-6


def test_pointer_sim_reproduces_weak_value():
    mean, prob = lab.postselected_pointer(0.01, lab.post_state())
    assert abs(mean / 0.01 - 21.0) < 0.35
    exact = lab.postselection_probability(lab.post_state())
    assert abs(prob - exact) / exact < 0.03


def test_pointer_sim_convergence():
    errs = [abs(lab.postselected_pointer(g, lab.post_state())[0] / g - 21.0)
            for g in (0.05, 0.02, 0.01)]
    assert errs[2] < errs[1] < errs[0]


# ---------------- ledger ----------------

def test_ledger_endpoints():
    rows = lab.backaction_ledger()
    assert rows[0]["information_bits"] == 0.0
    assert rows[0]["fidelity_kept"] == 1.0
    assert abs(rows[-1]["information_bits"] - 1.0) < 1e-12
    assert abs(rows[-1]["fidelity_kept"] - 0.5) < 1e-12


def test_ledger_monotone():
    rows = lab.backaction_ledger()
    for a, b in zip(rows, rows[1:]):
        assert a["information_bits"] < b["information_bits"]
        assert a["fidelity_kept"] > b["fidelity_kept"]


# ---------------- classifier / gates / seats ----------------

def test_classifier_scenarios():
    rep = lab.classifier_report()
    assert rep["barely_coupled_g0.1_sigma1"] == "too-weak-to-read"
    assert rep["gentle_probe_g0.5_sigma1"] == "weak-informative"
    assert rep["balanced_probe_g1_sigma1"] == "weak-informative"
    assert rep["firm_probe_g2_sigma1"] == "projective-like"
    assert rep["overcoupled_g3_sigma1"] == "demolished"
    assert rep["narrow_pointer_g1_sigma0.25"] == "demolished"
    assert rep["wide_pointer_g2_sigma2"] == "weak-informative"


def test_classifier_matches_policy():
    for g, s in [(0.1, 1.0), (0.5, 1.0), (1.0, 1.0), (2.0, 1.0),
                 (3.0, 1.0), (1.0, 0.25), (2.0, 2.0)]:
        assert lab.classify_measurement(g, s) == lab.policy_label(g, s)


def test_hold_gates():
    assert len(lab.HOLD_GATES) == 14
    assert lab.gate("real_detector_control") == "HOLD"
    assert lab.gate("weak_value_as_eigenvalue_claim") == "HOLD"
    assert lab.gate("postselection_data_fabrication") == "HOLD"
    assert lab.gate("run_simulation") == "PROCEED"


def test_hold_demo_exit_code():
    assert lab.main(["hold-demo", "real_detector_control"]) == 2
    assert lab.main(["hold-demo", "run_simulation"]) == 0


def test_seats_never_override():
    brains = lab.brains_report()
    assert brains["decider"]["can_override_hold"] is False
    assert brains["decider"]["model_id"] == "gemini-argon-4"
    assert brains["advisor"]["can_override_hold"] is False
    assert brains["flow"]["rendered"] is False
    assert brains["flow"]["live"] == 0


def test_checks_all_pass():
    checks = lab.run_checks()
    assert all(ok for _, ok in checks), [n for n, ok in checks if not ok]


def test_demo_runs():
    assert lab.main(["demo"]) == 0
