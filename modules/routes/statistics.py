# modules/routes/statistics.py

from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from dependency import get_db
from modules.routes.auth import require_doctor_or_admin
from modules.schema.schemas import User  # current_user schema (Pydantic)

from modules.db_models import (
    UserDB,
    DoctorDB,
    ClinicDB,
    QueueDB,
    VisitHistoryDB,
)

router = APIRouter(prefix="/statistics", tags=["Statistics"])


# ===================== HELPER =====================

def _parse_iso(dt_str: Optional[str]) -> Optional[datetime]:
    """
    Parse string ISO (misal dari datetime.isoformat()) menjadi datetime.
    Kalau gagal / None / kosong, return None.
    """
    if not dt_str:
        return None
    dt_str = dt_str.strip()
    if not dt_str:
        return None
    try:
        # contoh: "2025-12-10T13:45:00.123456" atau "2025-12-10T13:45:00"
        return datetime.fromisoformat(dt_str)
    except Exception:
        # handle yang pakai 'Z' di belakang: "2025-12-10T13:45:00Z"
        if dt_str.endswith("Z"):
            try:
                return datetime.fromisoformat(dt_str[:-1])
            except Exception:
                return None
        return None


def _month_key_from_string(date_str: Optional[str]) -> Optional[str]:
    """
    Ambil key bulan "YYYY-MM" dari string tanggal (visit_date) yang disimpan sebagai ISO string.
    Kalau format aneh, return None.
    """
    if not date_str:
        return None
    date_str = date_str.strip()
    if len(date_str) < 7:
        return None
    # asumsi format mulai dengan "YYYY-MM-..."
    return date_str[:7]


# ===================== 1. FINANCIAL SUMMARY =====================

@router.get("/financial-summary")
def financial_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    """
    Ringkasan finansial berbasis tabel visits (VisitHistoryDB).

    Kolom yang dipakai:
      - payment_amount (Float)
      - mode_of_payment (string: 'Cash', 'BPJS', 'Insurance', dll)
      - visit_date (string ISO, kita ambil "YYYY-MM" untuk per-bulan)
    """

    # total uang & jumlah visit
    total_q = db.query(
        func.coalesce(func.sum(VisitHistoryDB.payment_amount), 0).label("total_amount"),
        func.count(VisitHistoryDB.id).label("total_visits"),
    ).one()

    total_amount = float(total_q.total_amount or 0)
    total_visits = int(total_q.total_visits or 0)

    # revenue per mode_of_payment
    by_payment_rows = (
        db.query(
            VisitHistoryDB.mode_of_payment,
            func.coalesce(func.sum(VisitHistoryDB.payment_amount), 0).label("total"),
            func.count(VisitHistoryDB.id).label("count"),
        )
        .group_by(VisitHistoryDB.mode_of_payment)
        .all()
    )

    revenue_by_payment_mode: List[Dict[str, Any]] = []
    for r in by_payment_rows:
        revenue_by_payment_mode.append(
            {
                "mode_of_payment": r.mode_of_payment or "Unknown",
                "total_amount": float(r.total or 0),
                "visit_count": int(r.count or 0),
            }
        )

    # revenue per mode_of_appointment
    by_appointment_rows = (
        db.query(
            VisitHistoryDB.mode_of_appointment,
            func.coalesce(func.sum(VisitHistoryDB.payment_amount), 0).label("total"),
            func.count(VisitHistoryDB.id).label("count"),
        )
        .group_by(VisitHistoryDB.mode_of_appointment)
        .all()
    )

    revenue_by_appointment_mode: List[Dict[str, Any]] = []
    for r in by_appointment_rows:
        revenue_by_appointment_mode.append(
            {
                "mode_of_appointment": r.mode_of_appointment or "Unknown",
                "total_amount": float(r.total or 0),
                "visit_count": int(r.count or 0),
            }
        )

    # monthly revenue (kita hitung di Python karena visit_date = String)
    visits = db.query(VisitHistoryDB.visit_date, VisitHistoryDB.payment_amount).all()

    monthly_map: Dict[str, Dict[str, Any]] = {}
    for v_date, amount in visits:
        month_key = _month_key_from_string(v_date)
        if not month_key:
            continue
        if month_key not in monthly_map:
            monthly_map[month_key] = {"revenue": 0.0, "visit_count": 0}
        monthly_map[month_key]["revenue"] += float(amount or 0)
        monthly_map[month_key]["visit_count"] += 1

    monthly_revenue = [
        {
            "month": m,
            "revenue": round(data["revenue"], 2),
            "visit_count": data["visit_count"],
        }
        for m, data in sorted(monthly_map.items())
    ]

    return {
        "total_amount": round(total_amount, 2),
        "total_visits": total_visits,
        "revenue_by_payment_mode": revenue_by_payment_mode,
        "revenue_by_appointment_mode": revenue_by_appointment_mode,
        "monthly_revenue": monthly_revenue,
    }


# ===================== 2. OPERATIONAL SUMMARY =====================

@router.get("/operational-summary")
def operational_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    """
    Ringkasan operasional dari:
      - QueueDB (antrian)
      - VisitHistoryDB (riwayat kunjungan)
    """

    # ---- Status antrian ----
    status_rows = (
        db.query(QueueDB.status, func.count(QueueDB.id))
        .group_by(QueueDB.status)
        .all()
    )
    status_counts: Dict[str, int] = {
        (row[0] or "Unknown"): int(row[1]) for row in status_rows
    }

    total_queues = sum(status_counts.values())
    # di db_models: status: "menunggu", "sedang_dilayani", "selesai", "dibatalkan"
    completed = status_counts.get("selesai", 0)

    # misal kamu anggap "No-show" = dibatalkan:
    no_show = status_counts.get("dibatalkan", 0)
    no_show_rate = round((no_show / total_queues) * 100, 2) if total_queues > 0 else 0.0

    # ---- Waktu tunggu & durasi pelayanan (dihitung di Python) ----
    queues = db.query(
        QueueDB.registration_time,
        QueueDB.called_time,
        QueueDB.service_start_time,
        QueueDB.service_end_time,
    ).all()

    wait_seconds_list: List[float] = []
    service_seconds_list: List[float] = []

    for reg_str, called_str, start_str, end_str in queues:
        reg = _parse_iso(reg_str)
        start = _parse_iso(start_str)
        end = _parse_iso(end_str)

        # waktu tunggu: dari registration ke service_start
        if reg and start and start >= reg:
            wait_seconds_list.append((start - reg).total_seconds())

        # durasi pelayanan: dari service_start ke service_end
        if start and end and end >= start:
            service_seconds_list.append((end - start).total_seconds())

    def _summary_seconds_to_minutes(values: List[float]) -> Dict[str, Optional[float]]:
        if not values:
            return {"avg": None, "min": None, "max": None}
        avg_sec = sum(values) / len(values)
        return {
            "avg": round(avg_sec / 60.0, 2),
            "min": round(min(values) / 60.0, 2),
            "max": round(max(values) / 60.0, 2),
        }

    wait_summary = _summary_seconds_to_minutes(wait_seconds_list)
    service_summary = _summary_seconds_to_minutes(service_seconds_list)

    # ---- Monthly visits (dari VisitHistoryDB.visit_date) ----
    visits_dates = db.query(VisitHistoryDB.visit_date).all()
    monthly_visits_map: Dict[str, int] = {}
    for (v_date,) in visits_dates:
        month_key = _month_key_from_string(v_date)
        if not month_key:
            continue
        monthly_visits_map[month_key] = monthly_visits_map.get(month_key, 0) + 1

    monthly_visits = [
        {"month": m, "visits": cnt}
        for m, cnt in sorted(monthly_visits_map.items())
    ]

    # ---- Top dokter berdasarkan jumlah visit ----
    top_doctors_q = (
        db.query(
            VisitHistoryDB.doctor_id,
            VisitHistoryDB.doctor_name,
            func.count(VisitHistoryDB.id).label("visit_count"),
        )
        .group_by(VisitHistoryDB.doctor_id, VisitHistoryDB.doctor_name)
        .order_by(func.count(VisitHistoryDB.id).desc())
        .limit(10)
        .all()
    )

    top_doctors = [
        {
            "doctor_id": r.doctor_id,
            "doctor_name": r.doctor_name,
            "visit_count": int(r.visit_count or 0),
        }
        for r in top_doctors_q
    ]

    return {
        "total_queues": int(total_queues),
        "status_counts": status_counts,
        "completed_queues": int(completed),
        "no_show_count": int(no_show),
        "no_show_rate_percent": no_show_rate,
        "wait_time_minutes": wait_summary,      # {avg, min, max}
        "service_time_minutes": service_summary,  # {avg, min, max}
        "monthly_visits": monthly_visits,
        "top_doctors_by_visits": top_doctors,
    }


# ===================== 3. PATIENT / VISITS SUMMARY =====================

@router.get("/patient-summary")
def patient_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    """
    Ringkasan pasien & pola kunjungan, berbasis VisitHistoryDB.

    Karena UserDB tidak punya DOB / gender, fokus ke:
      - jumlah pasien unik (distinct patient_id di visits)
      - top pasien berdasarkan frekuensi visit
      - distribusi mode_of_appointment
      - distribusi visit per klinik
      - distribusi visit per dokter
    """

    # ---- total pasien unik yang pernah visit ----
    total_patients = (
        db.query(func.count(func.distinct(VisitHistoryDB.patient_id))).scalar() or 0
    )

    # ---- top pasien by visit_count ----
    top_patients_q = (
        db.query(
            VisitHistoryDB.patient_id,
            VisitHistoryDB.patient_name,
            func.count(VisitHistoryDB.id).label("visit_count"),
        )
        .group_by(VisitHistoryDB.patient_id, VisitHistoryDB.patient_name)
        .order_by(func.count(VisitHistoryDB.id).desc())
        .limit(10)
        .all()
    )

    top_patients = [
        {
            "patient_id": r.patient_id,
            "patient_name": r.patient_name,
            "visit_count": int(r.visit_count or 0),
        }
        for r in top_patients_q
    ]

    # ---- visits per mode_of_appointment ----
    mode_rows = (
        db.query(
            VisitHistoryDB.mode_of_appointment,
            func.count(VisitHistoryDB.id).label("visit_count"),
        )
        .group_by(VisitHistoryDB.mode_of_appointment)
        .all()
    )

    visits_by_mode_of_appointment = [
        {
            "mode_of_appointment": r.mode_of_appointment or "Unknown",
            "visit_count": int(r.visit_count or 0),
        }
        for r in mode_rows
    ]

    # ---- visits per klinik ----
    clinic_rows = (
        db.query(
            VisitHistoryDB.clinic_id,
            VisitHistoryDB.clinic_name,
            func.count(VisitHistoryDB.id).label("visit_count"),
        )
        .group_by(VisitHistoryDB.clinic_id, VisitHistoryDB.clinic_name)
        .all()
    )

    visits_by_clinic = [
        {
            "clinic_id": r.clinic_id,
            "clinic_name": r.clinic_name,
            "visit_count": int(r.visit_count or 0),
        }
        for r in clinic_rows
    ]

    # ---- visits per dokter ----
    doctor_rows = (
        db.query(
            VisitHistoryDB.doctor_id,
            VisitHistoryDB.doctor_name,
            func.count(VisitHistoryDB.id).label("visit_count"),
        )
        .group_by(VisitHistoryDB.doctor_id, VisitHistoryDB.doctor_name)
        .all()
    )

    visits_by_doctor = [
        {
            "doctor_id": r.doctor_id,
            "doctor_name": r.doctor_name,
            "visit_count": int(r.visit_count or 0),
        }
        for r in doctor_rows
    ]

    return {
        "total_patients": int(total_patients),
        "top_patients_by_visits": top_patients,
        "visits_by_mode_of_appointment": visits_by_mode_of_appointment,
        "visits_by_clinic": visits_by_clinic,
        "visits_by_doctor": visits_by_doctor,
    }
