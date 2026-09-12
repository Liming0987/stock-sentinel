## MODIFIED Requirements

### Requirement: Analysis schema includes RS rating, earnings, sector momentum, and score breakdown
The daily recon skill analysis JSON SHALL include the following new fields:

```json
{
  "rs_rating": 74,
  "earnings_days": 23,
  "earnings_flag": "catalyst_opportunity | earnings_risk | null",
  "sector_momentum": {
    "etf": "SMH",
    "return_4w_pct": 8.2,
    "label": "strong | neutral | weak"
  },
  "score": {
    "total": 68,
    "trend_health": 22,
    "fundamental_quality": 26,
    "timing_setup": 20
  }
}
```

#### Scenario: Analysis JSON written with new fields
- **WHEN** the skill generates an analysis for a stock
- **THEN** the analysis JSON SHALL contain rs_rating, earnings_days, earnings_flag, sector_momentum, and score fields

#### Scenario: yfinance earnings date unavailable
- **WHEN** yfinance returns no earnings date
- **THEN** earnings_days SHALL be null and earnings_flag SHALL be null

### Requirement: SKILL.md runbook instructs scoring before Claude narrative
The SKILL.md SHALL instruct Claude to compute the 0–100 score using the scoring engine rules before writing any narrative, and to pass the score breakdown into the analysis JSON.

#### Scenario: Stance derived from score
- **WHEN** scoring produces a total of 62
- **THEN** overall_stance SHALL be "watch" (50–74 band)

### Requirement: HTML report renders new fields
The generate_stock_report.py script SHALL render RS rating, earnings flag, sector momentum, and score breakdown visibly in the HTML report.

#### Scenario: RS rating displayed
- **WHEN** rs_rating is present in analysis JSON
- **THEN** the HTML SHALL display it as a badge (e.g. "RS 74") near the price header

#### Scenario: Earnings risk displayed
- **WHEN** earnings_flag is "earnings_risk"
- **THEN** the HTML SHALL display a prominent warning banner above the stance section

### Requirement: DCF API response includes upside_pct, growth_rate, discount_rate
The `/api/watchlist/{ticker}/dcf` endpoint SHALL return `upside_pct`, `growth_rate`, and `discount_rate` fields so Claude can write a complete DCF verdict.

#### Scenario: DCF fields present
- **WHEN** DCF is feasible
- **THEN** the API response SHALL include upside_pct (percentage), growth_rate (decimal), and discount_rate (decimal)
