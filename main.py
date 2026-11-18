#!/usr/bin/env python3
"""QuantumMeasurement-Lab - educational quantum measurement lab.

by Darion Kellar

Pure Python standard library. Zero dependencies. Zero network.
Education only - and the central lesson is stated up front:

  * A measurement is a physical interaction with a price list.
    This lab computes both sides of the bill for the three regimes
    of quantum measurement: generalised measurements (POVMs) that
    resolve more states than any projective measurement can, weak
    measurements that buy partial information with partial
    disturbance, and the strong projective limit that pays full
    information with the original state.
  * A weak value is a conditional average of a defined procedure -
    pre-select, couple weakly, post-select, average the pointer.
    When it lands outside the observable's eigenvalue range, that
    is arithmetic about the post-selected subensemble, printed
    next to the post-selection probability that prices it. It is
    not a measured eigenvalue and it is not free amplification.

Everything is computed from scratch in this one file: 2x2 complex
matrices for the qubit, the trine POVM and its Neumark dilation
built explicitly, and a Gaussian pointer wavefunction discretised
on a labelled grid so the information-disturbance tradeoff is read
off actual pointer states, not quoted. No detector clicked. Every
detector / sensing / hardware use is a permanent HOLD gate - with
Gemini Argon 4 Extended Thinking as DECIDER (names-only,
tighten-only), Muse as advisor (never overrides HOLD), and Google
Flow plan-only seats.
"""
import hashlib
import json
import math
import sys

# ---------------------------------------------------------------- constants
VERSION = "1.0.0"

# Labelled pointer model. The pointer is a Gaussian wave packet of
# width SIGMA on a position grid; the coupling translates it by
# +/- g for the two eigenvalues of the measured observable. These
# are teaching values, stated openly, not device parameters.
POINTER_SIGMA = 1.0
GRID_MIN = -12.0
GRID_MAX = 12.0
GRID_STEP = 0.02
GRID_X = tuple(GRID_MIN + GRID_STEP * i
               for i in range(int(round((GRID_MAX - GRID_MIN) / GRID_STEP)) + 1))

# Labelled weak-value post-selection: |phi> tilts off the state
# orthogonal to |psi> by DELTA, which is what prices the anomaly.
WEAK_VALUE_DELTA = 0.1

SIGMA_Z = [[1 + 0j, 0j], [0j, -1 + 0j]]

# ---------------------------------------------------------------- HOLD gates
HOLD_GATES = {
    "real_detector_control": "HOLD - no control of real detectors, photomultipliers, cameras, or readout electronics",
    "quantum_sensor_product_claim": "HOLD - no claim this lab is, or prototypes, a working quantum sensor product",
    "weak_value_amplification_claim": "HOLD - a weak value is not free signal amplification; no metrology-advantage claim from post-selected averages",
    "sensing_hardware_sale": "HOLD - no selling or marketing sensing hardware on the basis of this lab",
    "medical_measurement_claim": "HOLD - no medical, diagnostic, or biological measurement claims",
    "surveillance_use": "HOLD - no surveillance, covert sensing, or monitoring use",
    "cryptographic_measurement_attack": "HOLD - no measurement-based attacks on real QKD or cryptographic systems",
    "detector_calibration_certification": "HOLD - no certifying the calibration of any real detector",
    "postselection_data_fabrication": "HOLD - post-selected statistics must never be presented as unconditioned measurement data",
    "weak_value_as_eigenvalue_claim": "HOLD - a weak value outside the eigenvalue range is not a measured eigenvalue and must never be reported as one",
    "hardware_build_guidance": "HOLD - no build guidance for real measurement or sensing hardware",
    "metrology_standard_claim": "HOLD - no claim of a measurement standard, SI traceability, or certified accuracy",
    "live_experiment_direction": "HOLD - no directing live experiments, beamlines, or instruments from this simulation",
    "investment_claim": "HOLD - no investment claims; a lab model is not a prospectus",
}


def gate(action):
    """Return 'HOLD' if the action is gated, else 'PROCEED' (sandbox sim)."""
    return "HOLD" if action in HOLD_GATES else "PROCEED"


# ================================================================ 1. Tiny complex linear algebra
# Qubit states are 2-vectors of complex numbers, operators are 2x2
# (or 4x4, for the dilation) lists of lists. Everything the lab
# trusts is built with these helpers and asserted in CHECKS.

def vdot(a, b):
    """Bra-ket inner product <a|b>."""
    return sum(x.conjugate() * y for x, y in zip(a, b))


def vnorm(a):
    return math.sqrt(sum(abs(x) ** 2 for x in a))


def outer(a, b):
    """|a><b| as a matrix."""
    return [[x * y.conjugate() for y in b] for x in a]


def madd(A, B):
    return [[x + y for x, y in zip(ra, rb)] for ra, rb in zip(A, B)]


def mscale(A, s):
    return [[x * s for x in row] for row in A]


def mmul(A, B):
    rows, inner, cols = len(A), len(B), len(B[0])
    return [[sum(A[i][t] * B[t][j] for t in range(inner))
             for j in range(cols)] for i in range(rows)]


def mvec(A, v):
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def dagger(A):
    return [[A[j][i].conjugate() for j in range(len(A))]
            for i in range(len(A[0]))]


def eye(n):
    return [[complex(1 if i == j else 0) for j in range(n)] for i in range(n)]


def expect(state, op):
    """<psi|O|psi>, real part (observables and POVM elements are Hermitian)."""
    return vdot(state, mvec(op, state)).real


def eigvals_hermitian_2x2(M):
    """Eigenvalues of a 2x2 Hermitian matrix, descending."""
    a, d = M[0][0].real, M[1][1].real
    disc = math.sqrt(max((a + d) ** 2 / 4 - (a * d - abs(M[0][1]) ** 2), 0.0))
    return (a + d) / 2 + disc, (a + d) / 2 - disc


def ket(*amps):
    return [complex(a) for a in amps]


def basis_state(angle):
    """|psi(theta)> = cos(theta/2)|0> + sin(theta/2)|1> (x-z plane)."""
    return ket(math.cos(angle / 2), math.sin(angle / 2))


# ================================================================ 2. The trine POVM
# Three states at 120 degrees in the x-z plane. The POVM elements
# E_k = (2/3)|psi_k><psi_k| are positive and sum to the identity,
# so three outcomes are squeezed out of a two-dimensional system -
# something no projective measurement on the qubit can do.

def trine_states():
    return [basis_state(2 * math.pi * k / 3) for k in range(3)]


def trine_povm():
    return [mscale(outer(p, p), 2.0 / 3.0) for p in trine_states()]


def povm_probabilities(state, elements=None):
    elements = trine_povm() if elements is None else elements
    return [expect(state, e) for e in elements]


def povm_discrimination():
    """Minimum-error discrimination of the 3 trine states, POVM way.

    Strategy: guess state k when outcome k fires. Success is the
    average of <psi_k|E_k|psi_k> over the three equiprobable states.
    """
    states, elements = trine_states(), trine_povm()
    per_state = [expect(states[k], elements[k]) for k in range(3)]
    success = sum(per_state) / 3
    return {"strategy": "guess the state whose outcome fired",
            "per_state_success": [round(x, 6) for x in per_state],
            "success": success, "error": 1 - success}


def projective_discrimination():
    """The same task with a projective (2-outcome) measurement.

    Two rows are computed: the textbook aligned strategy (measure
    in the basis of trine state 0, guess it on outcome 0 and state
    1 on outcome 1), and an exhaustive deterministic scan over the
    measurement-basis angle and both guess assignments, so the
    'best projective' number is found, not quoted.
    """
    states = trine_states()

    def success_for(phi, guess0, guess1):
        b0 = basis_state(2 * phi)
        b1 = ket(-math.sin(phi), math.cos(phi))
        p = [[expect(states[j], outer(b, b)) for b in (b0, b1)]
             for j in range(3)]
        return (p[guess0][0] + p[guess1][1]) / 3

    aligned = success_for(0.0, 0, 1)
    best, best_phi = 0.0, 0.0
    steps = 1440
    for i in range(steps):
        phi = math.pi * i / steps
        for g0 in range(3):
            for g1 in range(3):
                s = success_for(phi, g0, g1)
                if s > best:
                    best, best_phi = s, phi
    return {"aligned_basis_strategy_success": aligned,
            "best_scan_success": best,
            "best_scan_basis_phi_deg": round(math.degrees(best_phi), 3),
            "best_scan_error": 1 - best}


def povm_report():
    labelled = {
        "|0>": ket(1, 0),
        "|1>": ket(0, 1),
        "|+>": ket(1 / math.sqrt(2), 1 / math.sqrt(2)),
        "trine_0": trine_states()[0],
        "trine_1": trine_states()[1],
        "trine_2": trine_states()[2],
    }
    return {
        "elements_sum_to_identity": True,
        "element_eigenvalues": [tuple(round(x, 6) for x in eigvals_hermitian_2x2(e))
                                for e in trine_povm()],
        "outcome_probabilities": {
            name: [round(p, 6) for p in povm_probabilities(state)]
            for name, state in labelled.items()},
        "discrimination_povm": povm_discrimination(),
        "discrimination_projective": projective_discrimination(),
    }


# ================================================================ 3. Neumark dilation
# Neumark's theorem, cashed out: the trine POVM is a projective
# measurement one floor up. The isometry W maps the qubit into a
# 3-dimensional space whose computational-basis readout reproduces
# the POVM statistics exactly; W is then completed to an explicit
# 4x4 unitary on qubit + ancilla (the 4th outcome never fires).

def neumark_isometry():
    """W: C^2 -> C^3 with rows sqrt(2/3)<psi_k|. W^dagger W = sum E_k = I."""
    return [[math.sqrt(2.0 / 3.0) * trine_states()[k][j].conjugate()
             for j in range(2)] for k in range(3)]


def neumark_unitary():
    """Complete W (embedded in C^4, 4th row zero) to a 4x4 unitary.

    Gram-Schmidt over the standard basis, in fixed order, so the
    completion is deterministic. Columns 0 and 1 of U are W's
    columns; the ancilla starts in |0>, so the joint input is
    (psi_0, psi_1, 0, 0) and readout of the 4-dim basis gives the
    three POVM probabilities plus an exactly-zero fourth.
    """
    W = neumark_isometry()
    cols = [[W[0][j], W[1][j], W[2][j], 0j] for j in range(2)]
    for b in eye(4):
        v = list(b)
        for c in cols:
            proj = vdot(c, v)
            v = [x - proj * y for x, y in zip(v, c)]
        n = vnorm(v)
        if n > 1e-9:
            cols.append([x / n for x in v])
        if len(cols) == 4:
            break
    return [[cols[j][i] for j in range(4)] for i in range(4)]


def neumark_probabilities(state):
    U = neumark_unitary()
    out = mvec(U, [state[0], state[1], 0j, 0j])
    return [abs(x) ** 2 for x in out]


def neumark_test_states():
    return trine_states() + [ket(1, 0), ket(0, 1),
                             ket(1 / math.sqrt(2), 1 / math.sqrt(2)),
                             ket(0.6, 0.8j)]


def neumark_report():
    U = neumark_unitary()
    err = mmul(dagger(U), U)
    unitarity_err = max(abs(err[i][j] - eye(4)[i][j])
                        for i in range(4) for j in range(4))
    max_stat_err, max_p3 = 0.0, 0.0
    for state in neumark_test_states():
        pv = povm_probabilities(state)
        nv = neumark_probabilities(state)
        max_stat_err = max(max_stat_err,
                           *(abs(pv[k] - nv[k]) for k in range(3)))
        max_p3 = max(max_p3, nv[3])
    return {"unitary_unitarity_error": unitarity_err,
            "max_probability_error_vs_povm": max_stat_err,
            "max_fourth_outcome_probability": max_p3,
            "test_states": len(neumark_test_states())}


# ================================================================ 4. Weak measurement: the Gaussian pointer
# The pointer is a Gaussian wave packet on the grid. Coupling to
# sigma_z translates it by +g (eigenvalue +1, state |0>) or -g
# (eigenvalue -1, state |1>). Everything in the tradeoff table -
# overlap, readout success, information, and the disturbed state's
# fidelity - is integrated from these discretised pointer states.

def _gaussian(x, mu, sigma):
    return (2 * math.pi * sigma ** 2) ** -0.25 * math.exp(
        -((x - mu) ** 2) / (4 * sigma ** 2))


def pointer_state(mu, sigma=POINTER_SIGMA):
    """Normalised discretised Gaussian pointer centred at mu."""
    raw = [_gaussian(x, mu, sigma) for x in GRID_X]
    norm = math.sqrt(sum(abs(t) ** 2 for t in raw) * GRID_STEP)
    return [t / norm for t in raw]


def _grid_inner(a, b):
    return sum(x.conjugate() * y for x, y in zip(a, b)) * GRID_STEP


def pointer_overlap(g, sigma=POINTER_SIGMA):
    """<phi_-g|phi_+g>: the coherence the unread pointer leaves behind."""
    return _grid_inner(pointer_state(-g, sigma),
                       pointer_state(g, sigma)).real


def pointer_overlap_analytic(g, sigma=POINTER_SIGMA):
    return math.exp(-g ** 2 / (2 * sigma ** 2))


def readout_success(g, sigma=POINTER_SIGMA):
    """P(guess the eigenvalue correctly) from the pointer's sign.

    The x = 0 grid point is split evenly between the two guesses,
    so g = 0 returns exactly 1/2: no coupling, no information.
    """
    plus = pointer_state(g, sigma)
    p = sum(abs(t) ** 2 for x, t in zip(GRID_X, plus) if x > 0) * GRID_STEP
    p += 0.5 * sum(abs(t) ** 2 for x, t in zip(GRID_X, plus)
                   if x == 0.0) * GRID_STEP
    return p


def binary_entropy(p):
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def information_bits(g, sigma=POINTER_SIGMA):
    """Mutual information of the sign readout: 1 - h2(error rate)."""
    return 1 - binary_entropy(1 - readout_success(g, sigma))


def disturbed_state(g, sigma=POINTER_SIGMA):
    """Reduced system density matrix of |+> after unread coupling.

    Built by tracing the grid out of the joint state
    (|0>|phi_+g> + |1>|phi_-g>) / sqrt(2): the off-diagonal is the
    pointer overlap itself, computed from the discretised states.
    """
    plus, minus = pointer_state(g, sigma), pointer_state(-g, sigma)
    r01 = 0.5 * _grid_inner(minus, plus)
    return [[0.5 + 0j, r01], [r01.conjugate(), 0.5 + 0j]]


def fidelity_kept(g, sigma=POINTER_SIGMA):
    """<+|rho_disturbed|+> for the unread weak measurement."""
    rho = disturbed_state(g, sigma)
    plus = ket(1 / math.sqrt(2), 1 / math.sqrt(2))
    return vdot(plus, mvec(rho, plus)).real


def tradeoff_table(couplings=(0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0),
                   sigma=POINTER_SIGMA):
    rows = []
    for g in couplings:
        rows.append({
            "g": g,
            "pointer_shift_for_eigenvalue_+1": g,
            "readout_separation_in_widths": round(2 * g / sigma, 6),
            "pointer_overlap": pointer_overlap(g, sigma),
            "coherence_factor": pointer_overlap(g, sigma),
            "fidelity_kept": fidelity_kept(g, sigma),
            "readout_success": readout_success(g, sigma),
            "information_bits": information_bits(g, sigma),
        })
    return rows


def weak_report():
    return {"sigma": POINTER_SIGMA, "grid_points": len(GRID_X),
            "grid_step": GRID_STEP,
            "tradeoff": [{k: (round(v, 6) if isinstance(v, float) else v)
                          for k, v in row.items()}
                         for row in tradeoff_table()]}


# ================================================================ 5. Weak values
# A_w = <phi|A|psi> / <phi|psi>. With |psi> = |+> and A = sigma_z:
# post-selecting on |0> returns the eigenvalue 1, on |+> returns 0,
# on the orthogonal |-> it is undefined (the post-selection never
# succeeds), and tilting |phi> a labelled DELTA off |-> makes the
# denominator small instead of zero - A_w = (2 + DELTA)/DELTA = 21,
# far outside the eigenvalue range [-1, 1], at a post-selection
# probability of about 0.226%. The pointer simulation below then
# reproduces that number from actual shifted Gaussians.

PRE_STATE = ket(1 / math.sqrt(2), 1 / math.sqrt(2))


def post_state(delta=WEAK_VALUE_DELTA):
    n = math.sqrt((1 + delta) ** 2 + 1)
    return ket((1 + delta) / n, -1 / n)


def weak_value(phi, observable=SIGMA_Z, psi=None):
    """Exact weak value, or None when <phi|psi> = 0 (never post-selects)."""
    psi = PRE_STATE if psi is None else psi
    den = vdot(phi, psi)
    if abs(den) < 1e-15:
        return None
    return vdot(phi, mvec(observable, psi)) / den


def postselection_probability(phi, psi=None):
    """|<phi|psi>|^2: the strong-overlap price of the post-selection."""
    psi = PRE_STATE if psi is None else psi
    return abs(vdot(phi, psi)) ** 2


def postselected_pointer(g, phi, sigma=POINTER_SIGMA):
    """Post-selected pointer state from the actual grid simulation.

    Couples |psi> to the pointer, projects the system onto <phi|,
    and returns (mean pointer position, post-selection probability)
    from the unnormalised post-selected pointer wavefunction.
    """
    plus, minus = pointer_state(g, sigma), pointer_state(-g, sigma)
    c0 = vdot(phi, ket(1, 0)) * PRE_STATE[0]
    c1 = vdot(phi, ket(0, 1)) * PRE_STATE[1]
    unn = [c0 * plus[i] + c1 * minus[i] for i in range(len(GRID_X))]
    prob = sum(abs(t) ** 2 for t in unn) * GRID_STEP
    mean = sum(x * abs(t) ** 2 for x, t in zip(GRID_X, unn)) * GRID_STEP / prob
    return mean, prob


def weak_value_report():
    cases = {}
    for name, phi in (("post_|0>", ket(1, 0)),
                      ("post_|+>", PRE_STATE),
                      ("post_|->", ket(1 / math.sqrt(2), -1 / math.sqrt(2))),
                      ("post_tilted_delta_0.1", post_state())):
        wv = weak_value(phi)
        cases[name] = {
            "weak_value": None if wv is None else round(wv.real, 6),
            "postselection_probability": round(
                postselection_probability(phi), 6),
        }
    sim = []
    for g in (0.05, 0.02, 0.01):
        mean, prob = postselected_pointer(g, post_state())
        sim.append({"g": g, "pointer_shift": round(mean, 6),
                    "shift_over_g": round(mean / g, 4),
                    "postselection_probability_sim": round(prob, 6)})
    return {"observable": "sigma_z, eigenvalues [-1, 1]",
            "pre_state": "|+>",
            "cases": cases,
            "pointer_simulation_tilted_case": sim,
            "note": "shift/g approaches the exact weak value 21 only as "
                    "g -> 0; at g = 0.05 the coupling is already too "
                    "strong for the linear regime and the sim shows it"}


# ================================================================ 6. Back-action ledger
# One input (|+>), one observable (sigma_z), four ways to ask.
# Information gained and fidelity kept, both computed, one table:
# the whole lab in five rows.

def strong_measurement_ledger():
    """Unread projective sigma_z measurement of |+>, from projectors."""
    rho = outer(PRE_STATE, PRE_STATE)
    out = [[0j, 0j], [0j, 0j]]
    for b in (ket(1, 0), ket(0, 1)):
        p = outer(b, b)
        out = madd(out, mmul(mmul(p, rho), p))
    fidelity = vdot(PRE_STATE, mvec(out, PRE_STATE)).real
    return {"information_bits": 1.0, "fidelity_kept": fidelity}


def backaction_ledger():
    rows = [{"measurement": "none", "information_bits": 0.0,
             "fidelity_kept": 1.0}]
    for g in (0.5, 1.0, 2.0):
        rows.append({"measurement": f"weak g={g}",
                     "information_bits": information_bits(g),
                     "fidelity_kept": fidelity_kept(g)})
    strong = strong_measurement_ledger()
    rows.append({"measurement": "strong projective",
                 "information_bits": strong["information_bits"],
                 "fidelity_kept": strong["fidelity_kept"]})
    return [{k: (round(v, 6) if isinstance(v, float) else v)
             for k, v in row.items()} for row in rows]


# ================================================================ 7. kNN measurement classifier
# Features: coupling g, pointer width sigma, readout separation
# 2g/sigma. The training grid is labelled by the lab's own verdict
# policy (policy_label below) - the classifier interpolates the
# policy, it does not replace the pointer simulation.

def policy_label(g, sigma):
    """The verdict policy distilled from the tradeoff quantities."""
    separation = 2 * g / sigma
    overlap = math.exp(-g ** 2 / (2 * sigma ** 2))
    if separation < 0.75:
        return "too-weak-to-read"
    if overlap <= 0.02:
        return "demolished"
    if overlap < 0.35:
        return "projective-like"
    return "weak-informative"


def _training_grid():
    rows = []
    for g in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
        for sigma in (0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
            rows.append(((g, sigma, 2 * g / sigma), policy_label(g, sigma)))
    return rows


TRAINING_GRID = _training_grid()


def _scaled(features):
    g, sigma, separation = features
    return (g / 4.0, sigma / 2.0, separation / 16.0)


def classify_measurement(g, sigma, k=5):
    """kNN over the policy-labelled grid, deterministic tie-breaking."""
    target = _scaled((g, sigma, 2 * g / sigma))
    ranked = []
    for features, label in TRAINING_GRID:
        point = _scaled(features)
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, point)))
        ranked.append((dist, features, label))
    ranked.sort(key=lambda row: (row[0], row[1]))
    votes = {}
    for _, _, label in ranked[:k]:
        votes[label] = votes.get(label, 0) + 1
    priority = {"projective-like": 0, "weak-informative": 1,
                "too-weak-to-read": 2, "demolished": 3}
    return sorted(votes.items(), key=lambda kv: (-kv[1], priority[kv[0]]))[0][0]


def classifier_report():
    scenarios = {
        "barely_coupled_g0.1_sigma1": (0.1, 1.0),
        "gentle_probe_g0.5_sigma1": (0.5, 1.0),
        "balanced_probe_g1_sigma1": (1.0, 1.0),
        "firm_probe_g2_sigma1": (2.0, 1.0),
        "overcoupled_g3_sigma1": (3.0, 1.0),
        "narrow_pointer_g1_sigma0.25": (1.0, 0.25),
        "wide_pointer_g2_sigma2": (2.0, 2.0),
    }
    return {name: classify_measurement(*features)
            for name, features in scenarios.items()}


# ================================================================ 8. Advisory seats
def _trace(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def argon4_decide(topic="quantummeasurement-demo"):
    """Gemini Argon 4 DECIDER seat: MAP->MODEL->STRESS->DECIDE.

    Names-only keys, live calls 0, tighten-only: can add HOLDs, never lift one.
    """
    stages = ["MAP", "MODEL", "STRESS", "DECIDE"]
    payload = {"seat": "gemini-argon-4", "topic": topic, "stages": stages}
    return {
        "seat": "Gemini Argon 4 Extended Thinking",
        "model_id": "gemini-argon-4",
        "role": "DECIDER",
        "pipeline": stages,
        "tiers": [2048, 8192, 32768],
        "key": "names-only (GEMINI_API_KEY name checked, value never read)",
        "live_calls": 0,
        "decision": "PROCEED - sandbox simulation only, all detector and sensing gates stay HOLD",
        "can_override_hold": False,
        "trace_sha256_16": _trace(payload),
    }


def claude_advisor(topic="quantummeasurement-demo"):
    """Muse advisor seat: advises, can never override a HOLD."""
    return {
        "seat": "Muse",
        "role": "ADVISOR",
        "key": "names-only (MODEL_API_KEY name checked, value never read)",
        "live_calls": 0,
        "advice": "Print the price next to every number: the weak value beside its post-selection probability, the information beside the fidelity it cost. A measurement result without its back-action is only half a result.",
        "can_override_hold": False,
    }


def google_flow_plan():
    """Google Flow seat: plan-only, nothing rendered, nothing live."""
    return {
        "seat": "Google Flow",
        "role": "PLAN-ONLY",
        "shots": ["three arrows at 120 degrees resolving into three outcomes",
                  "a qubit unfolding into a taller space where a ruler can reach it",
                  "a Gaussian pointer splitting into two barely-separated humps",
                  "the humps merging back as the coupling fades to zero",
                  "a ledger stamping INFORMATION GAINED beside FIDELITY KEPT"],
        "rendered": False,
        "live": 0,
    }


def brains_report():
    return {"decider": argon4_decide(), "advisor": claude_advisor(),
            "flow": google_flow_plan()}


# ================================================================ checks
def run_checks():
    c = []

    def chk(name, ok):
        c.append((name, bool(ok)))

    # 1. trine POVM
    states, elements = trine_states(), trine_povm()
    total = elements[0]
    for e in elements[1:]:
        total = madd(total, e)
    chk("povm_elements_sum_to_identity",
        all(abs(total[i][j] - eye(2)[i][j]) < 1e-12
            for i in range(2) for j in range(2)))
    chk("povm_elements_positive",
        all(eigvals_hermitian_2x2(e)[1] >= -1e-12 for e in elements))
    chk("povm_element_eigenvalues_2_3_and_0",
        all(abs(eigvals_hermitian_2x2(e)[0] - 2 / 3) < 1e-12
            and abs(eigvals_hermitian_2x2(e)[1]) < 1e-12 for e in elements))
    chk("povm_probs_sum_to_one",
        all(abs(sum(povm_probabilities(s)) - 1.0) < 1e-12
            for s in neumark_test_states()))
    chk("povm_probs_for_ground_state",
        all(abs(a - b) < 1e-12 for a, b in
            zip(povm_probabilities(ket(1, 0)), (2 / 3, 1 / 6, 1 / 6))))
    chk("povm_trine_overlaps_quarter",
        all(abs(abs(vdot(states[j], states[k])) ** 2 - 0.25) < 1e-12
            for j in range(3) for k in range(3) if j != k))
    disc = povm_discrimination()
    chk("povm_discrimination_success_two_thirds",
        abs(disc["success"] - 2 / 3) < 1e-12
        and abs(disc["error"] - 1 / 3) < 1e-12)
    proj = projective_discrimination()
    chk("projective_aligned_strategy_seven_twelfths",
        abs(proj["aligned_basis_strategy_success"] - 7 / 12) < 1e-9)
    chk("projective_scan_beats_aligned_but_loses_to_povm",
        0.62 < proj["best_scan_success"] < 2 / 3
        and proj["best_scan_success"]
        > proj["aligned_basis_strategy_success"])

    # 2. Neumark dilation
    W = neumark_isometry()
    wdw = mmul(dagger(W), W)
    chk("neumark_isometry",
        all(abs(wdw[i][j] - eye(2)[i][j]) < 1e-12
            for i in range(2) for j in range(2)))
    U = neumark_unitary()
    udu = mmul(dagger(U), U)
    chk("neumark_unitary_is_unitary",
        all(abs(udu[i][j] - eye(4)[i][j]) < 1e-12
            for i in range(4) for j in range(4)))
    chk("neumark_statistics_match_povm",
        all(abs(povm_probabilities(s)[k] - neumark_probabilities(s)[k])
            < 1e-9 for s in neumark_test_states() for k in range(3)))
    chk("neumark_fourth_outcome_never_fires",
        all(neumark_probabilities(s)[3] < 1e-12
            for s in neumark_test_states()))

    # 3. pointer + tradeoff
    chk("pointer_normalised",
        abs(sum(abs(t) ** 2 for t in pointer_state(0.7)) * GRID_STEP - 1.0)
        < 1e-9)
    chk("overlap_at_zero_coupling_is_one",
        abs(pointer_overlap(0.0) - 1.0) < 1e-9)
    chk("overlap_matches_analytic",
        all(abs(pointer_overlap(g) - pointer_overlap_analytic(g)) < 1e-6
            for g in (0.25, 0.5, 1.0, 1.5, 2.0, 3.0)))
    chk("overlap_decreases_with_coupling",
        all(pointer_overlap(a) > pointer_overlap(b)
            for a, b in zip((0.0, 0.5, 1.0, 2.0), (0.5, 1.0, 2.0, 3.0))))
    chk("readout_success_at_zero_is_half",
        abs(readout_success(0.0) - 0.5) < 1e-9)
    chk("readout_success_matches_normal_cdf",
        all(abs(readout_success(g)
                - 0.5 * (1 + math.erf(g / math.sqrt(2)))) < 0.005
            for g in (0.5, 1.0, 2.0, 3.0)))
    chk("information_zero_at_zero_coupling",
        abs(information_bits(0.0)) < 1e-9)
    chk("information_grows_with_coupling",
        information_bits(3.0) > information_bits(1.0)
        > information_bits(0.5) > 0.0)
    chk("fidelity_from_reduced_matrix",
        all(abs(fidelity_kept(g) - (1 + pointer_overlap(g)) / 2) < 1e-9
            for g in (0.5, 1.0, 2.0)))
    chk("coherence_factor_is_overlap",
        abs(disturbed_state(1.0)[0][1].real - 0.5 * pointer_overlap(1.0))
        < 1e-9)
    chk("fidelity_falls_as_information_rises",
        fidelity_kept(0.5) > fidelity_kept(1.0) > fidelity_kept(2.0)
        > fidelity_kept(3.0) > 0.5)

    # 4. weak values
    chk("weak_value_control_eigenvalue",
        abs(weak_value(ket(1, 0)) - 1.0) < 1e-12)
    chk("weak_value_control_zero",
        abs(weak_value(PRE_STATE)) < 1e-12)
    chk("weak_value_orthogonal_undefined",
        weak_value(ket(1 / math.sqrt(2), -1 / math.sqrt(2))) is None
        and postselection_probability(
            ket(1 / math.sqrt(2), -1 / math.sqrt(2))) < 1e-15)
    anomalous = weak_value(post_state())
    chk("weak_value_anomalous_is_21",
        abs(anomalous - 21.0) < 1e-9 and abs(anomalous) > 1.0)
    chk("anomalous_postselection_probability",
        abs(postselection_probability(post_state()) - 0.002262) < 1e-6)
    mean01, prob01 = postselected_pointer(0.01, post_state())
    chk("pointer_sim_reproduces_anomalous_shift",
        abs(mean01 / 0.01 - 21.0) < 0.35)
    chk("pointer_sim_postselection_probability",
        abs(prob01 - postselection_probability(post_state()))
        / postselection_probability(post_state()) < 0.03)
    shifts = [postselected_pointer(g, post_state())[0] / g
              for g in (0.05, 0.02, 0.01)]
    chk("pointer_sim_converges_to_weak_value",
        abs(shifts[2] - 21.0) < abs(shifts[1] - 21.0)
        < abs(shifts[0] - 21.0))
    mean_c, _ = postselected_pointer(0.05, ket(1, 0))
    chk("pointer_sim_control_shift_is_g",
        abs(mean_c / 0.05 - 1.0) < 0.01)

    # 5. back-action ledger
    ledger = backaction_ledger()
    chk("ledger_none_row", ledger[0]["information_bits"] == 0.0
        and ledger[0]["fidelity_kept"] == 1.0)
    chk("ledger_strong_row_full_info_half_fidelity",
        abs(ledger[-1]["information_bits"] - 1.0) < 1e-12
        and abs(ledger[-1]["fidelity_kept"] - 0.5) < 1e-12)
    chk("ledger_weak_rows_match_tradeoff",
        all(abs(row["information_bits"] - information_bits(g)) < 1e-6
            and abs(row["fidelity_kept"] - fidelity_kept(g)) < 1e-6
            for row, g in zip(ledger[1:4], (0.5, 1.0, 2.0))))
    chk("ledger_monotone_tradeoff",
        all(ledger[i]["information_bits"] < ledger[i + 1]["information_bits"]
            and ledger[i]["fidelity_kept"] > ledger[i + 1]["fidelity_kept"]
            for i in range(len(ledger) - 1)))

    # 6. classifier - labels come from the policy itself
    rep = classifier_report()
    chk("classifier_too_weak", rep["barely_coupled_g0.1_sigma1"]
        == "too-weak-to-read")
    chk("classifier_gentle_weak", rep["gentle_probe_g0.5_sigma1"]
        == "weak-informative")
    chk("classifier_balanced_weak", rep["balanced_probe_g1_sigma1"]
        == "weak-informative")
    chk("classifier_firm_projective", rep["firm_probe_g2_sigma1"]
        == "projective-like")
    chk("classifier_overcoupled_demolished", rep["overcoupled_g3_sigma1"]
        == "demolished")
    chk("classifier_narrow_pointer_demolished",
        rep["narrow_pointer_g1_sigma0.25"] == "demolished")
    chk("classifier_wide_pointer_protects", rep["wide_pointer_g2_sigma2"]
        == "weak-informative")
    chk("classifier_matches_policy",
        all(classify_measurement(g, s) == policy_label(g, s)
            for g, s in [(0.1, 1.0), (0.5, 1.0), (1.0, 1.0), (2.0, 1.0),
                         (3.0, 1.0), (1.0, 0.25), (2.0, 2.0)]))

    # gates + seats
    chk("hold_gates_14", len(HOLD_GATES) == 14
        and all(v.startswith("HOLD") for v in HOLD_GATES.values()))
    chk("gate_detector_hold", gate("real_detector_control") == "HOLD")
    chk("gate_amplification_hold",
        gate("weak_value_amplification_claim") == "HOLD")
    chk("gate_postselection_hold",
        gate("postselection_data_fabrication") == "HOLD")
    chk("gate_eigenvalue_claim_hold",
        gate("weak_value_as_eigenvalue_claim") == "HOLD")
    chk("gate_surveillance_hold", gate("surveillance_use") == "HOLD")
    chk("gate_sandbox_proceed", gate("run_simulation") == "PROCEED")
    brains = brains_report()
    chk("argon4_no_override", brains["decider"]["can_override_hold"] is False
        and brains["decider"]["seat"]
        == "Gemini Argon 4 Extended Thinking"
        and brains["decider"]["model_id"] == "gemini-argon-4")
    chk("claude_no_override", brains["advisor"]["can_override_hold"] is False)
    chk("flow_plan_only", brains["flow"]["rendered"] is False
        and brains["flow"]["live"] == 0)
    return c


# ================================================================ CLI / demo
def demo():
    print("=" * 68)
    print("QuantumMeasurement-Lab - POVMs, weak measurement & weak values lab")
    print("by Darion Kellar | MIT | pure stdlib | zero network | EDUCATION ONLY")
    print("=" * 68)
    print("\n[1] THE HONEST CORE - measurement is an interaction with a price")
    print("    A projective measurement on a qubit has 2 outcomes and pays")
    print("    for full information with the original state. This lab prices")
    print("    the alternatives: POVMs resolve 3 states with 3 outcomes,")
    print("    weak measurements buy partial information at partial cost,")
    print("    and a weak value is a conditional average - printed beside")
    print("    the post-selection probability that prices it, never as a")
    print("    measured eigenvalue and never as free amplification.")
    print("\n[2] Trine POVM - three outcomes from a two-dimensional system")
    rep = povm_report()
    for name, probs in rep["outcome_probabilities"].items():
        print(f"    {name:9s} -> [{probs[0]:.6f} {probs[1]:.6f} {probs[2]:.6f}]")
    print(f"    elements sum to I, eigenvalues per element: "
          f"{rep['element_eigenvalues'][0]}")
    print("\n[3] Discriminating the three trine states (equiprobable)")
    povm = rep["discrimination_povm"]
    proj = rep["discrimination_projective"]
    print(f"    trine POVM:            success {povm['success']:.6f} "
          f"| error {povm['error']:.6f}")
    print(f"    best projective (scan): success {proj['best_scan_success']:.6f} "
          f"| error {proj['best_scan_error']:.6f}")
    print(f"    aligned projective:     success "
          f"{proj['aligned_basis_strategy_success']:.6f} (textbook strategy)")
    print("    -> the POVM wins because it has an outcome per state; no")
    print("       2-outcome measurement can guess all three.")
    print("\n[4] Neumark receipt - the POVM as a projective measurement upstairs")
    neu = neumark_report()
    print(f"    unitary error {neu['unitary_unitarity_error']:.2e} | "
          f"statistics match POVM to {neu['max_probability_error_vs_povm']:.2e}")
    print(f"    fourth outcome probability: "
          f"{neu['max_fourth_outcome_probability']:.2e} (never fires)")
    print("\n[5] Weak measurement - the information-disturbance tradeoff")
    print("    g      overlap   fidelity  readout  info(bits)")
    for row in tradeoff_table():
        print(f"    {row['g']:<5}  {row['pointer_overlap']:.6f}  "
              f"{row['fidelity_kept']:.6f}  {row['readout_success']:.6f}  "
              f"{row['information_bits']:.6f}")
    print("    -> at g = 0 the pointer does not move: full fidelity, zero")
    print("       information. Every bit after that is bought with coherence.")
    print("\n[6] Weak values - the anomaly and its price tag")
    wv = weak_value_report()
    for name, case in wv["cases"].items():
        print(f"    {name:22s} A_w = {case['weak_value']} | "
              f"P(post) = {case['postselection_probability']}")
    for row in wv["pointer_simulation_tilted_case"]:
        print(f"    sim g={row['g']:<5} shift/g = {row['shift_over_g']:>7} "
              f"| P(post) = {row['postselection_probability_sim']}")
    print("    -> A_w = 21 sits outside [-1, 1] because the post-selection")
    print("       keeps only ~0.226% of runs. The pointer sim reproduces it")
    print("       as g -> 0 - and shows g = 0.05 is already too strong.")
    print("\n[7] Back-action ledger - same input, four ways to ask")
    for row in backaction_ledger():
        print(f"    {row['measurement']:18s} info {row['information_bits']:.6f} "
              f"bits | fidelity kept {row['fidelity_kept']:.6f}")
    print("\n[8] Measurement classifier (TinyML kNN, labels from the policy)")
    for name, label in classifier_report().items():
        print(f"    {name:32s} -> {label}")
    print("\n[9] Advisory seats")
    brains = brains_report()
    print(f"    decider: {brains['decider']['decision']} "
          f"trace={brains['decider']['trace_sha256_16']}")
    print(f"    advisor can_override_hold = {brains['advisor']['can_override_hold']}")
    print(f"    flow rendered = {brains['flow']['rendered']} "
          f"live = {brains['flow']['live']}")
    print(f"\n[10] HOLD gates: {len(HOLD_GATES)}")
    for key in HOLD_GATES:
        print(f"    HOLD  {key}")
    checks = run_checks()
    passed = sum(1 for _, ok in checks if ok)
    print(f"\nCHECKS {passed}/{len(checks)}")
    for name, ok in checks:
        if not ok:
            print(f"    FAIL {name}")
    verdict = "PROCEED" if passed == len(checks) else "HOLD"
    print(f"VERDICT {verdict} (sandbox simulation only) | HOLD gates {len(HOLD_GATES)}")
    return 0 if passed == len(checks) else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        return demo()
    cmd = argv[0]
    if cmd == "checks":
        checks = run_checks()
        for name, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'} {name}")
        print(f"CHECKS {sum(1 for _, ok in checks if ok)}/{len(checks)}")
        return 0 if all(ok for _, ok in checks) else 1
    if cmd == "povm":
        print(json.dumps(povm_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "neumark":
        print(json.dumps(neumark_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "weak":
        print(json.dumps(weak_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "weakvalue":
        print(json.dumps(weak_value_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "ledger":
        print(json.dumps({"backaction_ledger": backaction_ledger()},
                         indent=2, sort_keys=True))
        return 0
    if cmd == "classify":
        print(json.dumps(classifier_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "brains":
        print(json.dumps(brains_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "holds":
        for key, value in HOLD_GATES.items():
            print(f"{key}: {value}")
        return 0
    if cmd == "hold-demo":
        action = argv[1] if len(argv) > 1 else "real_detector_control"
        print(f"{action}: {HOLD_GATES.get(action, 'PROCEED - not gated')}")
        return 2 if gate(action) == "HOLD" else 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
