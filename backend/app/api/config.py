from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any
from app.api.deps import get_db
from app.services.config_service import config_service

router = APIRouter(prefix="/api/config", tags=["config"])

@router.get("/weights")
def get_weights(db: Session = Depends(get_db)) -> Dict[str, float]:
    return config_service.get_weights(db)

@router.put("/weights")
def update_weights(weights: Dict[str, float], db: Session = Depends(get_db)) -> Dict[str, float]:
    return config_service.update_weights(db, weights)

@router.get("/threshold")
def get_threshold(db: Session = Depends(get_db)) -> Dict[str, float]:
    threshold = config_service.get_threshold(db)
    return {"threshold": threshold}

@router.put("/threshold")
def update_threshold(params: Dict[str, float], db: Session = Depends(get_db)) -> Dict[str, float]:
    threshold = params.get("threshold", 85.0)
    return {"threshold": config_service.update_threshold(db, threshold)}

@router.get("/pending-threshold")
def get_pending_threshold(db: Session = Depends(get_db)) -> Dict[str, float]:
    threshold = config_service.get_pending_threshold(db)
    return {"threshold": threshold}

@router.put("/pending-threshold")
def update_pending_threshold(params: Dict[str, float], db: Session = Depends(get_db)) -> Dict[str, float]:
    threshold = params.get("threshold", 60.0)
    return {"threshold": config_service.update_pending_threshold(db, threshold)}

@router.get("/poll-interval")
def get_poll_interval(db: Session = Depends(get_db)) -> Dict[str, float]:
    hours = config_service.get_poll_interval_hours(db)
    return {"hours": hours}

@router.put("/poll-interval")
def update_poll_interval(params: Dict[str, float], db: Session = Depends(get_db)) -> Dict[str, float]:
    hours = params.get("hours", 2.0)
    return {"hours": config_service.update_poll_interval_hours(db, hours)}

@router.get("/patient-fields")
def get_patient_fields(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取im_patient表的字段列表"""
    try:
        result = db.execute(text("DESCRIBE im_patient"))
        columns = [row[0] for row in result.fetchall()]
        return {"fields": columns}
    except Exception:
        return {"fields": []}