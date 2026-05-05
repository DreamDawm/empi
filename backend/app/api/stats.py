from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.api.deps import get_db
from app.models import EmpiMaster, EmpiMergeLog, EmpiPendingReview, EmpiProcessLog
from app.services.etl import etl_scheduler
from app.services.config_service import config_service
from app.services.logging_service import logging_service
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
def trigger_clean(batch_size: int = 1000, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """触发增量清洗（基于最后更新时间）- 同步执行"""
    try:
        stats = etl_scheduler.poll_and_process(db, batch_size=batch_size)
        return {"message": "清洗完成", "stats": stats}
    except Exception as e:
        return {"message": f"清洗失败: {str(e)}", "stats": None}

@router.post("/trigger-clean-async")
async def trigger_clean_async(batch_size: int = 1000, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """触发增量清洗 - 异步执行（后台任务）"""
    def run_clean():
        return etl_scheduler.poll_and_process(db, batch_size=batch_size)

    background_tasks.add_task(run_clean)
    return {"message": "增量清洗任务已提交后台执行"}

@router.post("/trigger-full-clean")
def trigger_full_clean(batch_size: int = 1000, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """触发全量清洗（同步执行）- 清空4个表后重新处理所有数据"""
    try:
        # 清空所有相关表
        db.query(EmpiMaster).delete()
        db.query(EmpiMergeLog).delete()
        db.query(EmpiPendingReview).delete()
        db.query(EmpiProcessLog).delete()
        db.commit()

        # 重置游标（删除Redis键）
        etl_scheduler.redis_client.delete('etl:last_patient_id')

        # 执行全量清洗
        stats = etl_scheduler.poll_and_process(db, batch_size=batch_size)
        return {"message": "全量清洗完成", "stats": stats}
    except Exception as e:
        return {"message": f"全量清洗失败: {str(e)}", "stats": None}

@router.post("/trigger-full-clean-async")
async def trigger_full_clean_async(batch_size: int = 1000, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """触发全量清洗 - 异步执行（后台任务）"""
    def run_full_clean():
        db.query(EmpiMaster).delete()
        db.query(EmpiMergeLog).delete()
        db.query(EmpiPendingReview).delete()
        db.query(EmpiProcessLog).delete()
        db.commit()
        etl_scheduler.redis_client.delete('etl:last_patient_id')
        return etl_scheduler.poll_and_process(db, batch_size=batch_size)

    background_tasks.add_task(run_full_clean)
    return {"message": "全量清洗任务已提交后台执行"}

@router.get("/logs/stream")
async def stream_logs():
    """SSE实时日志流"""
    async def event_generator():
        async for log_entry in logging_service.stream_logs():
            yield log_entry
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.post("/admin/clear-processed-cache")
def clear_processed_cache(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """清除已处理患者缓存（用于调试）"""
    etl_scheduler.redis_client.delete(etl_scheduler._processed_patients_key)
    return {"message": "缓存已清除"}