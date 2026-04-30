from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
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