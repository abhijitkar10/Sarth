"""Synthetic mechanism study for rank-blend ensembles (NOT RSNA data).

Every model score is  s = d * y + noise,  y in {0,1}.  Noise is Gaussian with a chosen
correlation between models, so single-model AUC = Phi(d / sqrt(2)).  All parameters are
assumed, not fitted to any real data.  Output: results.json with paired AUC differences.
"""
import json, math
import numpy as np

SEED = 20261007
N, T, R = 1500, 12, 40          # studies, targets (macro of 12), repetitions
PREV = 0.25                     # label prevalence
rng = np.random.default_rng(SEED)


def rank01(x):
    """Percentile rank in (0,1], column-wise for 2-D."""
    r = np.argsort(np.argsort(x, axis=0), axis=0) + 1.0
    return r / x.shape[0]


def auc(score, y):
    """Mann-Whitney AUC for one score vector."""
    r = np.argsort(np.argsort(score)) + 1.0
    n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def macro_auc(scores, y):
    """scores: (N, T); y: (N, T) -> mean AUC across targets."""
    return float(np.mean([auc(scores[:, t], y[:, t]) for t in range(scores.shape[1])]))


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def d_for_auc(a):
    """Invert AUC = Phi(d/sqrt2) by bisection."""
    lo, hi = 0.0, 6.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if phi(mid / math.sqrt(2)) < a: lo = mid
        else: hi = mid
    return (lo + hi) / 2


def make_models(y, specs, rho_global, c_family):
    """specs: list of (family, d) -> scores (N, T, M).
    noise_m = sqrt(rho_global) g + sqrt(c_family - rho_global) f_fam + sqrt(1 - c_family) e_m."""
    n, t = y.shape
    g = rng.standard_normal((n, t))
    fams = {f: rng.standard_normal((n, t)) for f in sorted({s[0] for s in specs})}
    out = []
    for fam, d in specs:
        e = rng.standard_normal((n, t))
        noise = (math.sqrt(rho_global) * g + math.sqrt(max(c_family - rho_global, 0)) * fams[fam]
                 + math.sqrt(1 - c_family) * e)
        out.append(d * y + noise)
    return np.stack(out, axis=-1)


def per_target_d(base_auc, spread=0.025):
    """Targets differ in difficulty: AUC drawn around base_auc."""
    a = np.clip(base_auc + spread * rng.standard_normal(T), 0.75, 0.985)
    return np.array([d_for_auc(x) for x in a])


def summarize(diffs):
    diffs = np.asarray(diffs)
    m = diffs.mean(); se = diffs.std(ddof=1) / math.sqrt(len(diffs))
    return {"mean": float(m), "ci95": float(1.96 * se)}


res = {"config": {"N": N, "T": T, "R": R, "prevalence": PREV, "seed": SEED}}

# ---- Exp 1: ensemble size within one family (noise correlation c = 0.7) -------------
sizes = [1, 2, 5, 10, 20]
acc = {k: [] for k in sizes}
for _ in range(R):
    y = (rng.random((N, T)) < PREV).astype(float)
    dts = per_target_d(0.90)
    specs = [("dino", 1.0)] * 20
    sc = make_models(y, [(f, 1.0) for f, _ in specs], rho_global=0.0, c_family=0.7)
    sc = sc + ((dts - 1.0)[None, :] * y)[..., None]   # per-target signal strength shared by all members
    for k in sizes:
        acc[k].append(macro_auc(rank01(sc[..., :k].mean(-1)), y))
res["exp1_ensemble_size"] = {str(k): summarize(v) for k, v in acc.items()}

# ---- Exp 2: cross-family blend vs error correlation ---------------------------------
rhos = [0.2, 0.4, 0.6, 0.8]
blend = {}
for rho in rhos:
    rec = {"dino20": [], "rad": [], "coat": [], "blend": []}
    for _ in range(R):
        y = (rng.random((N, T)) < PREV).astype(float)
        dd = per_target_d(0.90)      # DINO ensemble member quality
        specs = [("dino", 1.0)] * 20 + [("rad", 1.0), ("coat", 1.0)]
        sc = make_models(y, specs, rho_global=rho, c_family=max(0.7, rho))
        scale_d = {"dino": 1.0, "rad": 0.93, "coat": 1.05}   # families differ in strength
        for i, (fam, _) in enumerate(specs):
            sc[..., i] += (dd * scale_d[fam] - 1.0) * y
        dino = rank01(sc[..., :20].mean(-1)); rad = rank01(sc[..., 20]); coat = rank01(sc[..., 21])
        t_branch = rank01(0.7 * dino + 0.3 * rad)
        final = rank01(0.4 * t_branch + 0.6 * coat)
        rec["dino20"].append(macro_auc(dino, y)); rec["rad"].append(macro_auc(rad, y))
        rec["coat"].append(macro_auc(coat, y)); rec["blend"].append(macro_auc(final, y))
    blend[str(rho)] = {k: summarize(v) for k, v in rec.items()}
res["exp2_family_blend"] = blend

# ---- Exp 3: post-calibration residual  T' = rank(T + s * (rank(a) - rank(b))) -------
scales = [0.05, 0.15, 0.30]
scen = {"a_worse_0.05auc": -0.05, "a_same_as_b": 0.0, "a_better_0.02auc": 0.02}
resid = {}
for name, gain in scen.items():
    rec = {str(s): [] for s in scales}
    for _ in range(R):
        y = (rng.random((N, T)) < PREV).astype(float)
        dt = per_target_d(0.92)
        db = np.array([d_for_auc(max(phi(d / math.sqrt(2)) - 0.015, 0.6)) for d in dt])   # b slightly weaker than T
        da = np.array([d_for_auc(min(phi(d / math.sqrt(2)) + gain, 0.99)) for d in db])
        specs = [("T", 1.0), ("ab", 1.0), ("ab", 1.0)]
        sc = make_models(y, specs, rho_global=0.5, c_family=0.92)  # a,b share most noise (same features)
        sc[..., 0] += (dt - 1.0) * y; sc[..., 1] += (da - 1.0) * y; sc[..., 2] += (db - 1.0) * y
        base = rank01(sc[..., 0]); base_auc = macro_auc(base, y)
        diff = rank01(sc[..., 1]) - rank01(sc[..., 2])
        for s in scales:
            rec[str(s)].append(macro_auc(rank01(base + s * diff), y) - base_auc)
    resid[name] = {k: summarize(v) for k, v in rec.items()}
res["exp3_residual"] = resid

# ---- Exp 4: gain marginalisation, weights 1/6,4/6,1/6 vs centre only vs equal -------
views = {}
for name, off_d_scale in {"views_equally_good": 1.0, "off_centre_5pct_weaker": 0.95}.items():
    rec = {"centre_only": [], "weights_1_4_1": [], "equal_thirds": []}
    for _ in range(R):
        y = (rng.random((N, T)) < PREV).astype(float)
        dt = per_target_d(0.91)
        # three views of one model: noise correlation 0.9 between gain views
        sc = make_models(y, [("v", 1.0)] * 3, rho_global=0.0, c_family=0.9)
        sc[..., 1] += (dt - 1.0) * y
        sc[..., 0] += (dt * off_d_scale - 1.0) * y
        sc[..., 2] += (dt * off_d_scale - 1.0) * y
        r = [rank01(sc[..., i]) for i in range(3)]
        rec["centre_only"].append(macro_auc(r[1], y))
        rec["weights_1_4_1"].append(macro_auc(rank01(r[0] / 6 + r[1] * 4 / 6 + r[2] / 6), y))
        rec["equal_thirds"].append(macro_auc(rank01((r[0] + r[1] + r[2]) / 3), y))
    c0 = np.array(rec["centre_only"])
    views[name] = {"centre_only": summarize(rec["centre_only"]),
                   "weights_1_4_1_delta": summarize(np.array(rec["weights_1_4_1"]) - c0),
                   "equal_thirds_delta": summarize(np.array(rec["equal_thirds"]) - c0)}
res["exp4_gain_views"] = views


# ---- Exp 5: factorial ablation on a toy replica of the fusion graph ------------------
# T branch (DINO x20 + A5 x5 + Rad head) -> optional residuals A, B -> rank;
# H = 0.6 * Raptor (optionally gain-averaged, G) + 0.4 * residual CoAt;
# final = rank((1-w) T' + w H) with w = 0.60 (1.00 for target index 3 = lateral meniscus).
def make_models2(y, specs, rho_global, c_by_family):
    """specs: list of (family, strength). noise = sqrt(rho)*g + sqrt(c_f - rho)*f_fam + sqrt(1-c_f)*e."""
    n, t = y.shape
    g = rng.standard_normal((n, t))
    fams = {f: rng.standard_normal((n, t)) for f in sorted({s_[0] for s_ in specs})}
    out = []
    for fam, strength in specs:
        c = max(c_by_family[fam], rho_global)
        e = rng.standard_normal((n, t))
        out.append(math.sqrt(rho_global) * g + math.sqrt(c - rho_global) * fams[fam] + math.sqrt(1 - c) * e)
    return out  # noise only; signal added by caller


def d_shift(dt, gain):
    return np.array([d_for_auc(min(max(phi(d / math.sqrt(2)) + gain, 0.6), 0.99)) for d in dt])


CONFIGS = {"parent": (0, 0, 0), "A": (1, 0, 0), "B": (0, 1, 0), "G": (0, 0, 1), "AB": (1, 1, 0), "ABG": (1, 1, 1)}
HEAD_SCENARIOS = {"heads_worse_0.03auc": -0.03, "heads_equal": 0.0, "heads_better_0.02auc": 0.02,
                  "stress_worse_0.06": -0.06, "stress_worse_0.10": -0.10, "stress_worse_0.15": -0.15}
fact = {k: {c: [] for c in CONFIGS} for k in HEAD_SCENARIOS}
for _ in range(R):
    y = (rng.random((N, T)) < PREV).astype(float)
    dt = per_target_d(0.90)
    for scen, hq in HEAD_SCENARIOS.items():
        fam_c = {"dino": 0.7, "a5": 0.7, "rad": 0.92, "raptor": 0.9, "rescoat": 0.7}
        # model list: 20 dino, 5 a5, rad ref, e13, e11, e10ref, e10alt, 3 raptor views, rescoat
        specs = [("dino", 1.0)] * 20 + [("a5", 1.03)] * 5 + [("rad", 0.93), ("rad", 0.95), ("rad", 0.95), ("rad", 0.93), ("rad", 0.93)] \
                + [("raptor", 1.05)] * 3 + [("rescoat", 1.0)]
        noises = make_models2(y, specs, 0.40, fam_c)
        sig = []
        for idx, (fam, st) in enumerate(specs):
            d_use = dt * st
            if idx == 27:   d_use = d_shift(dt * 0.95, hq)       # E11 native (A head) quality shift vs E13 (idx 26)
            if idx == 29:   d_use = d_shift(dt * 0.93, hq)       # alternate E10 (B head) quality shift vs reference E10 (idx 28)
            if idx in (30, 32): d_use = dt * 1.05 * 0.95         # off-centre Raptor views (gain 0.9 / 1.1) are 5% weaker
            sig.append(d_use[None, :] * y)
        sc = [sig[i] + noises[i] for i in range(len(specs))]
        dino = rank01(np.mean(sc[0:20], axis=0)); a5 = rank01(np.mean(sc[20:25], axis=0))
        rad_ref, e13, e11, e10r, e10a = (rank01(sc[i]) for i in range(25, 30))
        r_views = [rank01(sc[30]), rank01(sc[31]), rank01(sc[32])]   # gains 0.9, 1.0, 1.1
        rescoat = rank01(sc[33])
        da = rank01(0.55 * dino + 0.45 * a5)
        T0 = rank01(0.7 * da + 0.3 * rad_ref)
        for name, (a_on, b_on, g_on) in CONFIGS.items():
            Tp = T0 + a_on * 0.15 * (e11 - e13) + b_on * 0.85 * 0.500001 * (e10a - e10r)
            Tp = rank01(Tp)
            rap = rank01(r_views[0] / 6 + r_views[1] * 4 / 6 + r_views[2] / 6) if g_on else r_views[1]
            H = rank01(0.6 * rap + 0.4 * rescoat)
            final = rank01(0.4 * Tp + 0.6 * H)
            final[:, 3] = H[:, 3]                                # lateral meniscus uses the CoAt branch alone
            fact[scen][name].append(macro_auc(final, y))
exp5 = {}
for scen in HEAD_SCENARIOS:
    base_ = np.array(fact[scen]["parent"])
    exp5[scen] = {"parent_macro_auc": summarize(base_)}
    for name in CONFIGS:
        if name != "parent":
            exp5[scen][name] = summarize(np.array(fact[scen][name]) - base_)
res["exp5_factorial"] = exp5

json.dump(res, open("results.json", "w"), indent=2)
print(json.dumps(res, indent=1))
