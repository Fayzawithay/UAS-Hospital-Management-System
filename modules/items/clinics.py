# modules/items/clinics.py

from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy.orm import Session

from modules.schema.schemas import Clinic          # Pydantic schema
from modules.db_models import ClinicDB             # SQLAlchemy model
from database import SessionLocal

# Dummy dict supaya import lama di routes/statistics.py ("clinics_db") tidak error.
# Sekarang tidak dipakai untuk penyimpanan utama, hanya biar kompatibel.
clinics_db: Dict[str, Clinic] = {}


def _to_schema(db_obj: ClinicDB) -> Clinic:
    """Konversi object SQLAlchemy ke Pydantic Clinic."""
    return Clinic(
        id=db_obj.id,
        name=db_obj.name,
        description=db_obj.description,
        is_active=bool(db_obj.is_active),
        created_at=db_obj.created_at.isoformat() if db_obj.created_at else None,
    )


def create_clinic(name: str, description: Optional[str] = None) -> Clinic:
    """Buat klinik baru dan simpan ke MySQL."""
    db: Session = SessionLocal()
    try:
        # Cari id terakhir "clinic-xxx"
        last = (
            db.query(ClinicDB)
            .order_by(ClinicDB.id.desc())
            .first()
        )

        if last and last.id.startswith("clinic-"):
            try:
                last_num = int(last.id.split("-")[1])
            except ValueError:
                last_num = 0
        else:
            last_num = 0

        clinic_id = f"clinic-{last_num + 1:03d}"

        db_clinic = ClinicDB(
            id=clinic_id,
            name=name,
            description=description,
            is_active=True,
            created_at=datetime.now(),
        )

        db.add(db_clinic)
        db.commit()
        db.refresh(db_clinic)

        clinic_schema = _to_schema(db_clinic)

        # Optional: sync ke clinics_db biar kalau ada kode lama yang baca ini nggak kosong banget
        clinics_db[clinic_schema.id] = clinic_schema

        return clinic_schema
    finally:
        db.close()


def read_clinic(clinic_id: str) -> Optional[Clinic]:
    """Ambil 1 klinik dari MySQL berdasarkan id."""
    db: Session = SessionLocal()
    try:
        db_clinic = db.query(ClinicDB).filter(ClinicDB.id == clinic_id).first()
        if not db_clinic:
            return None
        clinic_schema = _to_schema(db_clinic)
        clinics_db[clinic_schema.id] = clinic_schema  # sync ringan
        return clinic_schema
    finally:
        db.close()


def read_all_clinics(is_active: Optional[bool] = None) -> List[Clinic]:
    """Ambil semua klinik (bisa difilter aktif/tidak)."""
    db: Session = SessionLocal()
    try:
        q = db.query(ClinicDB)
        if is_active is not None:
            q = q.filter(ClinicDB.is_active == is_active)
        db_clinics = q.all()

        clinics: List[Clinic] = []
        clinics_db.clear()

        for c in db_clinics:
            clinic_schema = _to_schema(c)
            clinics.append(clinic_schema)
            clinics_db[clinic_schema.id] = clinic_schema

        return clinics
    finally:
        db.close()


def update_clinic(clinic_id: str, **kwargs) -> Optional[Clinic]:
    """Update data klinik di MySQL."""
    db: Session = SessionLocal()
    try:
        db_clinic = db.query(ClinicDB).filter(ClinicDB.id == clinic_id).first()
        if not db_clinic:
            return None

        for key, value in kwargs.items():
            if hasattr(db_clinic, key) and value is not None:
                setattr(db_clinic, key, value)

        db.commit()
        db.refresh(db_clinic)

        clinic_schema = _to_schema(db_clinic)
        clinics_db[clinic_schema.id] = clinic_schema
        return clinic_schema
    finally:
        db.close()


def delete_clinic(clinic_id: str) -> bool:
    """Hapus klinik dari MySQL."""
    db: Session = SessionLocal()
    try:
        db_clinic = db.query(ClinicDB).filter(ClinicDB.id == clinic_id).first()
        if not db_clinic:
            return False

        db.delete(db_clinic)
        db.commit()

        if clinic_id in clinics_db:
            del clinics_db[clinic_id]

        return True
    finally:
        db.close()
