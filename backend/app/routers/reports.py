"""Daily performance report API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.daily_report import DailyReport

router = APIRouter()


def _serialize(report: DailyReport) -> dict:
    return {
        "id": report.id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "total_pnl": float(report.total_pnl) if report.total_pnl is not None else None,
        "realized_pnl": float(report.realized_pnl) if report.realized_pnl is not None else None,
        "unrealized_pnl": float(report.unrealized_pnl) if report.unrealized_pnl is not None else None,
        "total_trades": report.total_trades,
        "winning_trades": report.winning_trades,
        "signals_generated": report.signals_generated,
        "best_strategy": report.best_strategy,
        "worst_strategy": report.worst_strategy,
        "top_signals": report.top_signals if report.top_signals is not None else [],
        "strategy_breakdown": report.strategy_breakdown if report.strategy_breakdown is not None else {},
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@router.get("/reports")
async def list_reports(
    limit: int = Query(default=30, le=90),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DailyReport)
        .order_by(desc(DailyReport.report_date))
        .limit(limit)
    )
    reports = result.scalars().all()
    return {"reports": [_serialize(r) for r in reports], "total": len(reports)}


@router.get("/reports/latest")
async def get_latest_report(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DailyReport)
        .order_by(desc(DailyReport.report_date))
        .limit(1)
    )
    report = result.scalar_one_or_none()
    return {"report": _serialize(report) if report else None}
