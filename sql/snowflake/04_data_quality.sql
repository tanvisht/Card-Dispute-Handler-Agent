-- Data-quality checks; each query should return 0 rows. Run after every load.
USE SCHEMA DISPUTE_TRIAGE.CORE;
-- 1. classifications with out-of-vocabulary root causes
SELECT * FROM CLASSIFICATIONS WHERE ROOT_CAUSE NOT IN (
 'unauthorized_card_not_present','unauthorized_card_present','account_takeover','merchandise_not_received',
 'not_as_described_or_defective','credit_not_processed','cancelled_recurring','duplicate_processing',
 'incorrect_amount','paid_by_other_means','issuer_dispute_process_failure','other');
-- 2. confidence outside [0,1]
SELECT * FROM CLASSIFICATIONS WHERE CONFIDENCE < 0 OR CONFIDENCE > 1;
-- 3. orphan classifications
SELECT c.COMPLAINT_ID FROM CLASSIFICATIONS c LEFT JOIN RAW_COMPLAINTS r USING (COMPLAINT_ID) WHERE r.COMPLAINT_ID IS NULL;
-- 4. raw complaints never classified (pipeline gap)
SELECT COMPLAINT_ID FROM RAW_COMPLAINTS WHERE COMPLAINT_ID NOT IN (SELECT COMPLAINT_ID FROM CLASSIFICATIONS);
