# Legal Execution Checklist — Data Exclusivity Activation

One-page actionable checklist. Everything below activates on a single user decision:
approving $8-15k of legal spend. Until that approval, nothing here should be executed.
All cost figures are carried from the existing structural-edge documents
(RECOMMENDATION.md, DATA_EXCLUSIVITY_SCOPE.md), not newly invented.

---

## Step 1 — Hire lawyers (Week 1)

Two routes:

- Option A — single cross-border specialist covering EU and US: $10-15k. Simpler to
  manage, one invoice, one point of contact, but asks one firm to be strong in two
  very different regimes.
- Option B — two specialists: US commercial/IP counsel plus EU data/GDPR counsel:
  $8-15k combined. Recommended, because the gate question (derived-signal resale) is
  answered differently in each jurisdiction and we need both answers specific rather
  than averaged.

Firms to contact: contact user's preferred firm. No firm names are listed here
deliberately — this document does not fabricate recommendations for professional
advisers.

Deliverable to request from counsel: an 8-12 page memo answering the gate question in
Step 3, not a general legal opinion.

---

## Step 2 — Send the brief (Week 2)

Package to send: the legal brief template (docs/structural-edge/LEGAL_BRIEF_TEMPLATE.md),
this LOI term sheet (docs/data-exclusivity/LOI_TERM_SHEET.md), and the vendor question
list (docs/data-exclusivity/VENDOR_OUTREACH_TEMPLATE.md) so counsel sees what we
intend to ask counterparties.

Working rhythm: weekly check-in with counsel; expect the memo in 3-4 weeks from
engagement, i.e. end of Week 4.

---

## Step 3 — Gate decision (Week 4)

This is the decision point that determines whether the data direction continues at all.

The legal memo must confirm that derived-signal resale is DEFENSIBLE in at least one
of the two jurisdictions (US, EU) for at least one of the two data types (AIS shipping,
US card transaction panel).

- Gate PASSES: proceed to Step 4.
- Gate FAILS: pivot to Option 2 in RECOMMENDATION.md — the EM local partnership model
  (Vietnam or Brazil, $2-5M stake plus $0.5-1M per year local presence, 6-12 months to
  operational). Do not spend further on vendor outreach.

Record the gate outcome in writing, with the lawyer's memo attached. This is the
document that justifies either the next $200-500k or the pivot.

---

## Step 4 — Vendor outreach (Weeks 5-6)

Send the email template from VENDOR_OUTREACH_TEMPLATE.md to the 3 highest-priority
vendors (MarineTraffic, Spire, Consumer Edge). Follow up at Day 8 and add Kpler and
Earnest. Schedule discovery calls, run the 30-minute agenda, ask the 10 questions and
record answers verbatim.

Exit criterion for this step: LOI in negotiation with at least one vendor within 4
weeks of the first call. If no vendor will discuss exclusivity at all, the direction
is dead regardless of legal opinion — note it and go to the kill criteria.

---

## Step 5 — LOI negotiation (Weeks 7-10)

Use LOI_TERM_SHEET.md as the base document. Defend the three MUST-HAVE clauses
(Exclusivity, Source-of-Origin Warranty, Derived Data Ownership). Trade away the three
concession clauses (Audit Right, Data Residency, MFN) for speed.

Evaluate every vendor counter against the four walk-away triggers in Section 4 of the
term sheet, in severity order: anti-assignment refused, derived-data ownership
contested, exclusivity downgraded to marketing exclusivity, source-of-origin warranty
refused. Any one of them ends that negotiation; move to the next vendor, not to a
compromise.

---

## Step 6 — Phase 2 after LOI signature (Weeks 11-20)

Technical work begins only after signature and after the vendor delivers its historical
sample.

Backtest with the vendor's history. Target: Sharpe above 1.5 on paper with at least 6
months of clean data. If achieved, paper trading in Q1 2027. If not achieved, exit the
vendor contract at the end of Year 1, with no penalty provided the standard termination
clause survived negotiation (that is why Clause 6 is on the list).

---

## Estimated total cost to first signal

| Item | Cost | Source |
|------|------|--------|
| Legal review, Weeks 1-4 | $8-15k | RECOMMENDATION.md |
| Vendor license, Year 1 | $200-500k | DATA_EXCLUSIVITY_SCOPE.md (AIS $200k-1M, card $500k-2M; entry tier assumed) |
| Incremental technology | $0 | existing infrastructure |
| Total, Year 1 | $210-515k | sum of the above |

---

## Kill criteria (all must be met by end of Year 1)

1. Legal gate passed (Step 3).
2. Vendor exclusivity actually granted in the signed contract.
3. Backtest Sharpe above 1.5 on at least 6 months of clean vendor data.
4. LOI termination clause enables exit without penalty.

If any one of the four fails: close the data direction. Consequence is the pivot
already documented in RECOMMENDATION.md — EM local partnership (Option 2) or scaling
the short 13D direction. Do not restart the data search with a different vendor after
a failed gate; the gate answer is about the legal regime, not the counterparty.
