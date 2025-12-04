from fastapi import APIRouter, HTTPException
from modules.items.clinics import (
    create_clinic, read_clinic, read_all_clinics, update_clinic, delete_clinic
)

router = APIRouter()

@router.post("/")
def add_clinic(name: str, description: str = None):
    return create_clinic(name=name, description=description)

@router.get("/")
def get_clinics():
    return read_all_clinics()

@router.get("/{clinic_id}")
def get_clinic(clinic_id: str):
    clinic = read_clinic(clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic

@router.put("/{clinic_id}")
def update(clinic_id: str, name: str = None, description: str = None, is_active: bool = None):
    clinic = update_clinic(clinic_id, name=name, description=description, is_active=is_active)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic

@router.delete("/{clinic_id}")
def delete(clinic_id: str):
    success = delete_clinic(clinic_id)
    if not success:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return {"message": "Clinic deleted"}
