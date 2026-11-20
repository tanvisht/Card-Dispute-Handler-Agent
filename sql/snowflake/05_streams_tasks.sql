-- Incremental change capture + scheduled data-quality monitoring.
-- Requires: GRANT EXECUTE TASK ON ACCOUNT TO ROLE TRIAGE_ROLE;  (run once as ACCOUNTADMIN)
USE SCHEMA DISPUTE_TRIAGE.CORE;

-- 1. Stream: every complaint inserted/updated by SP_MERGE_COMPLAINTS since the last consume.
--    The Python pipeline (or a downstream task) can read this instead of diffing the full table.
CREATE OR REPLACE STREAM RAW_COMPLAINTS_STREAM ON TABLE RAW_COMPLAINTS APPEND_ONLY = FALSE;

-- Pending work for the classifier: new rows in the stream that have no classification yet.
CREATE OR REPLACE VIEW V_PENDING_CLASSIFICATION AS
SELECT s.COMPLAINT_ID, s.DATE_RECEIVED, s.METADATA$ACTION AS CHANGE_ACTION
FROM RAW_COMPLAINTS_STREAM s
LEFT JOIN CLASSIFICATIONS c ON c.COMPLAINT_ID = s.COMPLAINT_ID
WHERE s.METADATA$ACTION = 'INSERT' AND c.COMPLAINT_ID IS NULL;

-- 2. Data-quality results log (one row per check per run).
CREATE TABLE IF NOT EXISTS DQ_RESULTS (
  RUN_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  CHECK_NAME STRING,
  FAILED_ROWS NUMBER,
  PASSED BOOLEAN);

CREATE OR REPLACE PROCEDURE SP_RUN_DQ_CHECKS()
RETURNS STRING LANGUAGE SQL AS
$$
BEGIN
  INSERT INTO DQ_RESULTS (CHECK_NAME, FAILED_ROWS, PASSED)
  SELECT 'invalid_root_cause', COUNT(*), COUNT(*) = 0 FROM CLASSIFICATIONS
   WHERE ROOT_CAUSE NOT IN ('unauthorized_card_not_present','unauthorized_card_present','account_takeover',
     'merchandise_not_received','not_as_described_or_defective','credit_not_processed','cancelled_recurring',
     'duplicate_processing','incorrect_amount','paid_by_other_means','issuer_dispute_process_failure','other')
  UNION ALL
  SELECT 'confidence_out_of_range', COUNT(*), COUNT(*) = 0 FROM CLASSIFICATIONS
   WHERE CONFIDENCE < 0 OR CONFIDENCE > 1
  UNION ALL
  SELECT 'orphan_classification', COUNT(*), COUNT(*) = 0 FROM CLASSIFICATIONS c
   LEFT JOIN RAW_COMPLAINTS r ON r.COMPLAINT_ID = c.COMPLAINT_ID WHERE r.COMPLAINT_ID IS NULL
  UNION ALL
  -- allow a 24h grace window for the batch pipeline before flagging a gap
  SELECT 'unclassified_over_24h', COUNT(*), COUNT(*) = 0 FROM RAW_COMPLAINTS r
   WHERE r.LOADED_AT < DATEADD('hour', -24, CURRENT_TIMESTAMP())
     AND NOT EXISTS (SELECT 1 FROM CLASSIFICATIONS c WHERE c.COMPLAINT_ID = r.COMPLAINT_ID)
  UNION ALL
  SELECT 'p1_pending_over_15d', COUNT(*), COUNT(*) = 0 FROM MART.V_CASES
   WHERE PRIORITY = 'P1' AND CASE_STATUS = 'PENDING_REVIEW' AND AGE_DAYS > 15;
  RETURN 'ok';
END;
$$;

-- 3. Task: run the checks every morning (UTC) on the XS warehouse; suspended until resumed.
CREATE OR REPLACE TASK TASK_DAILY_DQ
  WAREHOUSE = TRIAGE_WH
  SCHEDULE = 'USING CRON 0 6 * * * UTC'
AS CALL SP_RUN_DQ_CHECKS();

ALTER TASK TASK_DAILY_DQ RESUME;

-- BI view: latest result per check (add as a "Data Health" card in Power BI).
CREATE OR REPLACE VIEW MART.V_DQ_LATEST AS
SELECT * FROM CORE.DQ_RESULTS
QUALIFY ROW_NUMBER() OVER (PARTITION BY CHECK_NAME ORDER BY RUN_AT DESC) = 1;
