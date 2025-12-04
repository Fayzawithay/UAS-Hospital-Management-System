from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from modules.schema.schemas import (
    QueueRegisterRequest,
    QueueStatus,
    User,
    UserRole,
    CompleteQueueRequest,
)
from modules.items import queues as queue_crud
from modules.items import visits as visit_crud
from modules.routes.auth import get_current_user, require_doctor_or_admin

router = APIRouter()


@router.post("/register", status_code=201)
async def register_queue(
    data: QueueRegisterRequest,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=403,
            detail="Hanya pasien yang dapat mendaftar antrean",
        )

    try:
        queue = queue_crud.create_queue(
            patient_id=current_user.id,
            patient_name=current_user.name,
            clinic_id=data.clinic_id,
            doctor_id=data.doctor_id,
        )

        position = queue_crud.get_queue_position(queue.id)

        return {
            "message": "Pendaftaran antrean berhasil",
            "queue": queue,
            "position": position,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def get_all_queues(
    clinic_id: Optional[str] = None,
    status: Optional[QueueStatus] = None,
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.PATIENT:
        queues = queue_crud.read_all_queues(
            patient_id=current_user.id,
            status=status,
        )
    else:
        queues = queue_crud.read_all_queues(
            clinic_id=clinic_id,
            status=status,
        )

    return {"queues": queues, "total": len(queues)}


@router.get("/my-position")
async def get_my_position(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=403, detail="Endpoint ini hanya untuk pasien"
        )

    user_queues = queue_crud.read_all_queues(
        patient_id=current_user.id,
        status=QueueStatus.WAITING,
    )

    if not user_queues:
        return {"message": "Tidak ada antrean aktif", "position": None}

    queue = user_queues[0]
    position = queue_crud.get_queue_position(queue.id)

    all_waiting = queue_crud.read_all_queues(
        clinic_id=queue.clinic_id,
        status=QueueStatus.WAITING,
    )

    return {
        "queue": queue,
        "position": position,
        "total_waiting": len(all_waiting),
        "estimated_wait_minutes": position * 15,
    }


@router.get("/{queue_id}")
async def get_queue(
    queue_id: str,
    current_user: User = Depends(get_current_user),
):
    queue = queue_crud.read_queue(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Antrean tidak ditemukan")

    if current_user.role == UserRole.PATIENT and queue.patient_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Tidak memiliki akses ke antrean ini"
        )

    return {"queue": queue}


@router.patch("/{queue_id}/call")
async def call_queue(
    queue_id: str,
    current_user: User = Depends(require_doctor_or_admin),
):
    queue = queue_crud.read_queue(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Antrean tidak ditemukan")

    if queue.status != QueueStatus.WAITING:
        raise HTTPException(
            status_code=400, detail="Antrean tidak dalam status menunggu"
        )

    updated_queue = queue_crud.update_queue_status(
        queue_id,
        QueueStatus.IN_SERVICE,
    )
    return {"message": "Pasien berhasil dipanggil", "queue": updated_queue}


# =============== COMPLETE QUEUE – BODY ALA KAGGLE ===============
@router.patch("/{queue_id}/complete")
async def complete_queue(
    queue_id: str,
    data: CompleteQueueRequest,
    current_user: User = Depends(require_doctor_or_admin),
):
    queue = queue_crud.read_queue(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Antrean tidak ditemukan")

    if queue.status not in [QueueStatus.IN_SERVICE, QueueStatus.WAITING]:
        raise HTTPException(
            status_code=400, detail="Antrean tidak dapat diselesaikan"
        )

    # update status antrean menjadi selesai
    updated_queue = queue_crud.update_queue_status(
        queue_id,
        QueueStatus.COMPLETED,
    )

    # buat riwayat kunjungan dengan field mirip Kaggle
    visit = visit_crud.create_visit(
        queue_id=queue_id,
        patient_id=queue.patient_id,
        patient_name=queue.patient_name,
        clinic_id=queue.clinic_id,
        clinic_name=queue.clinic_name,
        doctor_id=queue.doctor_id or current_user.id,
        doctor_name=queue.doctor_name or current_user.name,
        reason=data.reason,
        payment_amount=data.payment_amount,
        mode_of_payment=data.mode_of_payment,
        mode_of_appointment=data.mode_of_appointment,
    )

    return {
        "message": "Pelayanan berhasil diselesaikan",
        "queue": updated_queue,
        "visit_history": visit,
    }


@router.patch("/{queue_id}/cancel")
async def cancel_queue(
    queue_id: str,
    current_user: User = Depends(get_current_user),
):
    queue = queue_crud.read_queue(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Antrean tidak ditemukan")

    if current_user.role == UserRole.PATIENT and queue.patient_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Tidak memiliki akses ke antrean ini"
        )

    if queue.status != QueueStatus.WAITING:
        raise HTTPException(
            status_code=400,
            detail="Hanya antrean menunggu yang dapat dibatalkan",
        )

    updated_queue = queue_crud.update_queue_status(
        queue_id,
        QueueStatus.CANCELLED,
    )
    return {"message": "Antrean berhasil dibatalkan", "queue": updated_queue}
