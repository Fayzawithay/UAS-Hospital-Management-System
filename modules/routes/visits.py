from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import date
from modules.schema.schemas import User, UserRole
from modules.items import visits as visit_crud
from modules.routes.auth import get_current_user

router = APIRouter()


@router.get("")
async def get_all_visits(patient_id: Optional[str] = None,
                        clinic_id: Optional[str] = None,
                        start_date: Optional[date] = None,
                        end_date: Optional[date] = None,
                        current_user: User = Depends(get_current_user)):

    if current_user.role == UserRole.PATIENT:
        visits = visit_crud.read_all_visits(
            patient_id=current_user.id,
            start_date=start_date,
            end_date=end_date
        )
    else:

        visits = visit_crud.read_all_visits(
            patient_id=patient_id,
            clinic_id=clinic_id,
            start_date=start_date,
            end_date=end_date
        )
    
    return {"visit_history": visits, "total": len(visits)}


@router.get("/{visit_id}")
async def get_visit(visit_id: str, current_user: User = Depends(get_current_user)):
    visit = visit_crud.read_visit(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Riwayat kunjungan tidak ditemukan")
    
    if current_user.role == UserRole.PATIENT and visit.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Tidak memiliki akses ke riwayat kunjungan ini")
    
    return {"visit_history": visit}