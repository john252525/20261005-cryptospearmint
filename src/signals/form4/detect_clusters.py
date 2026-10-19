#!/usr/bin/env python3
"""Cluster detection: same company_cik, 2+ distinct insiders buying (P), within 30-day window."""
import sqlite3, csv
from datetime import datetime, timedelta

DB = "/tmp/form4_bulk.db"
OUT = "/tmp/form4_clusters.csv"

def pd(s):
    s = s.strip()
    for f in ("%d-%b-%Y", "%Y-%m-%d"):
        try: return datetime.strptime(s, f).date()
        except Exception: pass
    return None

def main():
    c = sqlite3.connect(DB).cursor()
    rows = c.execute("""SELECT company_cik, ticker, owner_cik, transaction_date
        FROM p_transactions
        WHERE ticker IS NOT NULL AND ticker NOT IN ('','n/a','NONE','None','(None)')
          AND owner_cik IS NOT NULL""").fetchall()
    by = {}
    for co, tk, ow, td in rows:
        d = pd(td)
        if d is None: continue
        by.setdefault((co, tk), []).append((d, ow))
    clusters = []
    for (co, tk), txns in by.items():
        txns.sort(); n = len(txns); i = 0
        while i < n:
            start = txns[i][0]
            end = start + timedelta(days=30)
            inside = [t for t in txns if start <= t[0] <= end]
            owners = set(o for _, o in inside)
            if len(owners) >= 2:
                maxd = max(t[0] for t in inside)
                clusters.append((co, tk, start.isoformat(), maxd.isoformat(), len(owners), len(inside)))
                nxt = maxd + timedelta(days=1)
                while i < n and txns[i][0] < nxt: i += 1
            else:
                i += 1
    seen = set(); out = []
    for cl in clusters:
        k = (cl[0], cl[3])
        if k in seen: continue
        seen.add(k); out.append(cl)
    out.sort(key=lambda x: x[3])
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["company_cik","ticker","cluster_start","cluster_end","cluster_size","n_transactions"])
        w.writerows(out)
    print("cluster_events:", len(out))
    from collections import Counter
    yr = Counter(x[3][:4] for x in out)
    print("by_year:", dict(sorted(yr.items())))
    print("size_distribution:", dict(sorted(Counter(x[4] for x in out).items())[:6]))
    print("csv:", OUT)

if __name__ == "__main__":
    main()
