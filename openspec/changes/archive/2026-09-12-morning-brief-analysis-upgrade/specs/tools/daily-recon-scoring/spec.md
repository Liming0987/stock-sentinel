## Purpose

Quantitative 0–100 scoring engine for the daily recon skill. Computes three dimension scores from existing API data plus new inputs (RS rating, earnings proximity, sector momentum) and produces a final conviction score that drives the buy/sell stance — replacing the binary accumulate/watch/hold/avoid logic that defaulted to "watch" when Wyckoff events did not fire.

## ADDED Requirements

### Requirement: Three-dimension scoring model
The scoring engine SHALL produce scores across three dimensions summing to a maximum of 100:
- Trend Health: 0–30 points
- Fundamental Quality: 0–30 points
- Timing/Setup: 0–40 points

#### Scenario: Score calculation
- **WHEN** all data is available for a stock
- **THEN** the engine SHALL compute each dimension score and return a total in [0, 100]

#### Scenario: Missing data dimension
- **WHEN** data for a dimension is unavailable (e.g. DCF not feasible)
- **THEN** the engine SHALL score that sub-component 0 rather than failing

### Requirement: Trend Health scoring (0–30 pts)
The Trend Health score SHALL reward stocks in confirmed uptrends with strong relative performance.

| Sub-component | Max pts | Signal |
|---------------|---------|--------|
| Price above EMA-50 > EMA-200 | 10 | Full stack aligned |
| EMA-50 rising over 10 days | 5 | Slope check |
| RS Rating ≥ 70 (top 30%) | 10 | 5 pts for RS 50–69 |
| Within 25% of 52-week high | 5 | Stage 2 proximity |

#### Scenario: Strong uptrend stock
- **WHEN** price > EMA-50 > EMA-200, EMA-50 rising, RS rating 80, within 15% of 52w high
- **THEN** Trend Health score SHALL be 30

#### Scenario: Broken downtrend stock
- **WHEN** price < EMA-200, RS rating 20
- **THEN** Trend Health score SHALL be 0 or near 0

### Requirement: Fundamental Quality scoring (0–30 pts)
The Fundamental Quality score SHALL reward strong fundamentals and DCF upside.

| Sub-component | Max pts | Signal |
|---------------|---------|--------|
| Fundamentals grade A | 15 | 10 for B, 5 for C, 0 for D/F |
| DCF upside > 15% | 10 | 5 pts for 5–15% upside |
| No red flags | 5 | 0 if any fundamental flags present |

#### Scenario: A-grade fundamentals with DCF upside
- **WHEN** fundamentals grade is A and DCF upside is 30%
- **THEN** Fundamental Quality score SHALL be 25–30

#### Scenario: DCF not feasible
- **WHEN** DCF returns feasible=false
- **THEN** DCF sub-component SHALL score 0; other sub-components unaffected

### Requirement: Timing/Setup scoring (0–40 pts)
The Timing/Setup score SHALL reward actionable technical setups.

| Sub-component | Max pts | Signal |
|---------------|---------|--------|
| VCP detected + Stage 2 | 15 | 7 pts for VCP detected without Stage 2 |
| Wyckoff LPS or SOS detected | 10 | 5 pts for any other bullish Wyckoff signal |
| Volume drying up in base | 5 | vol_ratio < 0.8× avg on recent sessions |
| Any strategy signal fired today | 10 | 5 pts for signal fired in last 3 days |

#### Scenario: Perfect setup
- **WHEN** VCP detected with Stage 2, Wyckoff SOS detected, volume drying, strategy signal today
- **THEN** Timing/Setup score SHALL be 40

#### Scenario: No setup
- **WHEN** no VCP, no Wyckoff signal, no strategy signal in last 3 days
- **THEN** Timing/Setup score SHALL be 0

### Requirement: Stance thresholds
The engine SHALL map total score to stance using fixed thresholds.

| Score | Stance |
|-------|--------|
| 75–100 | accumulate |
| 50–74 | watch |
| 35–49 | caution |
| 0–34 | avoid |

#### Scenario: Score 80
- **WHEN** total score is 80
- **THEN** stance SHALL be "accumulate"

#### Scenario: Score 45
- **WHEN** total score is 45
- **THEN** stance SHALL be "caution"

### Requirement: Earnings proximity override
Earnings proximity SHALL override the stance regardless of score.

#### Scenario: Earnings within 5 days
- **WHEN** next earnings date is ≤ 5 calendar days away
- **THEN** stance SHALL be overridden to "watch" and an earnings warning flag SHALL be set

#### Scenario: Earnings 5–14 days out
- **WHEN** next earnings date is 5–14 calendar days away
- **THEN** an earnings catalyst flag SHALL be added to the output without overriding stance
