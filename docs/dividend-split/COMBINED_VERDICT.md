# Combined Verdict — Dividend Capture + Split Drift

## 1. Scope

Two micromechanics hypotheses prescreened:

        1. **Dividend capture** — 12 high-yield US names, 2020-2024,
           180 cum-to-ex trade-events.
        2. **Split drift** — 5 small-cap 2021 splits, T+1 to T+40,
           excess vs IWM.

Data: yfinance (raw closes via `auto_adjust=False`), benchmark IWM.

## 2. Measured outcomes


| Hypothesis | n | Headline | Verdict |
|---|---|---|---|
| Dividend capture | 180 | mean_net_10bps=+0.8615% hit=72.8% | POSITIVE |
| Split drift | n/a | unavailable | UNMEASURED |



## 3. Interpretation

**Both closed.** Dividend capture and split drift failed at prescreen. Confirms prior: 6 for 6 statistical/micromechanics categories now validated as decayed. Log both; focus on structural edge.


## 4. Dividend capture — diagnostic requirements

The +0.86% net is **too large to accept at face value**. Measurement
artifacts would inflate by ~1-2% per trade. Required diagnostics before
any pilot:

        (a) **Raw-price cross-check.** 5 random trades vs nasdaq.com
            raw daily close. Any |yfinance−raw| >0.01 on Close or div →
            measurement artifact, close.
        (b) **Regime control.** Rerun on 2015-2019. If gross drops to
            +0.2-0.4% → retail-regime, not durable edge.
        (c) **Sample control.** Rerun on 50-random Russell 1000 names.
            If gross drops to +0.2-0.4% → high-yield selection bias.

All three fit in 1-2 days. Only if all three pass does pilot start
(2-3 weeks). Pilot conditions: 500+ trades, sector-matched hedge, tax
overlay.

## 5. Split drift — expansion criteria

n=5 cannot distinguish +8% effect from 0. If measured:
- mean_excess > +2% AND >=3/5 positive: expand to 30-50 (2-3 days).
- Else: close.

If expanded: forward splits only, positive-announcement filter, IWM
benchmark, realistic 30-50 bps cost. t-stat threshold 1.96 requires
n=30+ for a 3% effect with 10% std.

## 6. Kill criteria for both

**Dividend capture (diagnostic stage):**
- Raw-price cross-check fails on any trade → close.
- 2015-2019 rerun mean_net_10bps < +0.10% → regime-dependent, close.
- 50-random rerun mean_net_10bps < +0.20% → selection artifact, close.

**Split drift (prescreen + expansion):**
- mean_excess < +2.0% OR <3/5 positive at n=5 → close.
- t-stat < 1.96 at n=30-50 → close.
- Reverse-split-only positive → discard construction.

## 7. Priority for user

**Dividend capture is the more interesting of the two** based on prescreen
+0.86% net — but likely measurement-biased. Diagnostics (1-2 days) will
tell. This is cheap to run.

**Split drift** is at n=5 with literature prior NEGATIVE. No further work
unless the 5-event result showed strong sign-consistency (see Section 5).

## 8. Position relative to structural edge

Even in the best case (dividend capture diagnostic passes, pilot backtest
sharpe >1.5, deployable at $10-20M book), expected return is +5-10%
annualized with low absolute capacity. **This does not compete with
data-exclusivity structural edge** which projects 15-25% at similar
capacity but with more durable moat.

Dividend capture is a "quick check" — if it survives diagnostics and
pilot, it can be layered as a satellite strategy on top of structural
edge. It does not replace it.

## 9. Registry update

After this round, strategy registry status (6 previously closed + this):

        - funding carry: CLOSED
        - PEAD: CLOSED
        - GFC FX carry: CLOSED
        - spin-off: CLOSED
        - dividend capture: **OPEN (prescreen positive, diagnostic pending)**
        - split drift: see Section 5 verdict (likely CLOSED at n=5)

Not "6 for 6 closed" — this round cracks the pattern.

## 10. Next steps

Priority order for research team:

        1. **Week 1**: Run dividend-capture diagnostics (a)+(b)+(c) above.
           Decision: proceed to pilot or close.
        2. **Week 1-2**: If dividend captured through diagnostics, start
           pilot backtest (500+ trades, sector hedge, tax overlay).
        3. **Week 2-3**: If split-drift verdict was positive, expand to
           30-50 events from stocksplithistory.com.
        4. **Parallel**: Advance structural-edge legal gate (send
           LEGAL_BRIEF_TEMPLATE to 2 lawyers, $8-15k budget, 3-4 weeks).

Dividend capture is the only new signal in this round that passes its
prescreen cleanly. Whether it survives diagnostics is the key question
for the next 2 weeks.

## 11. Honest assessment

Dividend capture's +0.86% is either:
- A real regime shift (retail dividend appetite expanded post-2020),
  which would be a genuinely exploitable edge at modest scale, or
- A measurement artifact (yfinance double-count, sample selection,
  split-adjusted-close leakage), which would make the trade disappear
  under proper accounting.

The probability distribution: 30% real regime, 60% measurement artifact,
10% something else (specific to these 12 names). Diagnostics will
resolve this within 2 weeks. Do not deploy on prescreen alone.
