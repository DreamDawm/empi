from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.api.deps import get_db
from app.models import EmpiPendingReview, EmpiMergeLog, EmpiMaster
from app.services.merger import decision_engine
import json
from datetime import datetime

router = APIRouter(prefix="/api/merge", tags=["merge"])

@router.get("/candidates")
def list_merge_candidates(page: int = 1, page_size: int = 20, min_score: float = 0, db: Session = Depends(get_db)) -> Dict[str, Any]:
    offset = (page - 1) * page_size
    query = db.query(EmpiPendingReview).filter(EmpiPendingReview.status == 'PENDING')
    if min_score > 0:
        query = query.filter(EmpiPendingReview.similarity_score >= min_score)
    total = query.count()
    candidates = query.offset(offset).limit(page_size).all()

    result = []
    for c in candidates:
        patient_a = db.query(EmpiMaster).filter(EmpiMaster.patient_id == c.person_id_a).first()
        patient_b = db.query(EmpiMaster).filter(EmpiMaster.patient_id == c.person_id_b).first()

        result.append({
            "id": c.id,
            "patient_a": {
                "patient_id": patient_a.patient_id if patient_a else c.person_id_a,
                "patient_name": patient_a.patient_name if patient_a else None
            },
            "patient_b": {
                "patient_id": patient_b.patient_id if patient_b else c.person_id_b,
                "patient_name": patient_b.patient_name if patient_b else None
            },
            "similarity_score": float(c.similarity_score),
            "similarity_details": c.similarity_details,
            "create_time": c.create_time.isoformat() if c.create_time else None
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": result
    }

@router.post("")
def manual_merge(params: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
    person_id_a = params.get("person_id_a")
    person_id_b = params.get("person_id_b")

    if not person_id_a or not person_id_b:
        raise HTTPException(status_code=400, detail="person_id_a and person_id_b are required")

    patient_a = db.query(EmpiMaster).filter(EmpiMaster.patient_id == person_id_a).first()
    patient_b = db.query(EmpiMaster).filter(EmpiMaster.patient_id == person_id_b).first()

    if not patient_a or not patient_b:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_a_data = {
        "patient_id": patient_a.patient_id,
        "patient_name": patient_a.patient_name,
        "gender": patient_a.inverted_index.get("pinyin_gender", "").split("_")[-1] if patient_a.inverted_index else "",
        "created_at": patient_a.created_at
    }
    patient_b_data = {
        "patient_id": patient_b.patient_id,
        "patient_name": patient_b.patient_name,
        "gender": patient_b.inverted_index.get("pinyin_gender", "").split("_")[-1] if patient_b.inverted_index else "",
        "created_at": patient_b.created_at
    }

    master_id = decision_engine.auto_merge(db, patient_a_data, patient_b_data, 100.0, 'MANUAL')

    pending = db.query(EmpiPendingReview).filter(
        ((EmpiPendingReview.person_id_a == person_id_a) & (EmpiPendingReview.person_id_b == person_id_b)) |
        ((EmpiPendingReview.person_id_a == person_id_b) & (EmpiPendingReview.person_id_b == person_id_a))
    ).first()

    if pending:
        pending.status = 'RESOLVED'
        pending.resolution_type = 'MERGE'
        pending.resolved_at = datetime.now()
        db.commit()

    return {"master_id": master_id, "message": "Merge successful"}

@router.post("/{id}/ignore")
def ignore_candidate(id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    pending = db.query(EmpiPendingReview).filter(EmpiPendingReview.id == id).first()
    if not pending:
        raise HTTPException(status_code=404, detail="Candidate not found")

    pending.status = 'IGNORED'
    pending.resolved_at = datetime.now()
    db.commit()

    return {"message": "Ignored successfully"}

@router.get("/history")
def merge_history(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)) -> Dict[str, Any]:
    offset = (page - 1) * page_size
    total = db.query(EmpiMergeLog).count()
    logs = db.query(EmpiMergeLog).order_by(EmpiMergeLog.merge_time.desc()).offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "id": log.id,
                "person_id_a": log.person_id_a,
                "person_id_b": log.person_id_b,
                "master_id": log.master_id,
                "merge_type": log.merge_type,
                "similarity_score": float(log.similarity_score),
                "merge_time": log.merge_time.isoformat() if log.merge_time else None
            }
            for log in logs
        ]
    }