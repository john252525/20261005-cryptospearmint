# Context-Window Transmission — 2026-10-18/19

**Purpose:** state file to resume trading-desk work in a fresh context
window without re-deriving 30+ rounds of research, verifying infrastructure,
or re-reading every document.

**Reader:** the next assistant / operator picking up this repository.

**Rule:** read this after `docs/EXECUTIVE_SUMMARY.md` (the full decision
brief) and before touching any branch. This file contains the compressed
state; EXECUTIVE_SUMMARY.md contains the full reasoning.

---

## Section 1 — What has been done (30+ rounds)

### Research line — CLOSED with 7 hypotheses tested

| # | Hypothesis | Verdict | Key metric | Branch / commit |
|---|---|---|---|---|
| 1 | Funding carry (crypto perp) | CLOSED | Sharpe 0.17 / 20y; max funding 1.0 bps (floor) | `funding-carry` @ `89e055a` |
| 2 | PEAD (earnings drift) | CLOSED | Sharpe 0.70 (1990-2020) → 0.30 (2015-19) → −1.15 (2021-23) | `pead` @ `996242e` |
| 3 | GFC-era FX carry | CLOSED | Sharpe 0.165 / 20y; max DD −30.76% | `fx-carry` @ `f17c41a` |
| 4 | Corporate spin-off | CLOSED | Median −2.38%, t=1.24 (NS at 5%) | `event-research` @ `9ac1a97` |
| 5 | Dividend capture | CLOSED | mean_net −0.35% at 10 bps; hit 46.7%; n=180 | `dividend-split-drift` @ `d3f6634` |
| 6 | Split drift (Ikenberry) | CLOSED | mean_excess −4.43%, t=−0.83, 2/7 positive | `dividend-split-drift` @ `d3f6634` |
| 7 | S&P 500 additions | CLOSED | median_net +0.16%, t=1.968 (below Bonferroni) | `sp500-additions-backtest` |

Pattern: 7 academic-micromechanics categories tested against 2024-2026
data. All fail either in sign or in statistical significance after
multiple-testing correction. This matches the industry-wide decay of
classical anomalies.

### One live signal — short 13D market-neutral

- **Measured backtest (n=66 events, 36-day window Sept-Oct 2026):**
  mean +8.22%, median −3.99%, t=+2.62 (p<0.01)
- **Forward paper-trade:** branch `short-13d-paper` @ `0e55320`
- **Current state:** **90 open positions** across 29 tickers × 3 borrow
  tracks (30/50/80% annualized)
- **First exits due:** ~**2026-11-11** (20 business days)
- **Out-of-sample verdict:** 30-90 days from launch
- **Live DB:** `/root/short-13d-paper/state/short_13d.db` (table
  `paper_positions`, status='OPEN' = 90)
- **Cost to user:** $0 (paper only, no capital deployed)

### Infrastructure inventory

- **Risk engine** (`/root/risk_v0`): 56/56 tests, OMS event-sourced,
  PaperBroker, kill-switch L0-L4
- **Monitoring stack**: Prometheus `:57447`, Grafana `:36308`, both
  under systemd, survive reboot; two exporters (`risk-metrics :9100`,
  `demo-metrics :9101`); dashboards `trading-desk` + `paper-demo`
- **Paper-demo canary**: 60 fills accumulated, `demo_nav_usd=9992.80`,
  proving DCA continuity
- **Event scraper** (`/root/env-scraper-wt`, branch `event-scraper`):
  872 filings in SQLite (`state/scraper.db`), 248 spin-offs + 500 13D
- **QA framework** (`qa-paper`): 9 honesty checks, fail-closed on
  look_ahead + adjusted_prices, severity model
- **Pipeline orchestration** (`pipeline-monitoring`): unified CLI,
  FSM (BOOTSTRAP→PAPER_DRY→...), GitHub Actions CI, nightly cron
- **Rebuild cost estimate:** $150k-250k, 6 months — built at $0
  marginal cost during research rounds

### Documentation index

- `docs/EXECUTIVE_SUMMARY.md` (783 lines) — full decision brief v2
- `docs/executive/CFO_BRIEF.md` (~500 lines) — CFO-facing business brief
- `docs/structural-edge/STRUCTURAL_EDGE_LANDSCAPE.md` — 5 structural
  categories
- `docs/structural-edge/COMPARISON_TABLE.md` — 5×5 scoring (Data
  exclusivity 21/25)
- `docs/structural-edge/DATA_EXCLUSIVITY_SCOPE.md` — 8 verticals
- `docs/structural-edge/LEGAL_BRIEF_TEMPLATE.md` — 10 questions for
  outside counsel
- `docs/structural-edge/VENDOR_SHORTLIST.md` — 25 vendors
- `docs/structural-edge/RECOMMENDATION.md` — Data exclusivity #1, EM
  local #2
- `docs/data-exclusivity/LOI_TERM_SHEET.md` — term sheet with
  termination clause
- `docs/data-exclusivity/LEGAL_EXECUTION_CHECKLIST.md` — week-by-week
  legal execution
- `docs/data-exclusivity/VENDOR_OUTREACH_TEMPLATE.md` — outreach script
- `docs/dividend-split/*` — 3 files covering dividend/split closure

---

## Section 2 — What is on origin

Remote: `git@github.com:john252525/20261005-cryptospearmint.git`

Branches (per `git branch -r` at transmission time):

        origin/HEAD         -> origin/funding-carry
        origin/bootstrap
        origin/dividend-split-drift
        origin/event-research
        origin/event-scraper
        origin/funding-carry
        origin/fx-carry
        origin/index-rebalancing
        origin/pead
        origin/pipeline-monitoring
        origin/qa-paper
        origin/risk-engine
        origin/risk-monitoring
        origin/short-13d-paper
        origin/sp500-additions-backtest
        origin/structural-edge

Latest HEADs at transmission time (verify with `git fetch --all &&
git log --oneline -1 origin/<branch>` when resuming):

        funding-carry        @ 7e13ab1  (chore gitignore)
        pead                 @ 996242e  (v1/v2/v3 verdict)
        fx-carry             @ 6bbc3b4  (verdict CLOSE)
        event-research       @ 9cd1d66  (13D filer parsing)
        event-scraper        @ 9ad2bc3  (SEC EDGAR pipeline)
        dividend-split-drift @ d3f6634  (combined verdict)
        sp500-additions-backtest (check HEAD)
        short-13d-paper      @ 0e55320  (idempotency + metrics)
        structural-edge      @ a272ea8  (CFO brief) — WILL ADVANCE
        pipeline-monitoring  @ (check HEAD on resume)
        risk-engine          @ (check HEAD on resume)
        qa-paper             @ (check HEAD on resume)
        index-rebalancing    @ 4af6c71  (S&P additions backtest)

The current working branch at time of transmission is `structural-edge`.

---

## Section 3 — What is actively running in production

All on canonical server `109.172.6.35` (`pixinvent.dev`).

### systemd services

        unit                       state      port      purpose
        -------------------------  ---------  --------  -----------------
        trading-demo               active     (none)    demo runner (DCA BTC)
        trading-demo-exporter      active     9101      demo metrics
        trading-metrics            active     9100      funding-carry metrics
        prometheus                 active     57447     metrics DB + scrape
        grafana                    active     36308     dashboards

Check state: `systemctl is-active trading-demo trading-demo-exporter
trading-metrics prometheus grafana`

### Listening ports (verified externally)

        :9100    metrics-only, risk_* namespace (funding carry)
        :9101    metrics-only, demo_* namespace (paper demo)
        :9103    (may exist for short-13D exporter; check `ss -tlnp |
                 grep :9103` on resume if expected)
        :36308   Grafana UI, admin/admin
        :57447   Prometheus UI + API

All accessible from public IP 109.172.6.35. Firewall rules permit these.

### SQLite state files

        /root/short-13d-paper/state/short_13d.db   90 open paper positions
        /root/env-scraper-wt/state/scraper.db      872 filings
                                                   (248 spin-off + 500 13D)
        /root/risk_v0/state/demo.db                demo runner orders/fills
        /root/trading-desk/state/pipeline.sqlite   FSM state transitions
        /root/trading-desk/data/state.db           QA reconcile log
        /root/trading-desk/data/qa_state.json      QA honesty streak counters

---

## Section 4 — What awaits a USER decision

Three live options, detailed in `docs/EXECUTIVE_SUMMARY.md` Section 5
and `docs/executive/CFO_BRIEF.md` Page 10.

**Option A — Data exclusivity legal activation**
- Cost: $8,000-15,000 (legal brief to 2 lawyers: US commercial + EU IP)
- Timeline: 3-4 weeks for legal memo
- If pass, then vendor LOI ($200k-1M for AIS shipping, $500k-2M for US
  cards) — Year 1 total exposure $208k-515k
- Expected outcome distribution: 40% full pass, 40% legal pass/backtest
  fail, 20% legal gate fail → pivot EM local
- Kill: legal fails in both US and EU for derived-signal resale

**Option B — Wait for short 13D out-of-sample verdict**
- Cost: $0 (paper already running)
- Timeline: 30-90 days from launch (~2026-11-11 first exits)
- Kill: live Sharpe <1.0 at 50% borrow OR universal borrow >50%
- Scale: if live Sharpe >1.5 at <20% borrow → $500k live

**Option C — Pause / maintenance**
- Cost: $0
- Outcome: infrastructure runs, no new capital, no new hypotheses
- Fallback only, not recommended as primary

**Recommendation (both EXECUTIVE_SUMMARY and CFO_BRIEF):** A + C-in-house
XBRL in parallel; B autonomous in background.

---

## Section 5 — What runs without user input

Two activities continue autonomously while decision is pending:

1. **Short 13D forward paper-trade.** Entries already placed (90
   positions). Exits trigger ~2026-11-11 based on 20-BDay holding period.
   No new entries after current batch unless a fresh 13D filing arrives.
   Read: `journalctl -u` (if systemd) or process logs; SQLite is the
   ground truth.

2. **paper-demo canary.** Every 60 seconds, `demo_runner` buys $100 of
   BTC on the paper broker. Fills accumulate. `demo_nav_usd` tracks NAV.
   Continuously scraped by Prometheus (`:57447`) and graphed in Grafana
   (`:36308/d/paper-demo/`). Only purpose: prove end-to-end chain works
   continuously.

If the demo runner stops (systemd `trading-demo` inactive, expected
after `DEMO_DURATION_SEC=3600` 1-hour window), the exporter keeps
serving the last snapshot on `:9101`. To restart:
`systemctl restart trading-demo trading-demo-exporter`.

---

## Section 6 — How to resume work

Order of reading when picking up:

1. **`docs/transitions/TRANSMISSION_2026_10_18.md`** (this file) — 10
   minutes, full state.
2. **`docs/EXECUTIVE_SUMMARY.md`** — 15-min full decision brief; the
   reasoning behind every closure.
3. **`docs/executive/CFO_BRIEF.md`** — 10-min CFO perspective on same
   decisions.
4. **Branch-specific docs** as needed:
   - `docs/structural-edge/*` for structural analysis
   - `docs/data-exclusivity/*` for LOI/legal execution detail
   - `docs/dividend-split/*` for the last research round's full work

Then check infrastructure state:

        systemctl is-active trading-demo trading-demo-exporter \
                           trading-metrics prometheus grafana
        sqlite3 /root/short-13d-paper/state/short_13d.db \
            "SELECT COUNT(*) FROM paper_positions WHERE status='OPEN'"
        curl -s http://127.0.0.1:9101/metrics | head -5
        curl -s http://127.0.0.1:57447/api/v1/query?query=demo_nav_usd

If everything responds, the state is consistent with this file. If any
service is down, restart with `systemctl restart <unit>` before doing
any new work.

---

## Section 7 — Critical facts (do not forget)

### Environment

- **Canonical server:** `109.172.6.35` (`pixinvent.dev`), Ubuntu 22.04
  aarch64, root access. Any other IP means wrong server — STOP and
  report.
- **SSH to GitHub:** key registered as `john252525`. `ssh -T
  git@github.com` should return a greeting. If not, cannot push.
- **Docker:** installed but containers blocked (cgroup remount denied
  in sandbox). Prometheus/Grafana run as host-native tarballs under
  `/opt/prometheus` and `/opt/grafana` instead.
- **Python:** system `python3` = 3.10.12; venv `.venv` uses py 3.11.17
  via `/root/.local/share/uv/python/...`. `uv` at `/root/.local/bin/uv`.

### Team context

- **`form4-builder`** and **`pipeline-integrator`** agent slots are
  alive. Use them for UI/config-heavy work if available.
- **`qa-paper-verifier`** and **`event-driven-researcher`** agent slots
  are dead (echo / max-tokens failures). Do not attempt to route work
  through them.

### Format rules

- **Bash blocks parse and execute automatically.** Do not wrap commands
  in markdown triple-backticks inside bash blocks when producing output
  that is meant to be copy-pasted — the outer block is the delimiter.
- **JSON responses must be valid JSON only** — no markdown fences, no
  prose around the JSON. If replying with a tool-call argument, ensure
  the payload is parseable JSON.
- **`system_prompt` is immutable** across the session. Do not assume you
  can renegotiate the task rules mid-session.
- **No python heredoc** (`python3 - << EOF`) — use `python3 -c '...'` or
  `cat > file << 'MARKER' ... MARKER` instead.

### Do NOT attempt without user confirmation

- Force-push to any branch other than the one being worked on.
- Delete or reset `origin/structural-edge` (it is the decision-briefing
  branch).
- Deploy live capital. All signals are paper-trade only until the user
  approves live deployment.
- Change `state/short_13d.db` (the 90 open positions). Read-only until
  exits trigger.

### What to do if this file is stale

If any number in Section 1-5 seems inconsistent with reality on the
server, trust the server (`git log`, `sqlite3`, `systemctl`), not this
file. This file is a snapshot; the server is truth.

---

## End of transmission

Prepared 2026-10-18/19, on canonical server 109.172.6.35.
Next reader: resume from Section 6. Do not restart research; do not
re-audit closed strategies; wait for user decision on Section 4.
