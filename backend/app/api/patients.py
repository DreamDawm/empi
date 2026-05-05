from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.api.deps import get_db
from app.models import EmpiMaster, EmpiPendingReview

router = APIRouter(prefix="/api/patients", tags=["patients"])

@router.get("")
def list_patients(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)) -> Dict[str, Any]:
    offset = (page - 1) * page_size
    total = db.query(EmpiMaster).count()
    patients = db.query(EmpiMaster).offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "patient_id": p.patient_id,
                "patient_name": p.patient_name,
                "master_id": p.master_id,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in patients
        ]
    }

@router.get("/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)) -> Optional[Dict[str, Any]]:
    patient = db.query(EmpiMaster).filter(EmpiMaster.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return {
        "patient_id": patient.patient_id,
        "patient_name": patient.patient_name,
        "master_id": patient.master_id,
        "status": patient.status,
        "merged_to_master_id": patient.merged_to_master_id,
        "inverted_index": patient.inverted_index,
        "created_at": patient.created_at.isoformat() if patient.created_at else None,
        "updated_at": patient.updated_at.isoformat() if patient.updated_at else None
    }

@router.get("/{patient_id}/similar")
def get_similar_patients(patient_id: str, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    pending = db.query(EmpiPendingReview).filter(
        (EmpiPendingReview.person_id_a == patient_id) |
        (EmpiPendingReview.person_id_b == patient_id)
    ).filter(EmpiPendingReview.status == 'PENDING').all()

    return [
        {
            "id": p.id,
            "person_id_a": p.person_id_a,
            "person_id_b": p.person_id_b,
            "similarity_score": float(p.similarity_score),
            "similarity_details": p.similarity_details,
            "create_time": p.create_time.isoformat() if p.create_time else None
        }
        for p in pending
    ]

@router.get("/{patient_id}/master")
def get_patient_master(patient_id: str, db: Session = Depends(get_db)) -> Optional[Dict[str, Any]]:
    patient = db.query(EmpiMaster).filter(EmpiMaster.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    master_id = patient.master_id
    if patient.status == 'MERGED' and patient.merged_to_master_id:
        master_id = patient.merged_to_master_id

    master = db.query(EmpiMaster).filter(EmpiMaster.master_id == master_id).first()

    merged_patients = db.query(EmpiMaster).filter(
        EmpiMaster.merged_to_master_id == master_id
    ).all()

    return {
        "master_id": master_id,
        "primary_patient": {
            "patient_id": master.patient_id,
            "patient_name": master.patient_name
        } if master else None,
        "merged_patients": [
            {
                "patient_id": p.patient_id,
                "patient_name": p.patient_name
            }
            for p in merged_patients
        ]
    }