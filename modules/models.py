from sqlalchemy import Column, Integer, String, Date, Time, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

# ============================
#        PATIENTS
# ============================
class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_name = Column(String(100), nullable=False)
    gender = Column(String(10), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    contact_number = Column(String(20))
    address = Column(String(255))
    email = Column(String(100), unique=True)
    password = Column(String(255))
    registration_date = Column(Date)
    insurance_provider = Column(String(100))
    insurance_number = Column(String(50))

    # relationships
    appointments = relationship("Appointment", back_populates="patient")
    bills = relationship("Billing", back_populates="patient")
    records = relationship("Record", back_populates="patient")


# ============================
#        DOCTORS
# ============================
class Doctor(Base):
    __tablename__ = "doctors"

    doctor_id = Column(Integer, primary_key=True, autoincrement=True)
    doctors_name = Column(String(100), nullable=False)
    specialization = Column(String(100))
    phone_number = Column(String(20))
    years_experience = Column(Integer)
    hospital_branch = Column(String(100))
    email = Column(String(100), unique=True)
    password = Column(String(255))

    # relationships
    appointments = relationship("Appointment", back_populates="doctor")


# ============================
#        APPOINTMENTS
# ============================
class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"))
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time)
    reason_for_visit = Column(String(255))
    status = Column(String(50))  # e.g., Scheduled, Completed, Canceled

    # relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    treatments = relationship("Treatment", back_populates="appointment")
    records = relationship("Record", back_populates="appointment")


# ============================
#        TREATMENTS
# ============================
class Treatment(Base):
    __tablename__ = "treatments"

    treatment_id = Column(Integer, primary_key=True, autoincrement=True)
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id"))
    treatment_type = Column(String(100))
    description = Column(String(255))
    cost = Column(Float)
    treatment_date = Column(Date)

    # relationships
    appointment = relationship("Appointment", back_populates="treatments")
    bills = relationship("Billing", back_populates="treatment")
    records = relationship("Record", back_populates="treatment")


# ============================
#        BILLING
# ============================
class Billing(Base):
    __tablename__ = "billing"

    bill_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    treatment_id = Column(Integer, ForeignKey("treatments.treatment_id"))
    bill_date = Column(Date)
    amount = Column(Float)
    payment_method = Column(String(50))
    payment_status = Column(String(50))  # Paid, Pending, Failed

    # relationships
    patient = relationship("Patient", back_populates="bills")
    treatment = relationship("Treatment", back_populates="bills")
    records = relationship("Record", back_populates="billing")


# ============================
#        MAIN RECORDS
# ============================
class Record(Base):
    __tablename__ = "records"

    record_id = Column(Integer, primary_key=True, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("billing.bill_id"))
    patient_id = Column(Integer, ForeignKey("patients.patient_id"))
    patient_name = Column(String(100))
    gender = Column(String(10))
    date_of_birth = Column(Date)
    contact_number = Column(String(20))
    address = Column(String(255))
    email_x = Column(String(100))
    registration_date = Column(Date)
    insurance_provider = Column(String(100))
    insurance_number = Column(String(50))
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id"))
    appointment_date = Column(Date)
    doctor_id = Column(Integer, ForeignKey("doctors.doctor_id"))
    doctor_name = Column(String(100))
    reason_for_visit = Column(String(255))
    treatment_id = Column(Integer, ForeignKey("treatments.treatment_id"))
    treatment_type = Column(String(100))
    description = Column(String(255))
    treatment_date = Column(Date)
    cost = Column(Float)
    bill_date = Column(Date)
    amount = Column(Float)
    payment_method = Column(String(50))
    payment_status = Column(String(50))

    # relationships
    patient = relationship("Patient", back_populates="records")
    appointment = relationship("Appointment", back_populates="records")
    treatment = relationship("Treatment", back_populates="records")
    billing = relationship("Billing", back_populates="records")
