from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, date
from modules.schema.schemas import User, QueueStatus
from modules.items.queues import queues_db
from modules.items.clinics import clinics_db
from modules.items.visits import visits_db
from modules.routes.auth import require_doctor_or_admin

# New imports
import pandas as pd
import os

router = APIRouter()

# --- existing endpoints you had (queue-summary, clinic-density, daily-visits) ---
@router.get("/queue-summary")
async def get_queue_summary(clinic_id: Optional[str] = None,
                           current_user: User = Depends(require_doctor_or_admin)):
    queues = list(queues_db.values())
    
    if clinic_id:
        queues = [q for q in queues if q.clinic_id == clinic_id]
    
    total = len(queues)
    waiting = len([q for q in queues if q.status == QueueStatus.WAITING])
    in_service = len([q for q in queues if q.status == QueueStatus.IN_SERVICE])
    completed = len([q for q in queues if q.status == QueueStatus.COMPLETED])
    cancelled = len([q for q in queues if q.status == QueueStatus.CANCELLED])
    
    completed_queues = [q for q in queues if q.status == QueueStatus.COMPLETED 
                       and q.service_start_time and q.service_end_time]
    
    avg_service_time = 0
    if completed_queues:
        service_times = []
        for q in completed_queues:
            start = datetime.fromisoformat(q.service_start_time)
            end = datetime.fromisoformat(q.service_end_time)
            service_times.append((end - start).total_seconds() / 60)
        avg_service_time = sum(service_times) / len(service_times)
    
    return {
        "total_queues": total,
        "waiting": waiting,
        "in_service": in_service,
        "completed": completed,
        "cancelled": cancelled,
        "average_service_time_minutes": round(avg_service_time, 2)
    }


@router.get("/clinic-density")
async def get_clinic_density(current_user: User = Depends(require_doctor_or_admin)):
    clinics = list(clinics_db.values())
    density_data = []
    
    for clinic in clinics:
        queues = [q for q in queues_db.values() if q.clinic_id == clinic.id]
        waiting = len([q for q in queues if q.status == QueueStatus.WAITING])
        in_service = len([q for q in queues if q.status == QueueStatus.IN_SERVICE])
        
        density_data.append({
            "clinic_id": clinic.id,
            "clinic_name": clinic.name,
            "total_queues": len(queues),
            "waiting": waiting,
            "in_service": in_service,
            "active_patients": waiting + in_service
        })
    
    density_data.sort(key=lambda x: x["active_patients"], reverse=True)
    
    return {"clinic_density": density_data}


@router.get("/daily-visits")
async def get_daily_visits(visit_date: Optional[date] = None,
                          current_user: User = Depends(require_doctor_or_admin)):
    target_date = visit_date or date.today()
    
    visits = [v for v in visits_db.values() 
             if v.visit_date == target_date.isoformat()]
    
    clinic_visits = {}
    for visit in visits:
        if visit.clinic_id not in clinic_visits:
            clinic_visits[visit.clinic_id] = {
                "clinic_id": visit.clinic_id,
                "clinic_name": visit.clinic_name,
                "total_visits": 0
            }
        clinic_visits[visit.clinic_id]["total_visits"] += 1
    
    return {
        "date": target_date.isoformat(),
        "total_visits": len(visits),
        "clinic_breakdown": list(clinic_visits.values())
    }

# ------------------------------------------------------------
# New endpoints using CSV data + pandas
# ------------------------------------------------------------

DATA_DIR = "/mnt/data"  # adjust if data elsewhere

def read_csv_safe(name: str):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=500, detail=f"Data file not found: {path}")
    return pd.read_csv(path)

@router.get("/financial-summary")
async def financial_summary(current_user: User = Depends(require_doctor_or_admin)):
    """
    Returns financial aggregates derived from billing.csv and treatments.csv
    """
    billing = read_csv_safe("billing.csv")
    treatments = read_csv_safe("treatments.csv")

    # ensure necessary columns exist
    # billing: bill_date, amount, payment_status
    # treatments: cost, treatment_date
    try:
        billing["bill_date"] = pd.to_datetime(billing.get("bill_date", None), errors="coerce")
        treatments["treatment_date"] = pd.to_datetime(treatments.get("treatment_date", None), errors="coerce")
    except Exception:
        pass

    total_billed = float(billing["amount"].sum())
    total_paid = float(billing.loc[billing["payment_status"] == "Paid", "amount"].sum())
    outstanding = float(billing.loc[billing["payment_status"] != "Paid", "amount"].sum())

    treatment_cost_total = float(treatments["cost"].sum())
    avg_treatment_cost = float(treatments["cost"].mean()) if not treatments["cost"].empty else 0.0

    # monthly revenue series (Paid)
    paid = billing[billing["payment_status"] == "Paid"].copy()
    if "bill_date" in paid.columns:
        monthly_revenue = paid.groupby(paid["bill_date"].dt.to_period("M"))["amount"].sum().sort_index()
        monthly_revenue = [
            {"month": str(idx), "revenue": float(val)} for idx, val in monthly_revenue.items()
        ]
    else:
        monthly_revenue = []

    return {
        "total_billed": round(total_billed, 2),
        "total_paid": round(total_paid, 2),
        "outstanding": round(outstanding, 2),
        "treatment_cost_total": round(treatment_cost_total, 2),
        "avg_treatment_cost": round(avg_treatment_cost, 2),
        "monthly_revenue": monthly_revenue
    }


@router.get("/operational-summary")
async def operational_summary(current_user: User = Depends(require_doctor_or_admin)):
    """
    Returns operational metrics derived from appointments.csv
    """
    appt = read_csv_safe("appointments.csv")
    # normalize date column
    appt["appointment_date"] = pd.to_datetime(appt.get("appointment_date", None), errors="coerce")
    
    total_appointments = int(len(appt))
    status_counts = appt["status"].value_counts().to_dict()

    # no-show rate
    no_show = int(status_counts.get("No-show", 0))
    no_show_rate = round((no_show / total_appointments) * 100, 2) if total_appointments > 0 else 0.0

    # appointments per doctor (top 10)
    per_doctor = appt["doctor_id"].value_counts().head(10).to_dict()

    # monthly visits
    if "appointment_date" in appt.columns:
        monthly_visits = appt.groupby(appt["appointment_date"].dt.to_period("M"))["appointment_id"].count().sort_index()
        monthly_visits = [{"month": str(idx), "visits": int(val)} for idx, val in monthly_visits.items()]
    else:
        monthly_visits = []

    return {
        "total_appointments": total_appointments,
        "status_counts": status_counts,
        "no_show_count": no_show,
        "no_show_rate_percent": no_show_rate,
        "top_doctors_by_appointments": per_doctor,
        "monthly_visits": monthly_visits
    }


@router.get("/patient-summary")
async def patient_summary(current_user: User = Depends(require_doctor_or_admin)):
    """
    Returns patient demographics + behavioral metrics
    """
    patients = read_csv_safe("patients_new.csv")
    appointments = read_csv_safe("appointments.csv")

    # prepare
    patients["date_of_birth"] = pd.to_datetime(patients.get("date_of_birth", None), errors="coerce")
    appointments["appointment_date"] = pd.to_datetime(appointments.get("appointment_date", None), errors="coerce")

    # age calc (using end of year if missing)
    def compute_age(dob):
        if pd.isna(dob):
            return None
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    patients["age"] = patients["date_of_birth"].apply(lambda x: compute_age(x) if pd.notnull(x) else None)

    # basic age stats
    age_series = patients["age"].dropna().astype(int)
    age_stats = {}
    if not age_series.empty:
        age_stats = {
            "count": int(age_series.count()),
            "mean": float(round(age_series.mean(), 2)),
            "min": int(age_series.min()),
            "max": int(age_series.max()),
            "median": float(age_series.median())
        }

    # gender distribution
    gender_counts = patients["gender"].value_counts().to_dict()

    # visits per gender: need to merge
    merged = appointments.merge(patients[["patient_id","gender","age"]], on="patient_id", how="left")
    visits_by_gender = merged["gender"].value_counts().to_dict()

    # visits by age group per month
    # define age groups
    merged["age_group"] = pd.cut(merged["age"], bins=[0,17,30,45,60,200], labels=["0-17","18-30","31-45","46-60","60+"])
    if "appointment_date" in merged.columns:
        monthly_age_group = merged.groupby([merged["appointment_date"].dt.to_period("M"), "age_group"])["appointment_id"].count().unstack(fill_value=0).sort_index()
        monthly_age_group_out = []
        for period in monthly_age_group.index:
            row = {"month": str(period)}
            for grp in monthly_age_group.columns:
                row[str(grp)] = int(monthly_age_group.loc[period, grp])
            monthly_age_group_out.append(row)
    else:
        monthly_age_group_out = []

    return {
        "age_stats": age_stats,
        "gender_counts": gender_counts,
        "visits_by_gender": visits_by_gender,
        "monthly_visits_by_age_group": monthly_age_group_out
    }
