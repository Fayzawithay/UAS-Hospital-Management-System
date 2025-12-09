from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ================= ENUM =================

class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class QueueStatus(str, Enum):
    WAITING = "menunggu"
    IN_SERVICE = "sedang_dilayani"
    COMPLETED = "selesai"
    CANCELLED = "dibatalkan"


# ================= CORE MODEL =================

class User(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: str
    role: UserRole
    medical_record_number: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


class Clinic(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


class Doctor(BaseModel):
    id: str
    name: str
    specialization: str
    clinic_id: str
    clinic_name: Optional[str] = None
    phone: str
    is_available: bool = True
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


class Queue(BaseModel):
    id: str
    queue_number: str
    patient_id: str
    patient_name: str
    clinic_id: str
    clinic_name: str
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    status: QueueStatus
    registration_time: str
    called_time: Optional[str] = None
    service_start_time: Optional[str] = None
    service_end_time: Optional[str] = None
    notes: Optional[str] = None


# =============== VISIT HISTORY (ALA KAGGLE) =================
class VisitHistory(BaseModel):
    id: str                # record id
    queue_id: str
    patient_id: str
    patient_name: str
    clinic_id: str
    clinic_name: str
    doctor_id: str
    doctor_name: str
    visit_date: str        # isoformat tanggal kunjungan

    # kolom ala dataset Kaggle Medical Appointment
    reason: str
    payment_amount: float
    mode_of_payment: str
    mode_of_appointment: str
    appointment_status: str = "Completed"


# ================== AUTH / USER REQUEST ====================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str
    role: UserRole = UserRole.PATIENT


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ================== CLINIC / DOCTOR REQUEST =================

class ClinicCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ClinicUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DoctorCreate(BaseModel):
    name: str
    specialization: str
    clinic_id: str
    phone: str


class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialization: Optional[str] = None
    clinic_id: Optional[str] = None
    phone: Optional[str] = None
    is_available: Optional[bool] = None


# ================== QUEUE REQUEST =================

class QueueRegisterRequest(BaseModel):
    clinic_id: str
    doctor_id: Optional[str] = None


# BODY UNTUK /queues/{id}/complete – DISESUAIKAN DENGAN DATASET KAGGLE
class CompleteQueueRequest(BaseModel):
    reason: str
    payment_amount: float
    mode_of_payment: str
    mode_of_appointment: str
