# Vendor Outreach Template — Data Exclusivity

Status: activation-ready. Send only after the legal gate passes (see
LEGAL_EXECUTION_CHECKLIST.md Step 3). Cost figures quoted here come from
docs/structural-edge/DATA_EXCLUSIVITY_SCOPE.md and VENDOR_SHORTLIST.md; where a
vendor has no public price signal the template says "contact for quote" rather than
inventing a number.

---

## Initial Email Template

Subject: Data licensing inquiry — [Vendor] — exclusive arrangement

Body:

Dear [Name],

I am [Title] at [Our Company], a systematic investment manager running equity and
commodity signals with our own research and execution infrastructure. We are currently
evaluating data partners for a multi-year exclusive arrangement and your [Data Type]
product is on our shortlist.

Our intended use case is [use case, e.g. generating commodity-flow signals for listed
shipping and energy equities], with signals built entirely in-house and reused across
a small number of affiliated vehicles under common control. We are not a data reseller
and have no intention of redistributing raw data.

We are specifically interested in exclusivity or semi-exclusivity over a defined
slice — for example [vertical/geography] — rather than a standard multi-client
subscription. Please let us know whether that is something you offer today, and at
what tier.

Could you share indicative pricing for an annual arrangement with and without
exclusivity, and whether a historical data sample for backtesting is available before
signature? We would also welcome a 30-minute call in the next two weeks to cover your
product scope, sourcing and standard contract terms.

On our side, a signed LOI and a legal review are already prepared and we can move
quickly once we have clarity on pricing and exclusivity. We expect to make a vendor
decision within four to six weeks.

Best regards,
[Name] | [Title] | [Our Company] | [email] | [phone]

---

## Follow-up Email Template

Send 7 days after the initial email if there is no reply. Keep it short.

Subject: Re: Data licensing inquiry — [Vendor] — exclusive arrangement

Dear [Name],

Following up on my note of [date] regarding an exclusive licensing arrangement for
your [Data Type] product. We are actively evaluating a small number of vendors and
would like to include you in the process.

Would a 30-minute call in the next ten days work? If someone else on your team owns
data licensing for financial-services clients, I would appreciate an introduction.

Best regards,
[Name]

---

## Discovery Call Agenda (30 minutes)

| Minutes | Topic | Owner |
|---------|-------|-------|
| 0-5 | Vendor product overview — what exactly is in the dataset, coverage, refresh cadence, history depth | Vendor |
| 5-15 | Our questions, in order (see the 10 questions below); capture answers verbatim in the call notes | Us |
| 15-20 | Pricing ballpark — annual range with and without exclusivity, setup fees, overage terms | Vendor |
| 20-30 | Next steps — historical sample for backtest, NDA if needed, target date for LOI, named contacts on both sides | Both |

Rules for the call: do not disclose our specific signal design or backtest results;
ask for pricing ranges not quotes; write down every number and every "we'll get back
to you" with a date attached.

---

## Ten Questions to Ask the Vendor

1. How many financial-services licensees have access to this exact slice today?
   (The count is the direct counter to any exclusivity claim; a large number means
   we are buying a commodity.)
2. What is the median customer tenure on comparable contracts?
   (Stability indicator: high churn suggests delivery or legal problems.)
3. Do you offer exclusive or semi-exclusive arrangements for [vertical]?
   (Establishes whether exclusivity is even on the table before we invest effort.)
4. What is your standard redistribution language for derived signals?
   (Derived rights are the difference between a usable and an unusable contract.)
5. What is the primary source of each data field, and how is consent documented?
   (Provenance question, post-App Annie; vague answers are a red flag.)
6. Can you provide a sample of historical data for backtesting before any LOI?
   (Validation gate — never sign before testing the actual data.)
7. What is pricing for an annual contract with exclusivity versus without?
   (The exclusivity premium is the key number for the Year-1 budget.)
8. Do you offer MFN clauses on pricing?
   (Price protection if they later sell a bigger package cheaper.)
9. What is your termination-for-convenience clause?
   (Exit flexibility; we want a clean year-one off-ramp.)
10. Which jurisdictions do you currently serve, and for which data types do you have
    a regulatory-hedged position?
    (Jurisdiction flexibility determines whether EU data is even available to us.)

---

## Five Priority Vendors

Ranked from docs/structural-edge/VENDOR_SHORTLIST.md. Note: Earnest Analytics is rated
HIGH in that source document.

| Rank | Vendor | Category | Public cost signal | Contact priority | Reason |
|------|--------|----------|--------------------|------------------|--------|
| 1 | MarineTraffic (Kpler) | AIS shipping | $200k-1M/yr | HIGH | Largest AIS network; merged with Kpler, so covers both raw AIS and commodity analytics in one counterparty |
| 2 | Spire Global (NYSE: SPIR) | AIS + satellite | $300k-1M/yr | HIGH | Public company (audited financials, contract disclosure); satellite AIS coverage complements terrestrial |
| 3 | Kpler | Commodity flow | $200k-1M/yr | HIGH | Deepest commodity trade-flow modelling; analytics-only exclusivity is offered, which matches our derived-signal model |
| 4 | Consumer Edge | US card panel | $500k-2M/yr | HIGH | Slice-based exclusivity with MFN as standard; US panel clean under CCPA; clearest exclusivity path |
| 5 | Earnest Analytics | US card alt | contact for quote | HIGH | Direct-to-fund distribution with custom slices; smaller than Consumer Edge, so more likely to grant real exclusivity |

Concentration note: ranks 1 and 3 are the same corporate group (Kpler acquired
MarineTraffic in 2023). Approach them as one negotiation, not two, and use the
overlap to argue for a combined package price.

---

## Outreach Cadence

| Day | Action |
|-----|--------|
| Day 1 | Send initial email to the 3 highest-priority vendors (MarineTraffic, Spire, Consumer Edge) |
| Day 8 | Follow-up email to non-responders; send initial email to 2 further vendors (Kpler, Earnest) |
| Day 15 | All first-round responses expected; triage into call-scheduled / declined / silent |
| Day 16-20 | Discovery calls, 30 minutes each, agenda above; capture answers in writing |
| Day 21+ | LOI negotiation with the 1-2 vendors that survived the questions and the call |

Trigger to pause the cadence: if the legal gate (LEGAL_EXECUTION_CHECKLIST.md Step 3)
has not passed, do not send any email. Vendor outreach before the legal answer burns
relationships on a direction that may be closed.
