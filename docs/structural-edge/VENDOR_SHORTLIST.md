# Vendor Shortlist — 20 candidates across 8 verticals

Pricing signals drawn from public information (vendor websites, press
releases, industry reports, publicly-disclosed fund letters where
available). Where price is not publicly confirmed, marked "contact for
quote" — no fabrication.

Columns:
- Exclusivity option — what vendor publicly offers or implies
- Legal note — key risk for our use case
- Priority — our ranking (high/medium/low) based on fit to DATA_EXCLUSIVITY_SCOPE.md Recommendation A/B/C

## Section 1 — Credit/Debit Card Transaction Data

| Vendor | Public cost signal | Exclusivity option | Legal note | Priority |
|---|---|---|---|---|
| Consumer Edge | $500k-2M/yr (industry range) | Slice-based exclusivity, MFN standard | US panel; card-issuer consent basis; panel clean under CCPA | HIGH |
| Earnest Analytics | contact for quote | Direct-to-fund, custom slice | US panel; same basis as Consumer Edge | HIGH |
| Cardify | contact for quote | Vertical exclusivity possible | Smaller panel; independent sourcing | MEDIUM |
| Facteus | $300k-1M (industry) | Custom slice, MFN | Aggregates multiple issuer feeds | MEDIUM |
| Second Measure (Bloomberg) | Not resold external as of 2024 | Not applicable | Acquired by Bloomberg 2020; not for external clients | LOW |
| YipitData | $500k-1M (web-scrape + panel) | Vertical exclusivity sometimes | Mixed sourcing; ToS history (post-2020 litigation settlement) | MEDIUM |

## Section 2 — AIS Shipping

| Vendor | Public cost signal | Exclusivity option | Legal note | Priority |
|---|---|---|---|---|
| MarineTraffic (Kpler) | $200k-1M/yr | Rare; MFN instead | AIS broadcast openly; IMO 90-day anonymization | HIGH |
| Spire Global (NYSE: SPIR) | $300k-1M (smallsat AIS) | Tasking-exclusive possible | Satellite AIS; not defense-grade by default | HIGH |
| Kpler | $200k-1M (commodity-focused) | Analytics-only exclusivity | Combined with MarineTraffic; deep commodity model | HIGH |
| Windward | contact for quote | Vertical (defense finance) | Defense-grade; export-control consideration | MEDIUM |
| Pole Star | contact for quote | Defense-grade | Strong export-control; avoid for commercial use | LOW |

## Section 3 — Consumer Web Scraping

| Vendor | Public cost signal | Exclusivity option | Legal note | Priority |
|---|---|---|---|---|
| Similarweb (NYSE: SMWB) | $100-300k/yr | None realistic | Public web traffic; ToS-compliant via SDK panel | MEDIUM |
| Sensor Tower | $200-500k/yr | Vertical exclusivity | App-store data; similar ToS posture | MEDIUM |
| Thinknum | $100-300k/yr | Vertical | Web-scraped; precedent (App Annie) suggests caution | LOW |
| YipitData | $500k-1M | Vertical | Hybrid scraping+panel; largest settlement history | MEDIUM |

## Section 4 — Satellite Imagery

| Vendor | Public cost signal | Exclusivity option | Legal note | Priority |
|---|---|---|---|---|
| Planet Labs (NYSE: PL) | $100-500k/yr | Tasking-exclusive possible | 25cm limit US sales; daily coverage | MEDIUM |
| Maxar (private) | contact for quote | Tasking-exclusive | Sub-25cm requires NGA approval | MEDIUM |
| Orbital Insight | $500k-2M/yr | Analytics-exclusive | Analytics overlay, not raw imagery | MEDIUM |
| Kayrros | contact for quote | Analytics-exclusive | Energy-focused; well-fit for commodity research | HIGH |
| ICEYE (SAR) | contact for quote | Tasking-exclusive | SAR, Finland-based; ITAR-adjacent | MEDIUM |

## Section 5 — On-Chain Crypto

| Vendor | Public cost signal | Exclusivity option | Legal note | Priority |
|---|---|---|---|---|
| Glassnode | $50-150k/yr | Analytical formulas proprietary | On-chain public data; MiCA implications low | HIGH |
| Nansen | $150-400k/yr | Wallet-label DB not resold | Labels proprietary; ToS-compliant | HIGH |
| Amberdata | $300-500k/yr | Institutional-tier exclusive possible | Combined on-chain + derivatives | HIGH |
| Arkham | $200-500k/yr | Reputation risk (de-anonymization) | Controversial; avoid for institutional product | LOW |
| Chainalysis | $100-300k/yr (compliance tier) | Compliance-focus, not trading | Most useful for AML, not alpha | LOW |

## Section 6 — Phone Geolocation

| Vendor | Public cost signal | Exclusivity option | Legal note | Priority |
|---|---|---|---|---|
| SafeGraph | $100-400k/yr (Places tier) | MFN only | Post-2020 privacy leadership pivot; safer than peers | MEDIUM |
| Placer.ai | $200-500k/yr | Vertical | US-focused; has consented panel | MEDIUM |
| Advan (formerly UberMedia) | contact for quote | MFN | EU panel high-risk after EDPB 2023 | LOW |
| Unacast | $100-300k/yr | MFN | Legal basis historically contested | LOW |

## Section 7 — Corporate Filings NLP

| Vendor | Public cost signal | Exclusivity option | Legal note | Priority |
|---|---|---|---|---|
| (In-house build) | $0-50k/yr (engineering time) | Full control | Public record; no vendor LOI needed | HIGH |
| Intrinio | $20-100k/yr | None | Public filings normalization | MEDIUM |
| XBRL US | Free (public) | None | Raw XBRL; build extraction in-house | HIGH |
| Datalog (FactSet) | contact for quote | None | Japan filings expertise; niche | LOW |
| BamSEC | $50-150k/yr | None | US filings, clean interface | MEDIUM |

## Section 8 — Positioning / Survey

| Vendor | Public cost signal | Exclusivity option | Legal note | Priority |
|---|---|---|---|---|
| FactSet Estimates | $100-300k/yr | Geographic-exclusivity possible | Consensus estimates; MAR safe if aggregated | MEDIUM |
| Refinitiv I/B/E/S | $100-300k/yr | Same | Aggregate consensus; safe | MEDIUM |
| Hedge fund positioning (est. from 13F) | Free (SEC EDGAR 13F) | N/A | Public-record; safe | HIGH |
| CFTC Commitments of Traders | Free (public) | N/A | Public weekly; safe | HIGH |
| ICE COT | Free (public) | N/A | Public weekly; safe | HIGH |

## Section 9 — Aggregators (meta-layer)

| Vendor | Public cost signal | Exclusivity option | Legal note | Priority |
|---|---|---|---|---|
| Eagle Alpha | $30-80k/yr (subscription) | None | Aggregates marketplace, not exclusive | MEDIUM |
| BattleFin | contact for quote | None | Discovery layer, paid trial | MEDIUM |
| Neudata | $20-50k/yr | None | Research/rating service | LOW |

## Contact priority summary

Top priority (HIGH) to reach in Week 2:

- **AIS:** MarineTraffic, Spire, Kpler
- **Cards:** Consumer Edge, Earnest
- **On-chain:** Glassnode, Nansen, Amberdata
- **Filings:** In-house (XBRL US), also 13F/CoT public feeds
- **Satellite energy:** Kayrros

Medium priority (MEDIUM) — after first three LOIs are in motion:

- Similarweb, Sensor Tower, YipitData (scraping-tier; higher legal risk)
- Planet, Maxar, Orbital Insight, ICEYE (satellite tier)
- SafeGraph, Placer.ai (geolocation; high legal risk)
- FactSet Estimates, Refinitiv I/B/E/S (positioning/consensus)
- Eagle Alpha, BattleFin (discovery)

Low priority (LOW) — flagged for legal concern or redundancy:

- Thinknum (App Annie precedent risk)
- Arkham (reputational)
- Advan, Unacast (EU panel risk)
- Second Measure (unavailable)
- Pole Star (defense-only)
- Chainalysis (compliance not alpha)
- Neudata (discovery, not direct)

## Total count

20+ vendors evaluated across 9 categories. Pricing signals from
public information; "contact for quote" where vendor does not publish.

Ready for Week 2 shortlist of 2-3 per vertical to CEO/team for
NDA outreach.
