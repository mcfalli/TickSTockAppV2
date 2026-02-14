# Your questions
 Question 1: Data Freshness
  - When historical imports complete, are we analyzing the last 250 bars or all imported bars?
  - Current behavior: Analysis service queries last 250 bars (configurable bars parameter)
  - Is this the right default? Should imports analyze ALL imported data (e.g., 1 year = 252 bars)?

  Question 2: Timeframe Consistency
  - Historical Import: Supports daily/hourly/intraday/weekly/monthly
  - Auto-Analysis: Currently hardcoded to timeframe='daily' (line 267 in import_analysis_bridge.py)
  - Potential Issue: If user imports hourly data, auto-analysis runs on daily data (mismatch)
  - Should we: Match analysis timeframe to import timeframe?

  Question 3: Analysis Type Consistency
  - Auto-Analysis: Hardcoded to analysis_type='both' (patterns + indicators)
  - Process Analysis page: User selects Patterns/Indicators/Both
  - Question: Should users have control over analysis type for imports? (e.g., checkbox "Run Patterns Only" vs "Run Both")

  Question 4: Job Retention
  - Redis metadata keys: 24-hour TTL
  - Pattern detections: 48-hour retention (Sprint 74)
  - Import jobs: How long do they persist?
  - Question: Should metadata TTL match pattern retention (48 hours for consistency)?

  Question 5: Error Notification
  - If auto-analysis fails (e.g., no symbols found, database error), how does the user know?
  - Current: Logs only (not visible to admin user)
  - Should we: Add error notifications to Historical Data dashboard or Process Analysis page?

  Question 6: Universe vs Symbol Consistency
  - Historical Import: Accepts universe_key (e.g., 'SPY', 'nasdaq100')
  - Auto-Analysis: Stores universe_key in job status
  - Symbol resolution: Falls back to RelationshipCache if symbols missing
  - Question: Is this the intended fallback chain? (seems robust)

# My Responses
1. 250 daily bars - ok.  I assume we are talking daily.  if not let's discuss.
2. no change, indicators and patterns run on daily data.  The only reason that is there from a data import perspective is flexibility, we will always load those other timeframes for future use. 
3. no, run both. 
4. not understanding but if this is just job history then no issue here.
5. once we are set up we will be running at night 3k stocks (after we seed with 3 years of data) to get the daily data and pattern/indicators set or corrected. 
6. not sure.  we can create a * for import all stocks we have defined. 
7.  My question for you.  when evaluating select * from daily_indicators where symbol = 'INTC' and indicator_type like 'sma%' to my chart, the values are incorrect.  these SMA values are wrong.  is that because there is not enough data to perform calculations on?  I would think the minimum bars would come into play for this, but we removed that check.  I'd like to know the answer but at the end of the day we will have 3k stocks in database with 3 years of data to plow through.  
