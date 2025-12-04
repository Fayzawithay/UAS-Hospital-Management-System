# modules/db_models.py

from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Float
from database import Base


# ================= CLINIC =================

class ClinicDB(Base):
    __tablename__ = "clinics"

    id = Column(String(50), primary_key=True, index=True)  # contoh: "clinic-001"
    name = Column(String(255), nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ================= USER =================

class UserDB(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50), nullable=False)
    role = Column(String(50), nullable=False)  # "patient", "doctor", "admin"
    medical_record_number = Column(String(50), nullable=True)
    password_hash = Column(String(255), nullable=False)   # password yang sudah di-hash
    created_at = Column(DateTime, default=datetime.utcnow)


# ================= DOCTOR =================

class DoctorDB(Base):
    __tablename__ = "doctors"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    specialization = Column(String(255), nullable=False)
    clinic_id = Column(String(50), nullable=False)
    clinic_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ================= QUEUE (ANTRIAN) =================

class QueueDB(Base):
    __tablename__ = "queues"

    id = Column(String(50), primary_key=True, index=True)
    queue_number = Column(String(50), nullable=False)

    patient_id = Column(String(50), nullable=False)
    patient_name = Column(String(255), nullable=False)

    clinic_id = Column(String(50), nullable=False)
    clinic_name = Column(String(255), nullable=False)

    doctor_id = Column(String(50), nullable=True)
    doctor_name = Column(String(255), nullable=True)

    status = Column(String(50), nullable=False)  # "menunggu", "sedang_dilayani", "selesai", "dibatalkan"

    registration_time = Column(String(50), nullable=False)   # disimpan sebagai string ISO
    called_time = Column(String(50), nullable=True)
    service_start_time = Column(String(50), nullable=True)
    service_end_time = Column(String(50), nullable=True)

    notes = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ================= VISIT HISTORY =================

class VisitHistoryDB(Base):
    __tablename__ = "visits"

    id = Column(String(50), primary_key=True, index=True)
    queue_id = Column(String(50), nullable=False)

    patient_id = Column(String(50), nullable=False)
    patient_name = Column(String(255), nullable=False)

    clinic_id = Column(String(50), nullable=False)
    clinic_name = Column(String(255), nullable=False)

    doctor_id = Column(String(50), nullable=False)
    doctor_name = Column(String(255), nullable=False)

    visit_date = Column(String(50), nullable=False)  # isoformat string

    reason = Column(String(255), nullable=False)
    payment_amount = Column(Float, nullable=False)
    mode_of_payment = Column(String(50), nullable=False)
    mode_of_appointment = Column(String(50), nullable=False)
    appointment_status = Column(String(50), nullable=False, default="Completed")

    created_at = Column(DateTime, default=datetime.utcnow)
