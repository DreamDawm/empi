from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.api.deps import get_db
from app.models import EmpiMaster, EmpiMergeLog, EmpiPendingReview, EmpiProcessLog
from app.services.etl import etl_scheduler
from app.services.config_service import config_service
from typing import Dict, Any
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("")
def get_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    total = db.query(EmpiMaster).count()
    merged = db.query(EmpiMaster).filter(EmpiMaster.status == 'MERGED').count()

    # Get pending threshold and filter candidates accordingly
    pending_threshold = config_service.get_pending_threshold(db)
    pending = db.query(EmpiPendingReview).filter(
        EmpiPendingReview.status == 'PENDING',
        EmpiPendingReview.similarity_score >= pending_threshold
    ).count()

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

@router.post("/trigger-clean")
def trigger_clean(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """触发增量清洗（基于最后更新时间）"""
    try:
        stats = etl_scheduler.poll_and_process(db)
        return {"message": "清洗完成", "stats": stats}
    except Exception as e:
        return {"message": f"清洗失败: {str(e)}", "stats": None}

@router.post("/trigger-full-clean")
def trigger_full_clean(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """触发全量清洗（清除处理日志后重新处理所有数据）"""
    try:
        # 清除处理日志，允许重新处理所有数据
        db.query(EmpiProcessLog).delete()
        db.commit()

        # 重置last_update_time（删除Redis键）
        etl_scheduler.redis_client.delete('etl:last_update_time')

        # 执行全量清洗
        stats = etl_scheduler.poll_and_process(db)
        return {"message": "全量清洗完成", "stats": stats}
    except Exception as e:
        return {"message": f"全量清洗失败: {str(e)}", "stats": None}