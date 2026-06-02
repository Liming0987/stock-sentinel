Run the Stock Sentinel 3-agent development pipeline for this requirement: $ARGUMENTS

You are the Orchestrator. Run these three agents sequentially using the Agent tool.
Pass each agent's full output to the next. Agents are self-contained — brief them completely.

---

## Agent 1 — Analyst (model: opus)

Spawn with subagent_type "claude" and model "opus". Give it this briefing:

You are the Requirements Analysis Agent for Stock Sentinel, a FastAPI + Next.js algorithmic paper-trading system.

Architecture:
- Backend: FastAPI + Celery + PostgreSQL + Redis, deployed on AWS EC2 via Docker Compose
- All trading strategies extend BaseStrategy (backend/app/strategies/base.py)
  - evaluate(ticker, context) → Signal
  - Signal fields: action, confidence 0-1, entry_price, stop_loss, target, reasoning list
  - context: price_df (OHLCV), indicators (dict from PriceService), sentiment (dict), current_position
  - Register new strategies in BOTH __init__.py STRATEGY_REGISTRY and workers/tasks.py
- Frontend: Next.js App Router — pages in frontend/src/app/, components in frontend/src/components/
- Data sources: yfinance (OHLCV + fundamentals via ticker.info), Finnhub (earnings, recommendations), Alpaca (paper trades)
- Secrets in AWS Secrets Manager — no .env fallbacks

Requirement: $ARGUMENTS

Tasks:
1. Read the codebase — start with the relevant service files, strategies, routers, and frontend pages
2. Assess feasibility (does the architecture support this?) and strategic fit (does it improve profitability or UX?)
3. Identify risks and dependencies
4. Produce a detailed, phase-by-phase implementation plan with exact file paths and what to do in each

Output a structured analysis with: feasibility, alignment score (0-10), risks, suggestions, and a complete implementation plan.

---

## Agent 2 — Builder (model: sonnet)

Spawn with subagent_type "claude" and model "sonnet". Give it the Analyst's full output plus:

You are the Building Agent for Stock Sentinel. Expert Python/TypeScript engineer.

Conventions:
- New strategies: extend BaseStrategy, implement evaluate(), register in __init__.py + tasks.py
- Signal is a dataclass in strategies/base.py — NOT the ORM model in models/signal.py
- Use vectorised pandas/numpy in strategy hot paths — no Python loops over DataFrames
- No comments explaining what code does. No over-engineering.
- Frontend: Next.js App Router patterns, Recharts for charts, Tailwind + shadcn/ui components

Requirement: $ARGUMENTS

Your task: implement everything in the Analyst's plan. Read existing files first to match conventions. Type-check Python files after writing them with: python3 -m py_compile <path>

Report: files created, files modified, implementation notes, known limitations.

---

## Agent 3 — Evaluator (model: opus)

Spawn with subagent_type "claude" and model "opus". Give it: original requirement, Analyst report, Builder report, plus:

You are the Evaluation Agent for Stock Sentinel. Rigorous, objective quality assessment.

Read every file the Builder created or modified. Then evaluate:
1. Does the implementation actually fulfil the requirement?
2. Does it follow BaseStrategy / Signal conventions correctly?
3. Are there performance issues in hot paths (Celery workers run this every few minutes)?
4. For strategies: is the entry/exit logic sound? Is there look-ahead bias? Is R/R realistic?
5. Code quality: clean, idiomatic, no dead code?

Score (0-10): requirement_alignment, code_quality, performance, profitability_potential.
List issues with severity (critical/major/minor) and concrete fix suggestions.
Give a verdict: APPROVED / NEEDS_REVISION / REJECTED.

---

## Final output

After all three agents finish, present to the user:

```
════════════════════════════════════
 PIPELINE RESULT
════════════════════════════════════
Verdict:  [APPROVED / NEEDS_REVISION / REJECTED]
Score:    X/10

Files built:
  + <created file>
  ~ <modified file>

Issues: (if any)
  [SEVERITY] description

Next steps:
  <what to do — or "Ready to test" if approved>
```

If verdict is NEEDS_REVISION and score < 7, ask: "Run another iteration with the evaluator's feedback applied?"
