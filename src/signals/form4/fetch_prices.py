#!/usr/bin/env python3
"""Resumable yfinance fetch with hard per-chunk timeout (signal.alarm)."""
import json, os, pickle, time, signal
import yfinance as yf

CACHE = "/tmp/px_cache"; os.makedirs(CACHE, exist_ok=True)
cl = json.load(open("/tmp/clusters_clean.json"))
tickers = sorted(set(c["ticker"] for c in cl))
tickers = [t for t in tickers if t and "/" not in t and "." not in t and len(t) <= 6]
CHUNK = 50
chunks = [tickers[i:i+CHUNK] for i in range(0, len(tickers), CHUNK)]
print("tickers", len(tickers), "chunks", len(chunks), flush=True)

START = "2014-12-01"; END = "2025-08-01"

class TO(Exception): pass
def handler(s, f): raise TO()
signal.signal(signal.SIGALRM, handler)

for i, ch in enumerate(chunks):
    path = f"{CACHE}/chunk_{i}.pkl"
    if os.path.exists(path):
        continue
    out = {}
    try:
        signal.alarm(90)
        df = yf.download(ch, start=START, end=END, auto_adjust=True, progress=False, threads=True)
        signal.alarm(0)
        if df is not None and len(df) > 0 and hasattr(df.columns, "levels"):
            closes = df["Close"]
            if closes.ndim > 1:
                for tk in closes.columns:
                    s = closes[tk].dropna()
                    if len(s) > 10:
                        out[tk] = {d.strftime("%Y-%m-%d"): float(v) for d, v in s.items()}
    except TO:
        signal.alarm(0)
        print(f"chunk {i} TIMEOUT", flush=True)
    except Exception as e:
        signal.alarm(0)
        print(f"chunk {i} ERR {str(e)[:60]}", flush=True)
    if out:
        with open(path, "wb") as f:
            pickle.dump(out, f)
        print(f"chunk {i}/{len(chunks)} ok tickers={len(out)}", flush=True)
    else:
        print(f"chunk {i}/{len(chunks)} EMPTY", flush=True)
    time.sleep(0.3)
print("PRICE FETCH DONE", flush=True)
