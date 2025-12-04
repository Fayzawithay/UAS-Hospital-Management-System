# modules/items/visits.py

import uuid
from typing import Optional, List, Dict
from datetime import date, datetime

from sqlalchemy.orm import Session

from modules.schema.schemas import VisitHistory
from modules.db_models import VisitHistoryDB
from database import SessionLocal

# Cache ringan
visits_db: Dict[str, VisitHistory] = {}


def _to_schema(db_obj: VisitHistoryDB) -> VisitHistory:
    """Convert SQLAlchemy VisitHistoryDB -> Pydantic VisitHistory."""
    return VisitHistory(
        id=db_obj.id,
        queue_id=db_obj.queue_id,
        patient_id=db_obj.patient_id,
        patient_name=db_obj.patient_name,
        clinic_id=db_obj.clinic_id,
        clinic_name=db_obj.clinic_name,
        doctor_id=db_obj.doctor_id,
        doctor_name=db_obj.doctor_name,
        visit_date=db_obj.visit_date,
        reason=db_obj.reason,
        payment_amount=db_obj.payment_amount,
        mode_of_payment=db_obj.mode_of_payment,
        mode_of_appointment=db_obj.mode_of_appointment,
        appointment_status=db_obj.appointment_status,
    )


def create_visit(
    queue_id: str,
    patient_id: str,
    patient_name: str,
    clinic_id: str,
    clinic_name: str,
    doctor_id: str,
    doctor_name: str,
    reason: str,
    payment_amount: float,
    mode_of_payment: str,
    mode_of_appointment: str,
) -> VisitHistory:
    """
    Membuat catatan kunjungan (medical record) untuk satu antrean.
    Disimpan ke tabel visits di MySQL.
    """
    db: Session = SessionLocal()
    try:
        today = date.today().isoformat()

        db_visit = VisitHistoryDB(
            id=str(uuid.uuid4()),
            queue_id=queue_id,
            patient_id=patient_id,
            patient_name=patient_name,
            clinic_id=clinic_id,
            clinic_name=clinic_name,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            visit_date=today,
            reason=reason,
            payment_amount=payment_amount,
            mode_of_payment=mode_of_payment,
            mode_of_appointment=mode_of_appointment,
            appointment_status="Completed",
            created_at=datetime.now(),
        )

        db.add(db_visit)
        db.commit()
        db.refresh(db_visit)

        schema = _to_schema(db_visit)
        visits_db[schema.id] = schema
        return schema
    finally:
        db.close()


def read_visit(visit_id: str) -> Optional[VisitHistory]:
    db: Session = SessionLocal()
    try:
        v = db.query(VisitHistoryDB).filter(VisitHistoryDB.id == visit_id).first()
        if not v:
            return None
        schema = _to_schema(v)
        visits_db[visit_id] = schema
        return schema
    finally:
        db.close()


def read_all_visits(
    patient_id: Optional[str] = None,
    clinic_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[VisitHistory]:
    db: Session = SessionLocal()
    try:
        q = db.query(VisitHistoryDB)

        if patient_id:
            q = q.filter(VisitHistoryDB.patient_id == patient_id)
        if clinic_id:
            q = q.filter(VisitHistoryDB.clinic_id == clinic_id)
        if start_date:
            start_str = start_date.isoformat()
            q = q.filter(VisitHistoryDB.visit_date >= start_str)
        if end_date:
            end_str = end_date.isoformat()
            q = q.filter(VisitHistoryDB.visit_date <= end_str)

        q = q.order_by(VisitHistoryDB.visit_date.desc())

        db_visits = q.all()

        visits_db.clear()
        result: List[VisitHistory] = []

        for v in db_visits:
            schema = _to_schema(v)
            result.append(schema)
            visits_db[schema.id] = schema

        return result
    finally:
        db.close()


def update_visit(visit_id: str, **kwargs) -> Optional[VisitHistory]:
    db: Session = SessionLocal()
    try:
        db_visit = db.query(VisitHistoryDB).filter(VisitHistoryDB.id == visit_id).first()
        if not db_visit:
            return None

        editable = {
            "reason",
            "payment_amount",
            "mode_of_payment",
            "mode_of_appointment",
            "appointment_status",
        }

        for key, value in kwargs.items():
            if key in editable and value is not None:
                setattr(db_visit, key, value)

        db.commit()
        db.refresh(db_visit)

        schema = _to_schema(db_visit)
        visits_db[visit_id] = schema
        return schema
    finally:
        db.close()


def delete_visit(visit_id: str) -> bool:
    db: Session = SessionLocal()
    try:
        db_visit = db.query(VisitHistoryDB).filter(VisitHistoryDB.id == visit_id).first()
        if not db_visit:
            return False

        db.delete(db_visit)
        db.commit()

        if visit_id in visits_db:
            del visits_db[visit_id]
        return True
    finally:
        db.close()


def get_visits_by_queue(queue_id: str) -> Optional[VisitHistory]:
    db: Session = SessionLocal()
    try:
        v = (
            db.query(VisitHistoryDB)
            .filter(VisitHistoryDB.queue_id == queue_id)
            .order_by(VisitHistoryDB.visit_date.desc())
            .first()
        )
        if not v:
            return None
        schema = _to_schema(v)
        visits_db[schema.id] = schema
        return schema
    finally:
        db.close()
