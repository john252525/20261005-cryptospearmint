# Data Exclusivity — Week 1 Legal Scope

## Executive Summary

Ranking in COMPARISON_TABLE.md places Data exclusivity at #1 (21/25). But its
edge score is 3/5, the weakest of five categories. Data exclusivity is a
contractual moat, not a legal or physical one. It holds only if the vendor
agrees to terms that prevent the same slice being sold to 5 other funds.
Without an enforceable exclusivity clause, the category collapses into plain
commodity alt-data.

Week 1 exists to answer three questions before committing $8-15k to legal:

- Which verticals are worth signing? Eight candidates exist, each with
  different cost, legal exposure, and time-to-signal. Some are disqualified
  by regulatory regime before any LOI is discussed.
- What exact legal form must the LOI take for the moat to hold across
  jurisdictions? EU and US regimes differ materially on redistribution and
  derived data.
- What is the go/no-go verdict path? Even a "yes" from lawyers has to be
  consistent with unit economics at $1-2M/year licensing budget.

Deliverables this week:

- Scope of work document (this file) sent to 2 lawyers (IP + commercial)
- Legal brief template (LEGAL_BRIEF_TEMPLATE.md) with 10 targeted questions
- Vendor shortlist (VENDOR_SHORTLIST.md) with 15-20 candidates and public
  cost signals
- Budget: $8-15k legal, 2-3 weeks for turnaround
- Decision gate: proceed to LOI only if two vendors accept 6-month
  exclusivity trial terms AND legal memo confirms redistribution rights in
  at least one major jurisdiction (US or EU)

---

## Section 1 — Credit / Debit Card Transaction Data

### Provider examples

Consumer Edge (New York, ~$50M funding, consumer transaction panel,
~50-100M cards weekly), Second Measure (acquired by Bloomberg 2020),
Earnest Analytics (New York, credit card transaction panel, direct-to-fund
distribution), Cardify (Sydney-based, smaller panel), Facteus (Oregon,
transaction data).

### Cost signal

$500k-$2M per year for exclusive-panel access, tiered by:
- panel size (unique cards, refreshed weekly vs monthly)
- refresh cadence (daily ~2-3x price of weekly)
- historical depth (3+ years adds ~30-50%)
- geography (US-only cheapest; global 2-4x)
- exclusivity term (single-client slice 3-5x base; multi-client base)

### Exclusivity model

Typically sold as a "custom slice" — vendor constructs a panel subset
(geographic, demographic, merchant category) matching client's universe.
Exclusivity defined on that slice:
- Look-through: same underlying card IDs not resold to anyone else
- MFN: if vendor sells larger panel next quarter, base price adjusts
- No-redistribution: client may not redistribute underlying data, only
  derived signals; derived signals reusable internally

### Legal risk

Medium-high in EU, medium in US:
- US: legal basis is card issuer consent (each issuer's ToS permits
  anonymized resale). Panel is deidentified under CCPA/HIPAA-safe-harbor
  rules once stripped to ZIP3 + category code + timestamp. Enforcement
  precedent: App Annie 2021 (see precedent section).
- EU: GDPR Art. 4(1) — anonymization legally hard; "pseudonymized" data
  remains in scope. Schrems II limits US-vendor processing of EU card
  data. Most vendors restrict EU card panel availability.
- Practical: US-panel only is standard fund offering; EU panel typically
  unavailable or requires separate local vendor.

### Duration-to-signal

3-6 months from first call to first tradeable signal in backtest.

---

## Section 2 — AIS Shipping Data

### Provider examples

MarineTraffic (Greece, global AIS network, ~$300M revenue via
Kpler acquisition 2023), Spire Global (NYSE: SPIR, satellite AIS),
Kpler (merged with MarineTraffic, commodity trade flow analytics),
Windward (LL, maritime intelligence), Pole Star (defense-grade).

### Cost signal

$200k-$1M per year, tiered by:
- coverage (SAT-AIS or terrestrial-only; SAT is 2-4x)
- refresh (real-time vs historical)
- historical depth (5+ year history adds 50%)
- port/region filter (commodity-tied ports vs global)
- exclusivity (rare; usually sold on MFN instead of true exclusivity)

### Exclusivity model

Most AIS venders avoid strict exclusivity because AIS is technically
public (vessels broadcast openly). What's exclusive is:
- Enrichment layer (vessel identity resolution, cargo estimate,
  destination prediction)
- Latency (real-time vs delayed-24h)
- Raw feed access (they operate ground stations)

Practical model: "signal exclusivity" on a specific derived signal, not
raw AIS.

### Legal risk

Low-medium:
- AIS is broadcast openly; reception/resharing legal in most jurisdictions
- IMO privacy rules: historical AIS anonymized after 90+ days per IMO
  resolution; live data unrestricted
- Port access: ground stations in ports require cooperation (berth access,
  electricity); not a legal barrier, ops barrier
- Defense exposure: sub-set of AIS (military vessels, sanctioned vessels)
  restricted by local law; check where vendor's ground network sits

### Duration-to-signal

2-4 months. Signal quality depends on target commodity — crude oil
tankers well-tracked; dry bulk harder.

---

## Section 3 — Consumer Transaction via Web Scraping

### Provider examples

Similarweb (NYSE: SMWB, web traffic panels, ~$200M revenue),
Sensor Tower (mobile app store data), Thinknum (web-scraped
corporate metrics), YipitData (aggregated consumer panel from web
scraping + panel).

### Cost signal

$300k-$1M per year. Pricing varies widely by data depth:
- web traffic only (Similarweb): $100-300k
- app store + engagement (Sensor Tower): $200-500k
- transaction-scraping (YipitData alternative methods): $500k-1M

### Exclusivity model

Weak. Because the underlying method is scraping, competitors can scrape
too. Vendor cannot offer true exclusivity because the source is
recoverable by anyone with the same scraping infrastructure. What works:
- "Vertical exclusivity": only one client in a defined industry
- "Timing exclusivity": fresher update as first-look
- "Custom enrichment": vendor builds derived product only for client

### Legal risk

Medium-high:
- ToS violation: scraping violates ToS of most consumer platforms.
  Legal tests: hiQ Labs v. LinkedIn (9th Cir 2022) found scraping
  public data does not violate CFAA, but does not immunize from
  breach-of-contract claims.
- GDPR post-Schrems II: EU personal data from scraped web sources
  requires explicit legal basis; legitimate interest claims historically
  rejected for consumer population data.
- Practical: US-based scraped data more defensible; EU scraping
  increasingly reframed as personal data processing requiring consent.

### Duration-to-signal

1-3 months, faster than physical panels because turnaround shorter.

---

## Section 4 — Satellite Imagery / Geolocation

### Provider examples

Maxar Technologies (NYSE: MAXR, high-res optical), Planet Labs (NYSE: PL,
daily global optical, ~200 satellites), Orbital Insight (analysis overlay,
San Francisco), Kayrros (energy-tuned satellite analytics), Iceye
(SAR, Finland), Ursa Space (marketplace).

### Cost signal

$500k-$2M per year, highly variable:
- raw imagery (Planet subscription): $100-500k
- analytic product (Kayrros, Orbital Insight): $500k-2M
- custom tasking (Maxar specific orbits): $1M+ per shot
- SAR imagery: 2-4x optical for same coverage

### Exclusivity model

Genuine exclusivity possible for:
- Tasking windows: reserve specific orbit/time slot only for one client
- Analytic access: single-client derived product
- Raw imagery less often exclusive because satellite operators sell to
  multiple downstream partners

### Legal risk

Medium:
- Satellite imagery from commercial operator is not state-secret by
  default; export controls (ITAR) matter if client uses for sensitive
  end-effects.
- Resolution restriction: US commercial imagery capped at 25cm for
  unrestricted sales; sub-25cm requires NGA approval.
- Defense exposure: analyzing within 100km of military installations
  (naval bases, missile sites) may trigger state-secrets concern; needs
  careful scope in LOI.
- Privacy: individual-person imagery via commercial satellite is not
  GDPR-relevant (public space, purpose not identification), but
  aggregation into person-tracking analytics does trigger GDPR.

### Duration-to-signal

3-9 months. Tasking cycles are long (weeks to orbit), analytics build
takes 2-3 months more.

---

## Section 5 — On-Chain Crypto Data

### Provider examples

Glassnode (Switzerland, on-chain metrics), Nansen (Singapore,
wallet-labeling + on-chain analytics), Amberdata (US, institutional
on-chain plus derivatives), Chainalysis (compliance focus, less
directly relevant), Arkham (wallet deanonymization, controversial).

### Cost signal

$100k-$500k per year:
- basic on-chain aggregate (Glassnode tier): $50-150k
- labeled-wallet database (Nansen): $150-400k
- institutional derivatives + on-chain (Amberdata): $300k-500k

### Exclusivity model

Rare. On-chain data is public by construction. Value is in:
- Derived metrics (SOPR, MVRV, holder cohorts): proprietary formulas
- Wallet labeling (Nansen): proprietary database, not resellable
- API + historical snapshot: standard commercial products, not exclusive
- True exclusivity: only via contract that vendor won't sell to
  competitors in-niche; rare and usually priced 3-5x base

### Legal risk

Low-medium:
- On-chain data is public; aggregation not restricted
- MiCA implications: if using data for trading decisions in EU,
  CASP-licensed entity may need to treat as "market data". Our position:
  not licensed, no EU clients directly, so not MiCA-regulated as CASP.
- KYC/AML: vendor's own obligations (if vendor sells labeled IDs to
  sanctioned parties, they carry risk). Our risk: understand vendor's
  origination method.

### Duration-to-signal

2-4 weeks. On-chain integration is fastest of all eight — APIs mature,
schema well-documented.

---

## Section 6 — Phone Geolocation

### Provider examples

SafeGraph (US, POI + mobility, panel-based), Placer.ai (foot traffic,
US-focused), Advan (formerly UberMedia, US phone geolocation),
Unacast (foot traffic, US).

### Cost signal

$200k-$1M per year:
- POI dataset (SafeGraph Places): $100-400k
- foot traffic + patterns: $200-500k
- panel-level geolocation: $500k-1M
- exclusivity surcharge (rare): +100-200%

### Exclusivity model

Usually MFN only. Panel is aggregated from SDKs in third-party apps;
vendors cannot guarantee no other buyer sees same panel. What can be
exclusive:
- Custom vertical filter
- Derived product under NDA
- "First look" timing advantage

### Legal risk

HIGH — highest of all eight verticals:
- GDPR Art. 9 (special category data): geolocation in continuous form
  can infer religion (mosque visits), health (clinic visits), sexual
  orientation (bar visits). Requires explicit consent, not just
  legitimate interest.
- GDPR Art. 6 legal basis: legitimate interest historically rejected for
  panel-based geolocation in EU after 2020 CNIL enforcement (Google
  Mobility Reports controversy; Yahoo/WhatsApp cases).
- EU regulatory climate: 2023 EDPB opinion on geolocation explicit
  consent requirement; enforcement active.
- US: CCPA has opt-out for "sale of personal information", geolocation
  data sale is high-risk category; state AGs (CA, TX) actively
  enforcing 2023-2024.
- Practical: US-only viable with careful vendor; EU-only impractical
  without vendor providing explicit consent panel.

### Duration-to-signal

2-4 months for US panel; EU panel likely unavailable at any price
without vendor's explicit consent framework.

---

## Section 7 — Corporate Filings NLP

### Provider examples

Open source: SEC EDGAR (US), Companies House (UK), Handelsregister
(DE), Sirene (FR), ASIC (AU). Commercial overlay: Intrinio, XBRL US,
Datalog (Japan filings, now part of FactSet), BamSEC.

### Cost signal

$50k-$200k per year:
- raw filings data: free
- derived structured (XBRL tags normalized): $20-100k
- ML enrichment (sentiment, entity resolution): $100-200k
- true exclusivity: impossible (filings are public record)

### Exclusivity model

None. Filings are public-record. Edge is in speed-of-processing and
quality of NLP extraction, not data access. "Exclusivity" doesn't apply;
better framing is "proprietary extraction pipeline".

### Legal risk

Lowest of all eight:
- Filings are public record, no privacy or IP issue in extraction
- Restrictions: only if aggregating into product that resells filings
  themselves (that's redistributing public data, allowed but competitive
  with free sources)
- No GDPR, no state-secrets, no ToS issues

### Duration-to-signal

Weeks. Integration is well-understood; opportunity is in NLP quality
and speed, not data access.

---

## Section 8 — Industry-Specific Surveys / Positioning

### Provider examples

CFTC Commitments of Traders (public, weekly), ICE COT, hedge fund
positioning aggregators (mostly estimated via 13F filings), sell-side
consensus (Refinitiv I/B/E/S, FactSet Estimates, Bloomberg BEST),
non-public: specialized surveys via industry associations.

### Cost signal

$100k-$500k per year:
- CoT + public filings: free
- sell-side consensus data (FactSet, Refinitiv): $100-300k
- specialized positioning data (some vendors): $200-500k
- true non-public survey: rare, vendor-dependent

### Exclusivity model

Available but constrained. Sell-side consensus aggregates mostly
already published; exclusive access would mean:
- timing advantage (first-look at updated consensus)
- deeper cut (beyond top-line, into analyst-level detail)
- geographic exclusivity (non-US markets less covered)

### Legal risk

Medium:
- MAR (Market Abuse Regulation EU): trading on non-public
  survey/positioning data risks insider-trading classification if data
  reflects collective intention of specific named parties.
- Reg FD (US): if survey aggregates material non-public info about a
  public company, disclosure rules apply.
- CFTC COT data: public, safe.
- Practical: aggregated/estimated positioning is safe; specific
  fund-level positions from surveys are risky.

### Duration-to-signal

2-6 weeks. Aggregation of public data is fast; bespoke non-public
surveys take months to establish.

---

## Precedent Cases

### App Annie — SEC Enforcement September 2021

Context: App Annie (now data.ai) scraped app-store data and sold
anonymized app analytics to hedge funds and other clients. SEC charged
App Annie and its co-founder/CEO with securities fraud in September
2021; settled for $10M penalty.

Relevance: enforcement was under Section 10(b) of the Exchange Act —
specifically, misrepresentation of how the data was obtained. App
Annie told clients the data was from a curated panel of opt-in users;
in fact, it was scraped from app stores in violation of ToS, sometimes
with real user identities extractable. The SEC's case was not that
alt-data is illegal, but that misrepresenting data provenance to
clients buying the product is securities fraud when used for trading
decisions.

Operational takeaway: source-of-origin warranty in vendor LOI is
non-optional. Our LOI must require vendor to warrant how data was
obtained and require audit right.

### HiQ Labs v. LinkedIn — 9th Cir 2022

Context: hiQ scraped public LinkedIn profiles; LinkedIn sent cease-
and-desist citing CFAA. District Court (N.D. Cal 2017) ruled scraping
public data not CFAA violation; 9th Cir affirmed 2019, then 2022 on
remand after Van Buren.

Relevance: scraping publicly-accessible data without login does not
violate CFAA (federal anti-hacking). But it does not immunize from
state-law breach-of-contract claims (ToS) — LinkedIn's contract claims
remained live. Final settlement 2022 (unspecified terms, hiQ ceased
scraping).

Operational takeaway: web-scraped alt-data (Section 3) needs
representation on ToS status. Scaraped-data vendor must warrant not
currently subject to injunction or active contract claim on the
specific URL/panel.

### Additional precedents to research in Week 1

- SEC v. hedge funds using credit-card panels (2020-2023): no public
  case yet, but SEC exam priorities 2024 list "alternative data use" as
  supervisory topic. Interpret as increased enforcement risk, not
  prohibition.
- FTC enforcement on geolocation data (2023-2024): X-Mode Social /
  Outlogic (settled Jan 2024), InMarket Media (settled Jan 2024).
  Relevant to Section 6.
- ICO UK guidance on alt-data (2023): guidance, not enforcement, but
  sets expectation for GDPR compliance.

---

## LOI Template Checklist

Nine clauses that determine whether exclusivity holds. Missing any of these
converts the contract into commodity data purchase at premium price.

1. **Exclusivity clause.** Specific: define the slice (geography,
   panel size, refresh cadence). Duration: 12-36 months preferred,
   6 months minimum. Scope: single-client-in-niche vs single-client-
   globally; first is cheaper, sufficient for our purposes.
2. **Most-favoured-nation (MFN).** If vendor sells larger panel or
   fresher feed to any other client, we get same terms at no additional
   cost. Standard in alt-data LOIs.
3. **Redistribution rights.** Explicit matrix:
   - internal analytics: unrestricted
   - derived signals (not raw records): resellable to affiliated
     entities, restricted to third parties
   - raw records: no redistribution to any third party
   This clause is what creates our downstream product optionality.
4. **Source-of-origin warranty.** Vendor warrants:
   - Data obtained with documentable legal basis
   - No active litigation, injunction, or regulatory investigation on
     the specific panel/method
   - Vendor will notify us within 5 business days if either changes
   Non-optional post-App Annie (see precedent section).
5. **Compliance audit right.** We may, once per year, request evidence
   of (a) source legal basis, (b) consent records for personal-data
   feeds, (c) applicable insurance coverage. Vendor must respond to
   reasonable audit.
6. **Termination triggers.** Automatic termination with refund of prepaid
   fees if:
   - Regulatory action invalidates legal basis
   - Vendor's data quality falls below defined SLA (missing data >5%,
     refresh delay >48h)
   - Breach of source-of-origin warranty
7. **Derived data definition.** Post-DSM Directive (EU 2019/790) —
   derived data must be defined at contract signature, listed
   exhaustively, so disputes over scope don't emerge at year 2 renewal.
8. **Data residency and cross-border transfer.** Where does the data
   physically sit? If EU domiciled, Standard Contractual Clauses
   required for transfer to US; if US domiciled with EU underlying
   data, Schrems II impact needs separate evaluation.
9. **Anti-assignment and change-of-control.** If vendor is acquired
   (as Second Measure by Bloomberg, MarineTraffic by Kpler), our
   exclusivity survives; new owner cannot resell to our competitors
   without triggering renewal-or-exit at our election.

---

## Top-3 Recommended Verticals for Team Profile

Scoring criteria: (1) cost/benefit — expected alpha per dollar of
license; (2) legal risk — highest risk disqualified; (3) signal-to-noise
— time-to-signal, integration effort, derivative optionality.

### Recommendation A — AIS Shipping (Section 2)

Cost: $200k-1M per year. Legal risk: LOW-MEDIUM (AIS broadcast openly;
IMO regulation clear). Signal-to-noise: HIGH. Duration-to-signal 2-4
months. Vendor landscape mature (MarineTraffic/Kpler combined, Spire
public, Windward public). Look-through exclusivity achievable on
derived metrics without paying for raw feed. Best fit: research team
integrating into commodities-tied equity or crypto-tied trading.

Rationale: covers a real gap in public knowledge (physical commodity
flows) without crossing personal-data or defense thresholds. Oil,
LNG, container flows detectable. Freight rates, tanker positioning,
port congestion all extractable at high SNR.

### Recommendation B — Credit/Debit Card Transactions (Section 1)

Cost: $500k-2M per year (US-panel only for risk containment). Legal
risk: MEDIUM (US panel safe; EU panel avoid for legitimate basis
ambiguity). Signal-to-noise: HIGH if backtest validates. Duration-to-
signal 3-6 months. Panel-based data (Consumer Edge, Earnest) has
longer history and cleaner than web scraping.

Rationale: highest raw alpha of the eight if signal works; US panel
avoids GDPR well. Constraint: highest licence cost, so signal must
clear Sharpe >1.5 in backtest to justify 18-month payback. Buy only
after full backtest on free vignette data (typically 3-6 month sample
available under evaluation license).

### Recommendation C — Corporate Filings NLP (Section 7)

Cost: $50-200k per year. Legal risk: LOWEST. Signal-to-noise: MEDIUM.
Duration-to-signal 2-4 weeks. Public filings accessible free; edge in
NLP quality and speed. Perfect "always-on" base layer even if other
verticals don't sign.

Rationale: zero-risk integration. Establishes data pipeline,
monitoring, and event-driven infrastructure reusable for other
verticals. Public-record only — no vendor LOI required, just internal
build. Good first-90-days project while LOIs on A/B progress.

**Combined portfolio strategy:**

- Weeks 1-4: Corporate filings NLP (C) built in-house; low cost, no
  vendor LOI.
- Weeks 1-4 parallel: AIS vendor LOI negotiation (A); preferred
  primary vertical.
- Weeks 5-8: card transaction vendor LOI (B) initiated only if A
  signs and pilot generates alpha; else double down on A.

Kill criteria for portfolio: exit entire data-exclusivity program if
after 6 months neither A nor B produce backtested Sharpe >1.0 on
$10M+ allocation and C's build cost exceeds $150k without deliverable
signal.
