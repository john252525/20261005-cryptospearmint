# Structural Edge Landscape

## Executive Summary

For two decades quantitative research delivered alpha through statistical
anomalies: cross-sectional momentum, funding carry, post-earnings drift,
spin-off arbitrage. Each exploited a stable pattern that persisted because
information travelled slowly and capital arrived later. That era is closing.

Recent measurements confirm it. Funding carry across 20 years registers
Sharpe 0.17 — indistinguishable from noise once annualized and net of
cost. Post-earnings drift traces the decay curve most cleanly: Sharpe 0.70
across the full 1990-2020 sample, 0.30 in 2015-2019, and -1.15 in 2021-2023
as the window narrows. Spin-off long-short at median -2.38% with a t-stat
of 1.24 (not significant at 5%) shows the event-driven book has already
inverted. These are category failures, not strategy failures — the market
has eaten the category.

Structural edge is different in kind. Its source is a legal, physical, or
relational barrier: a license, a warehouse, a bilateral credit line, a
named counterparty relationship, an exclusive data feed. Each takes 6-36
months and a specific skill set to acquire. None can be replicated by
adding capital to an algorithm. The barrier is the business model, not the
signal. The unit of analysis is not the strategy but the jurisdiction, the
counterparty, and the balance sheet.

Five categories follow. For each: what the edge is, why it is structural,
who captures it today, how a 2-5 person research team with $5-50M could
enter, and what would kill the thesis. Ranking and recommendation are in
COMPARISON_TABLE.md and RECOMMENDATION.md.

---

## Category 1 — Jurisdictional Arbitrage (MiCA, MAS, VASP)

### What it is and where the edge lies

A license in one regulatory jurisdiction opens access to a specific
customer flow, asset class, or product set legally unavailable to
unlicensed operators. The market is access itself, not price.

EU MiCA (Regulation 2023/1114) is the leading example. Fully in force for
Crypto-Asset Service Providers since 30 December 2024; grandfathering for
pre-existing operators ends 1 July 2026. Any entity offering crypto
custody, exchange, portfolio management, transfer, or advice to EU
residents after that date must hold a CASP authorization from a national
competent authority — MFSA Malta, CySEC Cyprus, CSSF Luxembourg, BaFin
Germany, AMF France, or similar.

Singapore is the parallel: MAS Payment Services Act (PSA) covers digital
payment token services; Securities and Futures Act (SFA) covers custodial
and dealing activity. The combined CMS + PSA license is required for a
fully licensed exchange.

Quantified edge: licensed CASPs capture 40-70% gross margin on custody,
exchange fees, and regulated staking. In each jurisdiction they face 2-5
licensed competitors versus unlimited offshore UIs. The user has no
alternative once enforcement binds — ESMA has signalled active enforcement
from mid-2026.

### Why structural

The moat is legal, composed of:

- Application capital ($300k-2M depending on jurisdiction and scope)
- Regulatory relationship (fit-and-proper, board, MLRO, external audit)
- 6-18 months of approval during which existing operators enjoy protected flow
- Ongoing compliance staffing (2-4 FTE minimum for a licensed entity)

None of these can be acquired by statistical research. A team without them
cannot compete for the licensed flow regardless of model quality.

### Who plays

Listed: Coinbase (MiCA approval January 2025), Kraken (October 2024),
Bitpanda, Bitstamp. Custody: Zodia (Standard Chartered), Copper (Cayman),
Komainu (Jersey, backed by Nomura/Ledger/CoinShares). Asian: DBS Digital
Exchange (Singapore CMS+PSA), HashKey (Hong Kong VATP), OSL.

### How we enter

Cyprus (CySEC CASP) or Malta (MFSA Class 2/Class 3) is the cheapest
functional path into the EU. Budget $400k-800k to license plus $300-500k
per year ongoing compliance. Team requires: 1 senior compliance officer
with MiCA experience, 1 CTO with security/infra background, and the
existing research team.

Alternative: Cayman VASP (4-6 months, $150-300k setup, CIMA registered
auditor, AML program). Cheaper and faster, but non-EU commercial banks
generally refuse accounts without additional documentation. Recommended
only with offshore client base.

### Capacity for 2-5 team, $5-50M

Medium. Small licensed dealer viable at $2-5M capital. Licensed custodian
requires $5-15M setup plus $1-2M per year, viable at $50M+ AUM. Licensed
exchange requires $10M+ operational capital and 15+ staff — out of scope.

### Capital, competencies, time

- Capital at entry: $400k-800k setup, $300-500k per year, plus margin
- Competencies: compliance/regulatory heavy (60%), infrastructure (25%), research (15%)
- Time to first revenue: 10-14 months. To meaningful: 30-36 months.

### Kill criteria

- MiCA grandfathering extended by regulator to 2027+ (removes migration urgency)
- ESMA confirms CASP may outsource custody to non-licensed third parties (erodes custody moat)
- Enforcement against 2+ small CASPs for material breaches within 12 months of our launch

---

## Category 2 — Physical Commodity Trading

### What it is and where the edge lies

Buy physical, deliver physical. Margin comes from four sources: offtake
agreements (locked supply at discount to market), storage arbitrage (buy
low contango, sell into backwardation), freight arbitrage (buy in one
geography, ship), and credit lines ($500M-$2B trade finance at
sub-bank-rate costs).

Margin per move is thin — 0.5-2%. The book generates $200M-$1B profit on
$20B+ revenue for the largest houses. Volatility, not level, determines
capacity: 2022 (Ukraine war) generated record margins; 2020 (COVID) was
near zero.

### Why structural

No statistical edge — you are the physical counterparty. Barriers:

- Banking relationships: $500M-$2B revolving credit lines from top-tier
  banks. New entities cannot access these without 3-5 years of audited
  trade history.
- Physical infrastructure: terminals, storage tanks, freight contracts
  (time-charter or voyage). $50M-$500M commitments.
- Producer relationships: offtake contracts typically 3-10 years, started
  at CFO level.
- Basel III endgame (EU CRR3 implementing, US pending): 100-150% increase
  in commodity finance capital charge, favouring incumbents with existing
  lines.

Statistical models cannot substitute for a facility that physically holds
500,000 barrels.

### Who plays

Major trading houses: Vitol (~$505B revenue 2022), Trafigura (~$318B 2023),
Glencore (~$256B 2023), Mercuria (~$150B), Gunvor (~$120B), Cargill (agri).
Sovereign and state: Sumitomo, Mitsui, Unipec/PetroChina, Rosneft Trading,
Litasco (Lukoil). Chinese trade representatives in metals/agri increasingly
direct. Indian: Reliance Trading, Adani.

### How we enter

Metals concentrate (copper, zinc, cobalt, lithium intermediate) is the only
category where $10-30M working capital can access a specific offtake —
e.g., zinc concentrate from a mid-tier mine in Peru or South Africa via
2-3 year offtake, sold to a smelter in China or Korea. Requirements:

- 1-2 senior traders with 10+ years in the specific metal
- Chinese smelter relationship (Korea Zinc, Nyrstar, Glencore smelters)
- Trade finance line ($10-30M at SOFR+300-500)

Agri niche: 20k-50k tonnes of a specific origin (Brazilian coffee, East
African pulses) via 1-2 offtake contracts. Lower capital ($3-10M), smaller
margin, highly seasonal.

LNG small parcel: spot cargoes of 3-5 kt via NW Europe terminals. $30M+
capital due to ship charter.

### Capacity for 2-5 team, $5-50M

Low. Metals is the only realistic modality, requiring 2-3 experienced
physical traders hired away from majors. Team of 2-5 suffices for trading
only — needs outsourced ops (shipping agent, inspection). $20-30M working
capital minimum.

### Capital, competencies, time

- Capital: $20-30M metals, $30-50M LNG, $5-15M agri niche
- Competencies: physical trading 70%, ops/logistics 20%, research 10%
- Time: 18-36 months to first meaningful trade; 3-5 years to profitability

### Kill criteria

- Bank line at $15M+ unavailable after 6 months of negotiation (deal dead)
- Target commodity supply tightens, concentrate inventory at historic lows
- Basel IV implementation increases trade finance capital charge >150% by 2026

---

## Category 3 — Emerging Market Local Operations

### What it is and where the edge lies

Local licenses plus local relationships in high-growth EM markets —
Vietnam, Indonesia, Nigeria, Brazil. Edge is not quantifiable downstream;
it is presence in language, local counterparties (pension funds, family
offices, insurers), and regulatory proximity.

Vietnam: State Securities Commission (SSC) license for securities firm,
State Bank of Vietnam (SBV) for FX and capital operations. 100+ licensed
firms, top 20 capture 70% of flow.

Indonesia: OJK license for securities firm, IDX listings. One of the
fastest-growing exchanges globally, retail participation 60%+, foreign
ownership caps in many sectors.

Nigeria: SEC license for fund manager, NGX listings. 220M population,
nascent capital markets, FX regime uncertain (NGN devalued 60%+ 2023-24).

Brazil: CVM license for brokers, managers, advisors, B3 listings.
Tax-neutral FIA structure. BRL currency.

### Why structural

No algorithmic entry. Requirements:

- Local partner (typically 30-49% equity for foreign entrant)
- Residency and office in-country (regulatory requirement in all four)
- Language fluency (Vietnamese, Bahasa, Portuguese; Nigeria English but
  market-specific)
- Relationship capital with 3-5 anchor local counterparties

Not scalable via algos; not replaceable by capital alone.

### Who plays

Vietnam: VinaCapital ($4B AUM), Dragon Capital ($4.5B), SSI (brokerage),
VNDirect. Indonesia: Mandiri Sekuritas, BCA Sekuritas, Trimegah, Sucor.
Nigeria: ARM Group, Stanbic IBTC, CardinalStone. Brazil: BTG Pactual
($50B+), XP Inc, Itaú BBA, Genial.

### How we enter

Option A: acquisition of 30-49% stake in existing local manager — $2-10M
depending on country and scale. Retains local CEO/team; we supply strategy,
product, foreign capital.

Option B: joint venture with 1-2 senior local executives leaving existing
firms. Slower, more controllable. 12-24 months to operational.

Option C: sub-advisory to local licensed entity. Cheapest entry, captures
only 20-40% of margin.

For a 2-5 team, Option A in Vietnam (below VinaCapital scale) or Brazil
(small/mid-cap CVM-licensed manager) is realistic.

### Capacity for 2-5 team, $5-50M

High. $2-5M gets meaningful slice of a $200M-$1B local manager. Team can
leverage partner for ops, compliance, back-office, distribution. Our team
provides research, tactical allocation, foreign capital access.

### Capital, competencies, time

- Capital: $2-5M (JV) or $5-10M (stake)
- Competencies: local partner 60%, our research 40%
- Time: 6-12 months operational; 12-24 months to revenue

### Kill criteria

- Partner walks / governance breakdown within 12 months of JV
- Capital controls tighten (Vietnam has restricted foreign lending further
  in 2024-25; if capital outflow controls extend to LP remittances, model
  breaks)
- Currency devaluation >20% annually destroying USD returns over 2 quarters

---

## Category 4 — Market Infrastructure (exchange seat, clearing, custody, PB)

### What it is and where the edge lies

Own the plumbing. Exchange membership, clearing membership, custody, prime
brokerage — the revenue goes to the infrastructure operator and to direct
members, not to clients paying fees.

Access versus intermediary:

- Direct exchange member (CME, NYSE, Eurex) pays one-time setup plus no
  per-trade cost
- Clearing member holds margin at the CCP, captures financing spread on
  client margin, is counterparty of first resort
- Custodian holds client assets at 5-15 bps/year AUM, earns FX on cash
- Prime broker bundles custody, financing, clearing, execution — 15-30 bps
  on hedge fund AUM

### Why structural

Regulatory and capital moat:

- SRO/exchange membership: fit-and-proper test, minimum net capital ($5M+
  CME full member), 12-18 months regulator approval
- Clearing member (EMIR EU, Dodd-Frank US, Basel III): $5-15M minimum
  regulatory capital, daily margin, resolution planning
- Custody regulated under MiCA CASP, MAS CMS, EU MiFID: segregated
  accounts, insurance, third-party audits

No algorithm acquires a clearing member slot or a custody license.

### Who plays

Market makers relying on direct access: Citadel Securities (largest DMM
NYSE), Jane Street (fixed income MM), IMC, Optiver, Flow Traders, XTX
Markets. Exchange groups increasingly self-operate infrastructure: CME,
ICE, Eurex. Prime brokers: Goldman, Morgan Stanley, JP Morgan, BNP
Paribas, Deutsche Boerse (Clearstream), Euroclear.

### How we enter

Direct exchange membership: out of scope for 2-5 team with $5-50M. Minimum
requirements exceed capacity by 2-5x.

Recommended alternative: crypto custodian (Jersey or Cayman VASP) —
$2-5M setup plus $500k-1M/year, providing custody to hedge funds and
family offices.

Second alternative: clearing member on smaller exchange (EEX Power
Derivatives for carbon/renewables, ICE Endex for EU gas) — $5-10M
regulatory capital, 8-12 months setup.

### Capacity for 2-5 team, $5-50M

Very low. Direct membership: no. Crypto custodian: partial yes, but a
business-model shift requiring secops and ops leadership. Exchange-specific
clearing: possible but requires experienced operations head.

### Capital, competencies, time

- Capital: $5-15M regulatory (direct), $2-5M (crypto custodian)
- Competencies: regulatory/ops 70%, tech/security 20%, research 10%
- Time: 12-24 months setup; 24-36 months to break-even

### Kill criteria

- Exchange reduces membership barrier under competitive pressure (crypto
  venues with 10x lower fees) — moat collapses
- Additional Basel IV capital requirement imposed ($5-10M further)
- Client concentration: 2+ of top-5 clients leave within first year

---

## Category 5 — Data Exclusivity

### What it is and where the edge lies

Exclusive or near-exclusive license to proprietary data, or internal
generation. Two forms:

- License: pay $500k-2M/year for exclusive rights to a vendor feed
  (specific country credit-card panel, specific port AIS, specific
  satellite corridor)
- Generate: build proprietary panel (e.g., 50k consumer receipts via
  partnership with a retail chain; 20 satellites for global oil storage
  monitoring)

Edge is information asymmetry. With 3-5 firms sharing the feed, alpha is
1-2% annualized; with 1-2 firms, 3-6%. Realized by trading (long-only,
long-short, or overlay) or by reselling the feed ($100-500k per year per
client).

### Why structural

Contractual. Exclusive license terms negotiable for 1-3 years. Once
signed, no other firm can buy the same feed from that vendor. Not
replicable by algorithm because the data itself is the barrier — you
cannot compute it from public sources at similar latency without the
underlying right or panel.

### Who plays

Alt-data: M Science (consumer transaction), YipitData (US consumer),
Orbital Insight and Kayrros (satellite), Spire and HawkEye 360 (RF), Kpler
(shipping), TankerTrackers (AIS oil). Commodity info: Platts, Argus, ICE.
Crypto on-chain: Nansen, Glassnode, Arkham, Chainalysis. Data brokers:
Bloomberg (BEST), Refinitiv, FactSet.

### How we enter

Step 1: identify 3-5 data categories where vendor margin is high and
customer concentration is low (non-US port AIS, specific commodity
shipment data, specific country consumer transaction, specific exchange
order book depth).

Step 2: negotiate 1-3 year exclusivity in exchange for guaranteed annual
buying commitment ($500k-2M). Vendor gets certainty; we get exclusivity.

Step 3: integrate into research pipeline; measure realized alpha
(backtest + paper) before deploying capital.

Step 4 (optional): re-license to 1-3 other funds after first-year track
record.

### Capacity for 2-5 team, $5-50M

High. Perfect scaling — research team buys feed, integrates, extracts
alpha, adds feeds. Compounding across strategies and asset classes.

### Capital, competencies, time

- Capital: $500k-2M/year per exclusive feed; 2-3 feeds for critical mass
- Competencies: research and data integration 70%, contract negotiation 30%
- Time: 3-6 months to first signal; 6-12 months to meaningful alpha

### Kill criteria

- Vendor offers same feed to 5+ additional clients within 12 months
  (breaks exclusivity)
- Realized alpha <1% annualized on $10M+ traded after 6 months live
  (economics fail)
- Legal basis of feed revoked (privacy action, ITC/takedown, regulator
  ruling) within 18 months

---

## Cross-cutting notes

Three forces apply to all categories:

- Basel IV implementation (EU 2025, US 2026 pending): increases capital
  charges on commodity finance and clearing, favouring incumbents
- Regulatory divergence (MiCA vs. US SEC vs. MAS): drives cross-border
  arbitrage in the 2-4 years remaining before convergence
- AI-driven commoditization of research: reduces value of any strategy
  based on public data; increases value of proprietary data and licensed
  access

For a 2-5 person research team with $5-50M, categories 1, 3, and 5 are
executable in 6-24 months; categories 2 and 4 require partnership or
capital beyond scope. Ranking and recommendation follow in
COMPARISON_TABLE.md and RECOMMENDATION.md.
