## Purpose

Provides a daily local HTML report summarising how each of the 9 trading strategies performed today and over the past 30 days, written in plain English so that even a layman can understand it without interpreting raw numbers or navigating the web UI.

## ADDED Requirements

### Requirement: Report covers all 9 strategies
The skill SHALL fetch and report on all 9 active strategies (momentum, rsi_meanreversion, bb_breakout, macd_histogram, fib_retracement, elliott_fib, vcp, vwap_cross, opening_range_breakout) regardless of whether they fired signals today.

#### Scenario: Strategy with no signals today
- **WHEN** a strategy produced no signals on the report date
- **THEN** the report SHALL display a "No signals today" section for that strategy and still show its 30-day performance metrics

#### Scenario: Strategy with signals today
- **WHEN** a strategy produced one or more signals on the report date
- **THEN** the report SHALL display each signal's ticker, action, confidence, plain-English reasoning, and whether it was executed or skipped (with a plain-English reason if skipped)

### Requirement: 30-day performance metrics per strategy
The report SHALL display the following metrics for each strategy, calculated over the trailing 30 calendar days: win rate, total P&L in USD, number of trades, average gain on winners, average loss on losers, and consecutive loss streak.

#### Scenario: Strategy with no trades in 30 days
- **WHEN** a strategy has no closed trades in the past 30 days
- **THEN** the report SHALL display "No trades in the last 30 days" rather than showing zeroes or empty cells

### Requirement: Plain-English health summary per strategy
The report SHALL include a 2-3 sentence Claude-generated health summary per strategy that interprets the data in plain English, notes whether performance is in line with the strategy's design, and flags anything worth watching.

#### Scenario: Healthy strategy
- **WHEN** a strategy's win rate and P&L are within normal range for its design
- **THEN** the summary SHALL confirm the strategy is performing as expected in plain language

#### Scenario: Strategy showing warning signs
- **WHEN** a strategy has 3 or more consecutive losses, or win rate has dropped significantly
- **THEN** the summary SHALL call this out explicitly in plain language

### Requirement: Plain-English not_executed_reason translation
The report SHALL translate internal not_executed_reason codes into plain English.

#### Scenario: Known code
- **WHEN** a signal's not_executed_reason is a known internal code (e.g. position_cap, insufficient_funds, confidence_too_low)
- **THEN** the report SHALL display a plain-English explanation instead of the raw code

#### Scenario: Unknown code
- **WHEN** a signal's not_executed_reason is an unrecognised code
- **THEN** the report SHALL display the raw code in quotes rather than failing

### Requirement: Single self-contained HTML file output
The skill SHALL render a single HTML file at `reports/strategy-review/YYYY-MM-DD.html` relative to the repo root, and SHALL open it in the default browser automatically after generation.

#### Scenario: File written successfully
- **WHEN** the report generates without error
- **THEN** a file SHALL exist at the expected path and the browser SHALL open it

#### Scenario: Output directory does not exist
- **WHEN** the `reports/strategy-review/` directory does not exist
- **THEN** the skill SHALL create it before writing the file

### Requirement: Report is local-only
The report files SHALL NOT be committed to git and SHALL NOT be published to the website. The `reports/` directory SHALL be gitignored.

#### Scenario: Git status after report generation
- **WHEN** the report is generated
- **THEN** `git status` SHALL NOT show any new untracked files under `reports/`
