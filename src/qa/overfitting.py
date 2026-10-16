"""Overfitting diagnostics for grid/scan backtests."""
from __future__ import annotations
import logging, random, statistics
from typing import Any, Callable, Iterable

log = logging.getLogger("qa.overfitting")


def parameter_sensitivity(scan_rows, metric="sharpe", top_frac=0.2,
                          elasticity_flag=5.0, param_keys=None):
    """For each parameter: |max(mean(metric))|/|min(mean(metric))| across its values.

    Ratio > elasticity_flag means one parameter moves the metric more than Nx.
    """
    if not scan_rows:
        return {"params": {}, "worst": None, "flag": elasticity_flag}
    rows = [r for r in scan_rows if metric in r and isinstance(r[metric], (int, float))]
    if not rows:
        return {"params": {}, "worst": None, "flag": elasticity_flag}
    keys = set(param_keys) if param_keys else (set(rows[0].keys()) - {metric})
    out = {}
    for k in sorted(keys):
        by_val: dict[Any, list[float]] = {}
        for r in rows:
            by_val.setdefault(r.get(k), []).append(float(r[metric]))
        means = {vk: statistics.mean(vs) for vk, vs in by_val.items() if vs}
        if len(means) < 2:
            continue
        hi, lo = max(means.values()), min(means.values())
        if abs(lo) < 1e-9:
            ratio = float("inf") if abs(hi) > 1e-9 else 1.0
        else:
            ratio = abs(hi) / abs(lo)
        out[k] = {"ratio": ratio, "n_values": len(means),
                  "min_metric": round(lo, 6), "max_metric": round(hi, 6),
                  "flag": ratio > elasticity_flag}
    worst_name, worst_ratio = None, None
    for name, d in out.items():
        r = d["ratio"]
        r_cmp = 1e18 if r == float("inf") else r
        if worst_ratio is None or r_cmp > (1e18 if worst_ratio == float("inf") else worst_ratio):
            worst_name, worst_ratio = name, r
    return {"params": out, "worst": worst_name, "worst_ratio": worst_ratio,
            "flag": elasticity_flag}


def rank_stability(scan_rows, metric="sharpe", top_k=5, noise_frac=0.10,
                   n_trials=100, seed=42, param_keys=None):
    """How often the top-k set survives small multiplicative noise on the metric.

    Stability score = overlap fraction of top-k sets across trials.
    Score < 0.5 → overfitted / unstable.
    """
    if not scan_rows:
        return {"stable": True, "score": 1.0, "trials": 0}
    rows = [r for r in scan_rows if metric in r and isinstance(r[metric], (int, float))]
    if len(rows) < top_k:
        return {"stable": True, "score": 1.0, "trials": 0,
                "message": f"only {len(rows)} rows < top_k={top_k}"}
    keys = set(param_keys) if param_keys else (set(rows[0].keys()) - {metric})
    keys = sorted(keys)

    def sig(r):
        return tuple((k, r.get(k)) for k in keys)

    base_sorted = sorted(rows, key=lambda r: -float(r[metric]))
    base_top = {sig(r) for r in base_sorted[:top_k]}
    rng = random.Random(seed)
    overlaps = []
    for _ in range(n_trials):
        noisy = []
        for r in rows:
            v = float(r[metric])
            nr = dict(r)
            nr[metric] = v * (1.0 + rng.uniform(-noise_frac, noise_frac))
            noisy.append(nr)
        noisy.sort(key=lambda r: -float(r[metric]))
        trial_top = {sig(r) for r in noisy[:top_k]}
        overlaps.append(len(base_top & trial_top) / top_k)
    score = statistics.mean(overlaps) if overlaps else 0.0
    return {"stable": score >= 0.5, "score": round(score, 3),
            "trials": n_trials, "noise_frac": noise_frac,
            "top_k": top_k, "flag": score < 0.5}


def walk_forward(train_fn, test_fn, windows, metric="sharpe",
                 retention_flag=0.5):
    """Recursive train/test split.

    windows: iterable of (train_arg, test_arg).
    train_fn(arg) -> dict of metrics.
    test_fn(arg)  -> dict of metrics.
    """
    results, train_scores, test_scores = [], [], []
    for i, (tr, te) in enumerate(windows):
        try:
            tr_m = train_fn(tr) or {}
            te_m = test_fn(te) or {}
        except Exception as e:
            log.exception("wf window %d failed", i)
            results.append({"window": i, "error": str(e)})
            continue
        tr_v, te_v = tr_m.get(metric), te_m.get(metric)
        results.append({"window": i, "train_metric": tr_v, "test_metric": te_v,
                        "train": tr_m, "test": te_m})
        if isinstance(tr_v, (int, float)):
            train_scores.append(float(tr_v))
        if isinstance(te_v, (int, float)):
            test_scores.append(float(te_v))
    if not train_scores or not test_scores:
        return {"windows": results, "flag": None,
                "message": "no numeric train/test scores"}
    tr_mean = statistics.mean(train_scores)
    te_mean = statistics.mean(test_scores)
    frac = (te_mean / tr_mean) if abs(tr_mean) > 1e-9 else float("nan")
    flag = (frac != frac) or frac < retention_flag
    return {"windows": results, "train_mean": round(tr_mean, 4),
            "test_mean": round(te_mean, 4),
            "retention": round(frac, 3) if frac == frac else None,
            "flag": flag, "n_windows": len(results)}
