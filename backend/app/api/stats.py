from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.deps import get_db
from app.models import EmpiMaster, EmpiMergeLog, EmpiPendingReview
from typing import Dict, Any
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("")
def get_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    total = db.query(EmpiMaster).count()
    merged = db.query(EmpiMaster).filter(EmpiMaster.status == 'MERGED').count()
    pending = db.query(EmpiPendingReview).filter(EmpiPendingReview.status == 'PENDING').count()

    return {
        "total": total,
        "merged": merged,
        "pending": pending,
        "merge_rate": round(merged / total * 100, 2) if total > 0 else 0
    }

@router.get("/trend")
def get_trend(days: int = 7, db: Session = Depends(get_db)) -> Dict[str, Any]:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    daily_stats = []
    current = start_date
    while current <= end_date:
        next_day = current + timedelta(days=1)
        count = db.query(EmpiMergeLog).filter(
            EmpiMergeLog.merge_time >= current,
            EmpiMergeLog.merge_time < next_day
        ).count()
        daily_stats.append({
            "date": current.strftime("%Y-%m-%d"),
            "count": count
        })
        current = next_day

    return {"data": daily_stats}