#!/usr/bin/env python3
"""Form 4 insider cluster backtest 2015-2024. Entry=first close>=cluster_end+1td, exit=+180cd, SPY bench, 30bps."""
import csv, pickle, glob, bisect, json
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

COST = 0.0030
MIN_PRICE = 1.0

def load_px():
    px = {}
    for p in glob.glob("/tmp/px_cache/chunk_*.pkl"):
        for tk, ser in pickle.load(open(p, "rb")).items():
            px[tk] = ser
    return px

def ntd(days, d):
    i = bisect.bisect_left(days, d)
    return days[i] if i < len(days) else None

def main():
    clusters = []
    with open("/tmp/form4_clusters.csv") as f:
        for r in csv.DictReader(f):
            y = int(r["cluster_end"][:4])
            if 2015 <= y <= 2024:
                clusters.append(r)
    px = load_px()
    spy = pickle.load(open("/tmp/spy.pkl", "rb"))
    spy_days = sorted(spy.keys())
    print(f"clusters_2015_2024: {len(clusters)}  tickers_with_px: {len(px)}")

    events = []; skip_px = skip_dt = skip_liq = 0
    for r in clusters:
        tk = r["ticker"]
        if tk not in px or len(px[tk]) < 50:
            skip_px += 1; continue
        ser = px[tk]; days = sorted(ser.keys())
        try:
            end = datetime.strptime(r["cluster_end"], "%Y-%m-%d").date()
        except Exception:
            skip_dt += 1; continue
        ed = ntd(days, (end + timedelta(days=1)).isoformat())
        if ed is None: skip_dt += 1; continue
        xd = ntd(days, (datetime.strptime(ed, "%Y-%m-%d").date() + timedelta(days=180)).isoformat())
        if xd is None: skip_dt += 1; continue
        pe = ser[ed]
        if pe < MIN_PRICE: skip_liq += 1; continue
        sed = ntd(spy_days, ed); sxd = ntd(spy_days, xd)
        if not sed or not sxd: skip_dt += 1; continue
        rs = ser[xd] / pe - 1.0
        rb = spy[sxd] / spy[sed] - 1.0
        events.append(dict(ticker=tk, cik=r["company_cik"], cluster_start=r["cluster_start"],
                           cluster_end=r["cluster_end"], size=int(r["cluster_size"]),
                           n_tx=int(r["n_transactions"]), entry=ed, exit=xd, entry_price=pe,
                           r_stock=rs, r_spy=rb, excess=rs - rb - COST))
    print(f"events: {len(events)}  skip_no_px={skip_px} skip_date={skip_dt} skip_liq={skip_liq}")
    if not events: return
    json.dump(events, open("/tmp/form4_bt_events.json", "w"))

    ex = np.array([e["excess"] for e in events])
    n = len(ex)
    def st(arr, lab):
        m = arr.mean(); md = float(np.median(arr)); sd = arr.std(ddof=1)
        t = m / (sd / np.sqrt(len(arr))) if sd > 0 else 0
        hit = float((arr > 0).mean())
        lo = m - 1.96 * sd / np.sqrt(len(arr)); hi = m + 1.96 * sd / np.sqrt(len(arr))
        print(f"{lab}: n={len(arr)} mean={m*100:+.2f}% median={md*100:+.2f}% stdev={sd*100:.2f}% t={t:+.2f} hit={hit*100:.1f}% CI95=[{lo*100:+.2f}%,{hi*100:+.2f}%]")
        return dict(n=len(arr), mean=m, median=md, stdev=sd, t=t, hit=hit, lo=lo, hi=hi)

    print("\n=== AGGREGATE (raw) ===")
    agg = st(ex, "raw")
    p1, p99 = np.percentile(ex, [1, 99]); exw = np.clip(ex, p1, p99)
    print("\n=== WINSORIZED 1/99 ===")
    aggw = st(exw, "winsor")

    print("\n=== BY YEAR (winsorized) ===")
    by = defaultdict(list)
    for e in events: by[e["cluster_end"][:4]].append(e["excess"])
    pos = tot = 0; yr_stats = {}
    for y in sorted(by):
        a = np.array(by[y]); a = np.clip(a, p1, p99)
        m = a.mean(); md = float(np.median(a))
        t = m / (a.std(ddof=1) / np.sqrt(len(a))) if len(a) > 1 and a.std(ddof=1) > 0 else 0
        yr_stats[y] = dict(n=len(a), mean=m, median=md, t=t)
        print(f"{y}: n={len(a):4d} mean={m*100:+.2f}% median={md*100:+.2f}% t={t:+.2f}")
        tot += 1; pos += (m > 0)
    print(f"by_year_positive(mean): {pos}/{tot}")

    print("\n=== BY CLUSTER SIZE ===")
    for k in [2, 3, 4, 5, 6]:
        a = np.array([e["excess"] for e in events if e["size"] == k])
        if len(a) > 20: a = np.clip(a, p1, p99); st(a, f"size={k}")
    for k in [8, 10, 15]:
        a = np.array([e["excess"] for e in events if e["size"] >= k])
        if len(a) > 20: a = np.clip(a, p1, p99); st(a, f"size>={k}")

    print("\n=== BY ENTRY PRICE ===")
    for lo_, hi_, lab in [(1, 5, "$1-5"), (5, 15, "$5-15"), (15, 50, "$15-50"), (50, 1e9, "$50+")]:
        a = np.array([e["excess"] for e in events if lo_ <= e["entry_price"] < hi_])
        if len(a) > 20: a = np.clip(a, p1, p99); st(a, lab)

    print("\n=== COST SENSITIVITY (winsorized) ===")
    for c_ in [0.0015, 0.0030, 0.0050]:
        e2 = exw + COST - c_
        t = e2.mean() / (e2.std(ddof=1) / np.sqrt(len(e2)))
        print(f"{c_*10000:.0f}bps: mean={e2.mean()*100:+.2f}% median={np.median(e2)*100:+.2f}% t={t:+.2f}")

    es = sorted(events, key=lambda x: x["excess"])
    print("\n=== TOP 5 ===")
    for e in es[-5:][::-1]:
        print(f"{e['ticker']:6s} end={e['cluster_end']} excess={e['excess']*100:+.1f}% px=${e['entry_price']:.2f} size={e['size']}")
    print("\n=== WORST 5 ===")
    for e in es[:5]:
        print(f"{e['ticker']:6s} end={e['cluster_end']} excess={e['excess']*100:+.1f}% px=${e['entry_price']:.2f} size={e['size']}")

    mean_ = aggw["mean"]; t_ = aggw["t"]; hit_ = aggw["hit"]
    if mean_ > 0.03 and t_ > 1.96 and hit_ > 0.55: v = "POSITIVE"
    elif mean_ > 0 and t_ > 1.0: v = "MARGINAL"
    else: v = "NEGATIVE"
    print(f"\nVERDICT: {v}")
    json.dump(dict(agg=agg, aggw=aggw, yr=yr_stats, verdict=v, n_events=len(events),
                   clusters_total=len(clusters), skip=dict(px=skip_px, dt=skip_dt, liq=skip_liq),
                   top=[(e['ticker'], e['excess']) for e in es[-5:][::-1]],
                   worst=[(e['ticker'], e['excess']) for e in es[:5]]),
              open("/tmp/form4_bt_summary.json", "w"), indent=2)

if __name__ == "__main__":
    main()
