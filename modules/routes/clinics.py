from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from modules.schema.schemas import ClinicCreate, ClinicUpdate, User
from modules.items import clinics as clinic_crud
from modules.routes.auth import get_current_user, require_admin

router = APIRouter()


@router.post("", status_code=201)
async def create_clinic(data: ClinicCreate, current_user: User = Depends(require_admin)):
    try:
        clinic = clinic_crud.create_clinic(
            name=data.name,
            description=data.description
        )
        return {"message": "Klinik berhasil ditambahkan", "clinic": clinic}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def get_all_clinics(is_active: Optional[bool] = None):
    clinics = clinic_crud.read_all_clinics(is_active=is_active)
    return {"clinics": clinics, "total": len(clinics)}


@router.get("/{clinic_id}")
async def get_clinic(clinic_id: str):
    clinic = clinic_crud.read_clinic(clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Klinik tidak ditemukan")
    return {"clinic": clinic}


@router.put("/{clinic_id}")
async def update_clinic(clinic_id: str, data: ClinicUpdate, 
                       current_user: User = Depends(require_admin)):
    try:
        clinic = clinic_crud.update_clinic(
            clinic_id=clinic_id,
            name=data.name,
            description=data.description,
            is_active=data.is_active
        )
        if not clinic:
            raise HTTPException(status_code=404, detail="Klinik tidak ditemukan")
        return {"message": "Klinik berhasil diupdate", "clinic": clinic}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{clinic_id}")
async def delete_clinic(clinic_id: str, current_user: User = Depends(require_admin)):
    try:
        success = clinic_crud.delete_clinic(clinic_id)
        if not success:
            raise HTTPException(status_code=404, detail="Klinik tidak ditemukan")
        return {"message": "Klinik berhasil dihapus"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))