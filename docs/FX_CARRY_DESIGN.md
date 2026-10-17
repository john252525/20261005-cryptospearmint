# G10 FX Carry — Design Document (v1, research)

## 1. Edge hypothesis

Interest-rate differentials across G10 currencies are a **compensated risk
premium**. Currencies with structurally higher short rates (historically AUD,
NZD; now also USD after 2022-23 hikes) tend to outperform low-yielders (JPY,
CHF) on a total-return basis, because:

1. **Carry accrual** — a long high-yielder / short low-yielder position earns
   the rate differential as rollover, independent of spot direction.
2. **Central-bank reaction function** — high-yielders typically sit in a
   hawkish regime (commodity exporters, inflation-targeting with positive
   real rates); low-yielders in a ZLB/QE regime. The differential is
   persistent by construction.
3. **Risk premium** — carry is not free: it pays in "risk-on" regimes and
   suffers sharp unwinds (Aug 2024 JPY carry unwind, Mar 2020). The premium
   is compensation for crash risk, hence the vol filter.

**Falsifiable claim**: over a 3-year window, net-of-cost Sharpe ≥ 0.4 for the
top-|carry| G10 pairs, rebalanced weekly.

## 2. Implementation

### Data
- **FX**: `yfinance` daily close, `auto_adjust=True`, USD-quoted pairs
  (`EURUSD=X`, `GBPUSD=X`, `AUDUSD=X`, `NZDUSD=X`) and USD-base pairs
  (`JPY=X`, `USDCAD=X`, `USDCHF=X`, `USDNOK=X`, `USDSEK=X`).
- **Rates**: FRED 3-month interbank series `IR3TIB01<CC>M156N` via the direct
  CSV endpoint `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<series>`.
  Monthly frequency, forward-filled to daily.
- Caches: `data/fx_cache.parquet`, `data/rates_cache.parquet`. Delete to
  refresh (`--refresh` flag).

### Signal
For each pair with base `B` and quote `Q`:

# === Блок 29 ===
python3 -m pip install --user --break-system-packages \
    pyyaml pydantic pydantic-settings pandas numpy yfinance scipy pytest requests pyarrow
python3 -m pytest tests/test_fx_carry.py -q
python3 -m src.strategies.fx_carry.backtest --days 1095 --refresh

# === Блок 30 ===
cd /root/fx-carry-wt && cat backtest/results/*.metrics.json && echo "=== files ===" && ls backtest/results/

# === Блок 31 ===
cd /root/fx-carry-wt && python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd, numpy as np, glob
from src.strategies.fx_carry.backtest import run_backtest
from src.strategies.fx_carry.config import FXCarrySettings
px=pd.read_parquet('data/fx_cache.parquet'); rt=pd.read_parquet('data/rates_cache.parquet')
s=FXCarrySettings(); r=run_backtest(px,rt,settings=s)
e=r.equity; ret=e.pct_change().dropna()
print('yearly returns:')
for y,g in e.groupby(e.index.year):
    print(' ', y, round((g.iloc[-1]/g.iloc[0]-1)*100,2),'%')
print('daily vol ann%', round(ret.std()*np.sqrt(252)*100,2))
print('worst day %', round(ret.min()*100,2), ret.idxmin().date())
print('best day %', round(ret.max()*100,2), ret.idxmax().date())
print('max dd %', round((e/e.cummax()-1).min()*100,2), 'on', (e/e.cummax()-1).idxmin().date())
print('avg holding days', round(np.mean([t.holding_days for t in r.trades]),1))
print('avg carry bps', round(np.mean([t.carry_bps for t in r.trades]),1))
"

# === Блок 32 ===
cd /root/fx-carry-wt && python3 -c "
import sys; sys.path.insert(0,'.')
import pandas as pd
from src.strategies.fx_carry.backtest import run_backtest
from src.strategies.fx_carry.config import FXCarrySettings
px=pd.read_parquet('data/fx_cache.parquet'); rt=pd.read_parquet('data/rates_cache.parquet')
r=run_backtest(px,rt,settings=FXCarrySettings())
tr=r.trades
carry=sum(t.carry_pnl for t in tr); spot=sum(t.gross_pnl for t in tr); fee=sum(t.fees for t in tr)
print('carry pnl', round(carry), 'spot pnl', round(spot), 'fees', round(fee), 'net', round(carry+spot-fee))
print('carry share of gross %', round(carry/(carry+spot)*100,1))
"

# === Блок 33 ===
cat > /root/fx-carry-wt/docs/FX_CARRY_BACKTEST_RESULTS.md <<'MDEOF'
# G10 FX Carry — Backtest Results (v1, real data)

**Run date**: 2025 (see `backtest/results/fx_carry_*.metrics.json` stamp)
**Window**: ~3 years of daily bars (see `years` in metrics)
**Universe**: 9 G10 pairs (EUR, GBP, JPY, AUD, NZD, CAD, CHF, NOK, SEK vs USD)
**Max positions**: 3 · **Threshold**: 50 bps · **Cost**: 10 bps round trip

All numbers below are read directly from the JSON produced by
`python3 -m src.strategies.fx_carry.backtest --days 1095 --refresh`.

## 1. Headline metrics

(see `backtest/results/*.metrics.json` — filled from the actual run)

## 2. Comparison with kill criteria

| Criterion | Threshold | Actual | Pass? |
|---|---|---|---|
| net Sharpe | ≥ 0.4 | see JSON | — |
| max DD | ≤ 15% | see JSON | — |
| hit rate | ≥ 50% | see JSON | — |
| avg carry after costs | ≥ 0.5%/yr | see JSON | — |

## 3. Robustness sweeps

The `variant` sweep above (max_positions 2/3/5, min_carry 25/50/100,
vol filter on/off, risk 10%/25%) is the honest robustness check. Any variant
that flips sign or collapses Sharpe is a red flag on the baseline.

## 4. Verdict

Verdict is written at the bottom after reading real numbers — see
"## 5. Verdict" below.

## 5. Verdict

(to be filled from the run)

## 6. Next steps

(to be filled from the run)
