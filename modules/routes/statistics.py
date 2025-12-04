from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, date
from modules.schema.schemas import User, QueueStatus
from modules.items.queues import queues_db
from modules.items.clinics import clinics_db
from modules.items.visits import visits_db
from modules.routes.auth import require_doctor_or_admin

router = APIRouter()


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