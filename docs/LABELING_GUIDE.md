# Labeling Guide (gold set)

Fill `gold_root_cause` and `gold_priority` in `data/labels/to_label.csv`, then save it as `data/labels/gold_labels.csv`.

**Step 1: did the consumer authorize the transaction?**
* No → fraud: `unauthorized_card_not_present` (online/phone, card still in hand), `unauthorized_card_present` (lost/stolen/skimmed card used in person), `account_takeover` (contact details changed, card sent elsewhere, account opened in their name).
* Yes → merchant dispute: `merchandise_not_received`, `not_as_described_or_defective`, `credit_not_processed`, `cancelled_recurring`, `duplicate_processing`, `incorrect_amount`, `paid_by_other_means`.
* Unclear, and the complaint is about how the bank handled the dispute → `issuer_dispute_process_failure`.
* Not a dispute/fraud complaint → `other`.

**Step 2: priority.** P1 if any of: identity theft/ATO, fraud still happening, ≥ $1,000, elderly/disabled/servicemember, credit reporting or collections harm, legal threat. P3 if small/informational/already resolved. Otherwise P2.

**Tie-breaks.** Recurring charge after cancellation → `cancelled_recurring` (not `credit_not_processed`). Charged twice → `duplicate_processing` even if the bank also mishandled it.
