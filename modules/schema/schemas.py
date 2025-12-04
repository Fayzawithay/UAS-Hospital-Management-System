from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime
from enum import Enum

# ===============================================
# ENUM
# ===============================================

class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"

class QueueStatus(str, Enum):
    WAITING = "menunggu"
    IN_SERVICE = "sedang_dilayani"
    COMPLETED = "selesai"
    CANCELLED = "dibatalkan"


# ===============================================
# USER (Queue System)
# ===============================================

class User(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: str
    role: UserRole
    medical_record_number: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ===============================================
# CLINIC (Queue System)
# ===============================================

class Clinic(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ===============================================
# DOCTOR (Queue System)
# ===============================================

class Doctor(BaseModel):
    id: str
    name: str
    specialization: str
    clinic_id: str
    clinic_name: Optional[str] = None
    phone: str
    is_available: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ===============================================
# QUEUE (Queue System)
# ===============================================

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


# ===============================================
# VISIT HISTORY (Queue System)
# ===============================================

class VisitHistory(BaseModel):
    id: str                # record id
    queue_id: str

    patient_id: str
    patient_name: str

    clinic_id: str
    clinic_name: str

    doctor_id: str
    doctor_name: str

    visit_date: str

    reason: str
    payment_amount: float
    mode_of_payment: str
    mode_of_appointment: str
    appointment_status: str = "Completed"


# ===============================================
# AUTH (Queue System)
# ===============================================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str
    role: UserRole = UserRole.PATIENT

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ===============================================
# CLINIC / DOCTOR REQUEST (Queue System)
# ===============================================

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


# ===============================================
# QUEUE REQUEST (Queue System)
# ===============================================

class QueueRegisterRequest(BaseModel):
    clinic_id: str
    doctor_id: Optional[str] = None

class CompleteQueueRequest(BaseModel):
    reason: str
    payment_amount: float
    mode_of_payment: str
    mode_of_appointment: str


# =====================================================
# =====================================================
# ==========      HOSPITAL MEDICAL SYSTEM     =========
# =====================================================
# =====================================================

# ============================
# PATIENTS
# ============================
class PatientBase(BaseModel):
    patient_name: str
    gender: str
    date_of_birth: date
    contact_number: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    registration_date: Optional[date] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None

class PatientCreate(PatientBase):
    password: str

class PatientResponse(PatientBase):
    patient_id: int
    class Config:
        orm_mode = True


# ============================
# DOCTORS (MySQL Medical)
# ============================
class HospitalDoctorBase(BaseModel):
    doctors_name: str
    specialization: Optional[str] = None
    phone_number: Optional[str] = None
    years_experience: Optional[int] = None
    hospital_branch: Optional[str] = None
    email: Optional[str] = None

class HospitalDoctorCreate(HospitalDoctorBase):
    password: str

class HospitalDoctorResponse(HospitalDoctorBase):
    doctor_id: int
    class Config:
        orm_mode = True


# ============================
# APPOINTMENTS
# ============================
class AppointmentBase(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: Optional[str] = None
    reason_for_visit: Optional[str] = None
    status: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentResponse(AppointmentBase):
    appointment_id: int
    class Config:
        orm_mode = True


# ============================
# TREATMENTS
# ============================
class TreatmentBase(BaseModel):
    appointment_id: int
    treatment_type: Optional[str] = None
    description: Optional[str] = None
    cost: Optional[float] = None
    treatment_date: Optional[date] = None

class TreatmentCreate(TreatmentBase):
    pass

class TreatmentResponse(TreatmentBase):
    treatment_id: int
    class Config:
        orm_mode = True


# ============================
# BILLING
# ============================
class BillingBase(BaseModel):
    patient_id: int
    treatment_id: int
    bill_date: Optional[date] = None
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None

class BillingCreate(BillingBase):
    pass

class BillingResponse(BillingBase):
    bill_id: int
    class Config:
        orm_mode = True


# ============================
# RECORD (MASTER RECORD)
# ============================
class RecordBase(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    doctor_id: Optional[int] = None
    treatment_id: Optional[int] = None
    bill_id: Optional[int] = None

class RecordCreate(RecordBase):
    pass

class RecordResponse(RecordBase):
    record_id: int
    class Config:
        orm_mode = True
