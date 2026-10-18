# Legal Brief Template

To be sent to 2 lawyers: (1) EU IP/data specialist, (2) US commercial/
regulatory specialist. Budget $8-15k, 2-3 weeks turnaround.

## Company profile

We are a quantitative research desk (2-5 people) evaluating acquisition
of exclusive or near-exclusive licenses to alternative data feeds for
use in systematic trading. Estimated license budget: $1-2M per year
across 2-4 vendors. Intended use: trade for own account and possibly
provide signal-level products to affiliated funds. Jurisdictions of
interest: US (primary trading), EU (secondary), Switzerland (potential
holding). Team in [jurisdiction]. No existing licensed entity in
EU/US as a regulated broker-dealer, investment adviser, or CASP. If
that changes, it will be a separate legal track.

## Questions (10)

### Data Acquisition & Redistribution

1. For a license to a consumer transaction data panel (US credit/debit
   card data from a vendor that aggregates via card-issuer partnerships),
   what jurisdiction-specific rules apply to internal trading use?
   What changes if we resell a derived signal to one or two affiliated
   funds? Specifically: is the answer different for (a) raw records
   (nearly never acceptable), (b) unmasked aggregate records (likely
   acceptable if derived), (c) model outputs (most flexible)?

2. How does EU Data Governance Act (2022) and DSM Directive (2019/790)
   define "derived data" for a case of, say, a foot-traffic-derived
   earnings-predictor signal we compute ourselves? Where do the rights
   of the vendor, the underlying data subject, and the model owner
   fall in that chain?

### GDPR and Personal Data

3. For an AIS-shipping feed where vessel-identity is resolvable and
   owner-company is per IMO rules public, does any element of the feed
   constitute "personal data" under GDPR Art. 4(1)? Specifically, if we
   infer commercial behavior of a sole-trader owner, does the personal-
   data regime apply?

4. For EU card-transaction panel data, is legitimate-interest legal
   basis (Art. 6(1)(f)) viable for our downstream use if the vendor
   claims legitimate interest as their legal basis? Or are we required
   to have independent legal basis for the same data? How does EDPB
   recent guidance (2023, 2024) read on this?

### Scraping and Precedent

5. App Annie (SEC 2021, $10M settlement) was focused on
   misrepresentation of how data was obtained, not the use of alt-data
   per se. Under what specific facts could an alt-data vendor's
   misrepresentation become our liability if we relied on their
   data-as-represented? What warranties shield us?

6. HiQ Labs v. LinkedIn (9th Cir. 2022) held scraping public pages
   doesn't violate CFAA, but contract claims survived. Does purchasing
   from a scraped-data vendor leave us exposed to a chain-of-title
   problem, and what contractual language converts vendor's risk into
   vendor's obligation (indemnity) vs. our residual risk?

### Defense, Secrets, and Cross-border

7. Satellite imagery at sub-25cm resolution is ITAR-restricted for
   sale; at 25cm it's not. If our feed aggregates sub-25cm imagery from
   a non-US operator (ICEYE, for example), do US re-export rules
   apply to our downstream analysis? What is the practical clean-zone
   for a research shop using commercial-grade imagery?

8. What is the required posture on EU/US/Swiss data residency for
   exclusive-license contracts? Does the Schrems II / SCC regime impose
   an obligation on us as a data importer if the vendor is in one
   jurisdiction and we compute in another?

### Structure and Tax

9. For AML/KYC: alt-data vendors are not typically financial
   institutions, so AML does not attach to the transaction itself. But
   if our downstream trading entity is a regulated adviser, do alt-data
   payments fall within the adviser's books-records requirements under
   any jurisdiction we operate in? Practical compliance implications?

10. Best structure for exclusive-license payments: pay as a cost
    (expensed) at entity level, or capitalize the license as IP
    (depreciated, transfer-priced if multiple entities)? What are the
    downstream effects on our ability to assign the license in a sale,
    sub-license derived signals, or restructure teams?

## Expected deliverables from lawyers

- Written memorandum, 8-12 pages, addressing all 10 questions with
  concrete answers (not just "it depends")
- Term sheet framework with clauses modelling the 9-point LOI checklist
  from DATA_EXCLUSIVITY_SCOPE.md
- Risk statement: three highest-risk items, quantified where possible
  (probability estimate, financial exposure estimate)
- Recommendation: proceed, proceed with constraints, or do not
  proceed (with alternative)

## Budget and timeline

- Budget: $8-15k (US lawyer $5-10k, EU lawyer $3-5k, or $10-15k for
  one cross-border specialist)
- Timeline: 2-3 weeks for first draft, 1 week for return after Q&A
- Deliverable: Word/PDF, direct to us, not through third party

## Critical gate question

Before the lawyers begin, agree on the specific question that determines
proceed/no-proceed:

Do not start the LOI track unless the legal memos conclude that:

(a) an exclusive license to at least one of {AIS shipping data, card
    transaction data (US only), or corporate filings scraping} is
    legally defensible in at least one of the two jurisdictions, AND
(b) resale of derived signals to 1-3 affiliated funds is allowed
    without triggering financial-services licensing or GDPR
    third-party-transfer complications.

If both (a) and (b) do not hold, the Data Exclusivity recommendation
fails at Week 1 gate and we pivot to the contingency EM-local track
(Recommendation #2 from RECOMMENDATION.md). The $8-15k legal spend is
sunk-cost acceptable; the LOI spend of $500k+ is not.
