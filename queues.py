# modules/items/queues.py

import uuid
from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy.orm import Session

from modules.schema.schemas import Queue, QueueStatus
from modules.db_models import QueueDB, ClinicDB, DoctorDB
from database import SessionLocal

# Cache ringan supaya kode lama yang mungkin masih mengimport queues_db
# dan queue_counters tidak langsung rusak. Sumber data utama tetap MySQL.
queues_db: Dict[str, Queue] = {}
queue_counters: Dict[str, int] = {}


def _to_schema(db_obj: QueueDB) -> Queue:
    """Convert SQLAlchemy QueueDB -> Pydantic Queue."""
    return Queue(
        id=db_obj.id,
        queue_number=db_obj.queue_number,
        patient_id=db_obj.patient_id,
        patient_name=db_obj.patient_name,
        clinic_id=db_obj.clinic_id,
        clinic_name=db_obj.clinic_name,
        doctor_id=db_obj.doctor_id,
        doctor_name=db_obj.doctor_name,
        status=QueueStatus(db_obj.status),
        registration_time=db_obj.registration_time,
        called_time=db_obj.called_time,
        service_start_time=db_obj.service_start_time,
        service_end_time=db_obj.service_end_time,
        notes=db_obj.notes,
    )


def create_queue(
    patient_id: str,
    patient_name: str,
    clinic_id: str,
    doctor_id: Optional[str] = None,
) -> Queue:
    """
    Buat antrean baru dan simpan ke MySQL.
    Validasi:
      - klinik harus ada & aktif
      - kalau ada doctor_id, dokternya harus ada, available, dan kliniknya sama
    """
    db: Session = SessionLocal()
    try:
        # Cek klinik
        clinic = db.query(ClinicDB).filter(ClinicDB.id == clinic_id).first()
        if not clinic or not clinic.is_active:
            raise ValueError("Klinik tidak ditemukan atau tidak aktif")

        # Cek dokter kalau ada
        doctor_name = None
        if doctor_id:
            doctor = db.query(DoctorDB).filter(DoctorDB.id == doctor_id).first()
            if (
                not doctor
                or not doctor.is_available
                or doctor.clinic_id != clinic_id
            ):
                raise ValueError("Dokter tidak ditemukan atau tidak tersedia")
            doctor_name = doctor.name

        # Hitung nomor antrean per klinik (seperti queue_counters dulu)
        count_for_clinic = (
            db.query(QueueDB)
            .filter(QueueDB.clinic_id == clinic_id)
            .count()
        )
        next_num = count_for_clinic + 1
        prefix = (clinic.name[:3] or clinic.name).upper()
        queue_number = f"{prefix}{next_num:03d}"

        now_iso = datetime.now().isoformat()

        db_queue = QueueDB(
            id=str(uuid.uuid4()),
            queue_number=queue_number,
            patient_id=patient_id,
            patient_name=patient_name,
            clinic_id=clinic_id,
            clinic_name=clinic.name,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            status=QueueStatus.WAITING.value,
            registration_time=now_iso,
            called_time=None,
            service_start_time=None,
            service_end_time=None,
            notes=None,
            created_at=datetime.now(),
        )

        db.add(db_queue)
        db.commit()
        db.refresh(db_queue)

        schema_queue = _to_schema(db_queue)
        queues_db[schema_queue.id] = schema_queue
        queue_counters[clinic_id] = next_num
        return schema_queue
    finally:
        db.close()


def read_queue(queue_id: str) -> Optional[Queue]:
    db: Session = SessionLocal()
    try:
        q = db.query(QueueDB).filter(QueueDB.id == queue_id).first()
        if not q:
            return None
        schema = _to_schema(q)
        queues_db[queue_id] = schema
        return schema
    finally:
        db.close()


def read_all_queues(
    clinic_id: Optional[str] = None,
    status: Optional[QueueStatus] = None,
    patient_id: Optional[str] = None,
) -> List[Queue]:
    db: Session = SessionLocal()
    try:
        q = db.query(QueueDB)

        if clinic_id:
            q = q.filter(QueueDB.clinic_id == clinic_id)
        if status is not None:
            q = q.filter(QueueDB.status == status.value)
        if patient_id:
            q = q.filter(QueueDB.patient_id == patient_id)

        # Urutkan berdasarkan waktu registrasi (string isoformat → aman)
        q = q.order_by(QueueDB.registration_time.asc())

        db_queues = q.all()

        queues_db.clear()
        result: List[Queue] = []

        for item in db_queues:
            schema = _to_schema(item)
            result.append(schema)
            queues_db[schema.id] = schema

        return result
    finally:
        db.close()


def update_queue_status(queue_id: str, status: QueueStatus, **kwargs) -> Optional[Queue]:
    db: Session = SessionLocal()
    try:
        db_queue = db.query(QueueDB).filter(QueueDB.id == queue_id).first()
        if not db_queue:
            return None

        db_queue.status = status.value

        now_iso = datetime.now().isoformat()
        if status == QueueStatus.IN_SERVICE:
            if not db_queue.called_time:
                db_queue.called_time = now_iso
            if not db_queue.service_start_time:
                db_queue.service_start_time = now_iso
        elif status == QueueStatus.COMPLETED:
            db_queue.service_end_time = now_iso

        # Update field lain (notes, doctor_id, doctor_name, dll) kalau ada di kwargs
        for key, value in kwargs.items():
            if value is None:
                continue
            if hasattr(db_queue, key):
                setattr(db_queue, key, value)

        db.commit()
        db.refresh(db_queue)

        schema = _to_schema(db_queue)
        queues_db[queue_id] = schema
        return schema
    finally:
        db.close()


def delete_queue(queue_id: str) -> bool:
    db: Session = SessionLocal()
    try:
        db_queue = db.query(QueueDB).filter(QueueDB.id == queue_id).first()
        if not db_queue:
            return False

        db.delete(db_queue)
        db.commit()

        if queue_id in queues_db:
            del queues_db[queue_id]
        return True
    finally:
        db.close()


def get_queue_position(queue_id: str) -> int:
    """
    Posisi antrean: urutan di antara antrean lain di klinik yang statusnya WAITING.
    """
    db: Session = SessionLocal()
    try:
        db_queue = db.query(QueueDB).filter(QueueDB.id == queue_id).first()
        if not db_queue or db_queue.status != QueueStatus.WAITING.value:
            return 0

        waiting = (
            db.query(QueueDB)
            .filter(
                QueueDB.clinic_id == db_queue.clinic_id,
                QueueDB.status == QueueStatus.WAITING.value,
            )
            .order_by(QueueDB.registration_time.asc())
            .all()
        )

        for i, q in enumerate(waiting, start=1):
            if q.id == queue_id:
                return i
        return 0
    finally:
        db.close()
