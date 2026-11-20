# Power BI Dashboard: build spec

Connect with **Get Data → Snowflake**, database `DISPUTE_TRIAGE`, schema `MART`, role `TRIAGE_BI_READER`.
Import `V_CASES`, `V_CATEGORY_TRENDS`, `V_RECURRING_ISSUES`, `V_CASE_AGING`, `V_MODEL_QUALITY`.
Use Import mode with a daily scheduled refresh (DirectQuery is fine at under 1M rows).

## Data model
`V_CASES` is the fact table. Add a `DimDate` table marked as a date table, and relate `DimDate[Date]` 1:* to `V_CASES[DATE_RECEIVED]`.

## Measures (DAX)
```DAX
Total Cases        = COUNTROWS ( V_CASES )
Pending Review     = CALCULATE ( [Total Cases], V_CASES[CASE_STATUS] = "PENDING_REVIEW" )
Review Rate        = DIVIDE ( CALCULATE ( [Total Cases], V_CASES[NEEDS_HUMAN_REVIEW] = TRUE () ), [Total Cases] )
Fraud Share        = DIVIDE ( CALCULATE ( [Total Cases], V_CASES[IS_FRAUD] = TRUE () ), [Total Cases] )
Avg Age (days)     = AVERAGE ( V_CASES[AGE_DAYS] )
P1 Open > 15d      = CALCULATE ( [Total Cases], V_CASES[PRIORITY] = "P1",
                        V_CASES[CASE_STATUS] = "PENDING_REVIEW", V_CASES[AGE_DAYS] > 15 )
Model Agreement    = AVERAGE ( V_MODEL_QUALITY[ROOT_CAUSE_AGREEMENT] )
Cases MoM %        = VAR cur = [Total Cases]
                     VAR prev = CALCULATE ( [Total Cases], DATEADD ( DimDate[Date], -1, MONTH ) )
                     RETURN DIVIDE ( cur - prev, prev )
```

## Pages
1. **Overview**: KPI cards (Total, Pending Review, Review Rate, Fraud Share, P1 Open > 15d), a donut by root cause, and a bar by priority.
2. **Case Aging**: a stacked bar of `AGING_BUCKET` × `PRIORITY` (from `V_CASE_AGING`) and a table of the oldest pending cases.
3. **Recurring Issues**: a matrix of `COMPANY` × `ROOT_CAUSE` from `V_RECURRING_ISSUES` with conditional formatting on `CASES_90D`.
4. **Category Trends**: a line chart of monthly `CASES` by `ROOT_CAUSE` (`V_CATEGORY_TRENDS`) with `MOM_DELTA` in the tooltip.
5. **Model Quality**: a weekly line of `ROOT_CAUSE_AGREEMENT` by `PROMPT_VERSION`, and an override table where `MODEL_OVERRIDDEN = TRUE`.

Slicers on every page: date range, company, state, priority, case status.
