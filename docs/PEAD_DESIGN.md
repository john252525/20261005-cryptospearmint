# PEAD — Post-Earnings Announcement Drift

## Edge
After an earnings surprise, prices tend to keep drifting in the direction of
the surprise for weeks (Bernard & Thomas 1989, and the replication literature).
The underreaction is attributed to slow information diffusion and anchoring on
prior expectations. We trade only *large* surprises (|surprise| >= 5%) that are
confirmed by elevated announcement-day volume (rel-vol >= 1.5x), which filters
noise and low-conviction prints.

## Mechanics
- Entry: open of T+2 (T = earnings date), giving the initial reaction a day to clear.
- Sizing: risk_per_trade_pct (0.25% NAV) sized to the stop distance.
- Exit: stop-loss (7%), holding window (5–30 days), or end of sample.
- Costs: 1 bps commission + 5 bps slippage per side; short borrow 300 bps/yr.
- Hedge: when net-long book exceeds 30% of NAV, short QQQ to neutralise excess beta.

## Risks
1. **Regime dependence** — drift weakens in high-momentum/mean-reverting regimes.
2. **Estimate quality** — yfinance EPS estimates may be stale/restated.
3. **Short borrow** — hard-to-borrow names can cost far more than 300 bps/yr.
4. **Look-ahead risk** — earnings timestamps must be treated as post-close (we use T+2 entry).
5. **Survivorship** — current S&P constituents only; delisted names absent.

## Kill criteria (stop the strategy if any trip)
- Net Sharpe < 0.7 over a rolling 24 months.
- Realised slippage > 20 bps per side.
- Short borrow cost > 5%/year realised.
- Hit rate < 52%.
- Max drawdown > 15%.
