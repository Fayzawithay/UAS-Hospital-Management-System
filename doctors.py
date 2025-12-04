# modules/items/doctors.py

import uuid
from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy.orm import Session

from modules.schema.schemas import Doctor
from modules.db_models import DoctorDB, ClinicDB
from database import SessionLocal

# Dummy cache supaya import lama tidak error
doctors_db: Dict[str, Doctor] = {}


def _to_schema(db_obj: DoctorDB) -> Doctor:
    """Convert SQLAlchemy DoctorDB → Pydantic Doctor."""
    return Doctor(
        id=db_obj.id,
        name=db_obj.name,
        specialization=db_obj.specialization,
        clinic_id=db_obj.clinic_id,
        clinic_name=db_obj.clinic_name,
        phone=db_obj.phone,
        is_available=db_obj.is_available,
        created_at=db_obj.created_at.isoformat() if db_obj.created_at else None,
    )


# CREATE
def create_doctor(name: str, specialization: str, clinic_id: str, phone: str) -> Doctor:
    db: Session = SessionLocal()
    try:
        # Pastikan klinik ada
        clinic = db.query(ClinicDB).filter(ClinicDB.id == clinic_id).first()
        if not clinic:
            raise ValueError("Klinik tidak ditemukan")

        # Generate ID doctor-xxx
        last = (
            db.query(DoctorDB)
            .order_by(DoctorDB.id.desc())
            .first()
        )

        if last and last.id.startswith("doctor-"):
            try:
                last_num = int(last.id.split("-")[1])
            except ValueError:
                last_num = 0
        else:
            last_num = 0

        doctor_id = f"doctor-{last_num + 1:03d}"

        db_doctor = DoctorDB(
            id=doctor_id,
            name=name,
            specialization=specialization,
            clinic_id=clinic_id,
            clinic_name=clinic.name,
            phone=phone,
            is_available=True,
            created_at=datetime.now(),
        )

        db.add(db_doctor)
        db.commit()
        db.refresh(db_doctor)

        schema_doctor = _to_schema(db_doctor)
        doctors_db[schema_doctor.id] = schema_doctor  # sync ringan
        return schema_doctor
    finally:
        db.close()


# READ (single)
def read_doctor(doctor_id: str) -> Optional[Doctor]:
    db: Session = SessionLocal()
    try:
        d = db.query(DoctorDB).filter(DoctorDB.id == doctor_id).first()
        if not d:
            return None
        schema = _to_schema(d)
        doctors_db[doctor_id] = schema
        return schema
    finally:
        db.close()


# READ ALL
def read_all_doctors(clinic_id: Optional[str] = None, is_available: Optional[bool] = None) -> List[Doctor]:
    db: Session = SessionLocal()
    try:
        q = db.query(DoctorDB)

        if clinic_id:
            q = q.filter(DoctorDB.clinic_id == clinic_id)

        if is_available is not None:
            q = q.filter(DoctorDB.is_available == is_available)

        results = q.all()

        doctors_db.clear()
        items: List[Doctor] = []

        for d in results:
            schema = _to_schema(d)
            items.append(schema)
            doctors_db[schema.id] = schema

        return items
    finally:
        db.close()


# UPDATE
def update_doctor(doctor_id: str, **kwargs) -> Optional[Doctor]:
    db: Session = SessionLocal()
    try:
        db_doctor = db.query(DoctorDB).filter(DoctorDB.id == doctor_id).first()
        if not db_doctor:
            return None

        # Jika pindah klinik, ambil nama klinik baru
        if "clinic_id" in kwargs and kwargs["clinic_id"]:
            clinic = db.query(ClinicDB).filter(ClinicDB.id == kwargs["clinic_id"]).first()
            if not clinic:
                raise ValueError("Klinik tidak ditemukan")
            kwargs["clinic_name"] = clinic.name

        # Update allowed fields
        editable = {
            "name", "specialization", "clinic_id",
            "clinic_name", "phone", "is_available"
        }

        for key, value in kwargs.items():
            if key in editable and value is not None:
                setattr(db_doctor, key, value)

        db.commit()
        db.refresh(db_doctor)

        schema = _to_schema(db_doctor)
        doctors_db[doctor_id] = schema
        return schema
    finally:
        db.close()


# DELETE
def delete_doctor(doctor_id: str) -> bool:
    db: Session = SessionLocal()
    try:
        db_doctor = db.query(DoctorDB).filter(DoctorDB.id == doctor_id).first()
        if not db_doctor:
            return False

        db.delete(db_doctor)
        db.commit()

        if doctor_id in doctors_db:
            del doctors_db[doctor_id]

        return True
    finally:
        db.close()
