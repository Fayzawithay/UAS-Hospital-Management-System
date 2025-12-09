# modules/routes/statistics.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, case, Integer

# sesuaikan import path get_db dengan proyekmu
from dependency import get_db  # <-- jika get_db() ada di deps.py
from modules.routes.auth import require_doctor_or_admin
from modules.schema.schemas import User  # <-- auth user schema

# --- ORM models: sesuaikan path import sesuai struktur project ---
# If your models are in models.py, import from there; if in modules.models, change path.
try:
    from models import Patient, Doctor, Appointment, Treatment, Billing, Record  # <-- adjust
except Exception:
    # fallback: try modules.models or modules.db_models
    try:
        from modules.models import Patient, Doctor, Appointment, Treatment, Billing, Record
    except Exception:
        # if you keep models in modules.db_models (only some tables), import what exists
        from modules.db_models import VisitHistoryDB as VisitHistory, ClinicDB as Clinic
        Patient = None  # mark as unavailable

router = APIRouter()


@router.get("/financial-summary")
def financial_summary(db: Session = Depends(get_db),
                      current_user: User = Depends(require_doctor_or_admin)):
    """
    Financial aggregates using ORM queries (MySQL-compatible).
    Requires Billing and Treatment ORM models.
    """
    # totals from billing
    total_q = db.query(
        func.coalesce(func.sum(Billing.amount), 0).label("total_billed"),
        func.coalesce(func.sum(case([(Billing.payment_status == "Paid", Billing.amount)], else_=0)), 0).label("total_paid"),
        func.coalesce(func.sum(case([(Billing.payment_status != "Paid", Billing.amount)], else_=0)), 0).label("outstanding")
    ).one()

    total_billed = float(total_q.total_billed or 0)
    total_paid = float(total_q.total_paid or 0)
    outstanding = float(total_q.outstanding or 0)

    # treatments aggregates
    treat_q = db.query(
        func.coalesce(func.sum(Treatment.cost), 0).label("treatment_cost_total"),
        func.coalesce(func.avg(Treatment.cost), 0).label("avg_treatment_cost")
    ).one()
    treatment_cost_total = float(treat_q.treatment_cost_total or 0)
    avg_treatment_cost = float(treat_q.avg_treatment_cost or 0)

    # monthly revenue (paid) - using function DATE_FORMAT via func (works with MySQL)
    # SQLAlchemy generic approach: use func.date_format
    monthly = db.query(
        func.date_format(Billing.bill_date, "%Y-%m").label("month"),
        func.sum(Billing.amount).label("revenue")
    ).filter(Billing.payment_status == "Paid", Billing.bill_date.isnot(None))\
     .group_by(func.date_format(Billing.bill_date, "%Y-%m"))\
     .order_by(func.date_format(Billing.bill_date, "%Y-%m")).all()

    monthly_revenue = [{"month": m.month, "revenue": float(m.revenue)} for m in monthly]

    return {
        "total_billed": round(total_billed, 2),
        "total_paid": round(total_paid, 2),
        "outstanding": round(outstanding, 2),
        "treatment_cost_total": round(treatment_cost_total, 2),
        "avg_treatment_cost": round(avg_treatment_cost, 2),
        "monthly_revenue": monthly_revenue
    }


@router.get("/operational-summary")
def operational_summary(db: Session = Depends(get_db),
                        current_user: User = Depends(require_doctor_or_admin)):
    """
    Operational metrics from Appointment ORM.
    """
    # status counts
    status_rows = db.query(Appointment.status, func.count(Appointment.appointment_id)).group_by(Appointment.status).all()
    status_counts = {r[0]: int(r[1]) for r in status_rows}
    total_appointments = sum(status_counts.values()) if status_counts else 0
    no_show = status_counts.get("No-show", 0)
    no_show_rate = round((no_show / total_appointments) * 100, 2) if total_appointments > 0 else 0.0

    # top doctors by appointment count
    top_doctors_q = db.query(Appointment.doctor_id, func.count(Appointment.appointment_id).label("cnt"))\
                      .group_by(Appointment.doctor_id).order_by(func.count(Appointment.appointment_id).desc()).limit(10).all()
    top_doctors = [{"doctor_id": r.doctor_id, "appointments": int(r.cnt)} for r in top_doctors_q]

    # monthly visits
    monthly_q = db.query(func.date_format(Appointment.appointment_date, "%Y-%m").label("month"),
                         func.count(Appointment.appointment_id).label("visits"))\
                  .filter(Appointment.appointment_date.isnot(None))\
                  .group_by(func.date_format(Appointment.appointment_date, "%Y-%m"))\
                  .order_by(func.date_format(Appointment.appointment_date, "%Y-%m")).all()
    monthly_visits = [{"month": r.month, "visits": int(r.visits)} for r in monthly_q]

    return {
        "total_appointments": int(total_appointments),
        "status_counts": status_counts,
        "no_show_count": int(no_show),
        "no_show_rate_percent": no_show_rate,
        "top_doctors_by_appointments": top_doctors,
        "monthly_visits": monthly_visits
    }


@router.get("/patient-summary")
def patient_summary(db: Session = Depends(get_db),
                    current_user: User = Depends(require_doctor_or_admin)):
    """
    Patient demographics + visits using ORM models.
    Requires Patient and Appointment ORM models.
    """
    # Age stats: get count, avg, min, max via TIMESTAMPDIFF
    age_stats_q = db.query(
        func.count(Patient.patient_id).label("cnt"),
        func.avg(func.timestampdiff(func.literal_column('YEAR'), Patient.date_of_birth, func.curdate())).label("mean_age"),
        func.min(func.timestampdiff(func.literal_column('YEAR'), Patient.date_of_birth, func.curdate())).label("min_age"),
        func.max(func.timestampdiff(func.literal_column('YEAR'), Patient.date_of_birth, func.curdate())).label("max_age")
    ).filter(Patient.date_of_birth.isnot(None)).one()

    age_stats = {}
    if age_stats_q and age_stats_q.cnt and age_stats_q.cnt > 0:
        # median requires fetching list (MySQL lacks percentile easily)
        ages_rows = db.query(func.timestampdiff(func.literal_column('YEAR'), Patient.date_of_birth, func.curdate()).label("age"))\
                      .filter(Patient.date_of_birth.isnot(None)).order_by("age").all()
        ages = [int(r.age) for r in ages_rows if r.age is not None]
        median = None
        if ages:
            n = len(ages)
            if n % 2 == 1:
                median = float(ages[n//2])
            else:
                median = float((ages[n//2 - 1] + ages[n//2]) / 2.0)
        age_stats = {
            "count": int(age_stats_q.cnt),
            "mean": float(round(age_stats_q.mean_age, 2)) if age_stats_q.mean_age else None,
            "min": int(age_stats_q.min_age) if age_stats_q.min_age is not None else None,
            "max": int(age_stats_q.max_age) if age_stats_q.max_age is not None else None,
            "median": median
        }

    # gender counts
    gender_rows = db.query(Patient.gender, func.count(Patient.patient_id)).group_by(Patient.gender).all()
    gender_counts = {r[0]: int(r[1]) for r in gender_rows}

    # visits by gender (join)
    visits_gender_rows = db.query(Patient.gender, func.count(Appointment.appointment_id).label("visits"))\
                           .join(Appointment, Appointment.patient_id == Patient.patient_id, isouter=True)\
                           .group_by(Patient.gender).all()
    visits_by_gender = {r[0]: int(r[1]) for r in visits_gender_rows}

    # monthly visits by age group: produce buckets via CASE expressions in SQL
    age_group_case = case([
        (func.timestampdiff(func.literal_column('YEAR'), Patient.date_of_birth, func.curdate()).between(0,17), "0-17"),
        (func.timestampdiff(func.literal_column('YEAR'), Patient.date_of_birth, func.curdate()).between(18,30), "18-30"),
        (func.timestampdiff(func.literal_column('YEAR'), Patient.date_of_birth, func.curdate()).between(31,45), "31-45"),
        (func.timestampdiff(func.literal_column('YEAR'), Patient.date_of_birth, func.curdate()).between(46,60), "46-60")
    ], else_="60+")

    subq = db.query(
        func.date_format(Appointment.appointment_date, "%Y-%m").label("month"),
        age_group_case.label("age_group"),
        func.count(Appointment.appointment_id).label("cnt")
    ).join(Patient, Appointment.patient_id == Patient.patient_id, isouter=True)\
     .filter(Appointment.appointment_date.isnot(None), Patient.date_of_birth.isnot(None))\
     .group_by(func.date_format(Appointment.appointment_date, "%Y-%m"), age_group_case).subquery()

    # pivot-like aggregation
    monthly_age_group_rows = db.query(
        subq.c.month,
        func.sum(case([(subq.c.age_group == "0-17", subq.c.cnt)], else_=0)).label("0_17"),
        func.sum(case([(subq.c.age_group == "18-30", subq.c.cnt)], else_=0)).label("18_30"),
        func.sum(case([(subq.c.age_group == "31-45", subq.c.cnt)], else_=0)).label("31_45"),
        func.sum(case([(subq.c.age_group == "46-60", subq.c.cnt)], else_=0)).label("46_60"),
        func.sum(case([(subq.c.age_group == "60+", subq.c.cnt)], else_=0)).label("60_plus")
    ).group_by(subq.c.month).order_by(subq.c.month).all()

    monthly_age_group = []
    for r in monthly_age_group_rows:
        monthly_age_group.append({
            "month": r[0],
            "0-17": int(r[1]),
            "18-30": int(r[2]),
            "31-45": int(r[3]),
            "46-60": int(r[4]),
            "60+": int(r[5])
        })

    return {
        "age_stats": age_stats,
        "gender_counts": gender_counts,
        "visits_by_gender": visits_by_gender,
        "monthly_visits_by_age_group": monthly_age_group
    }
