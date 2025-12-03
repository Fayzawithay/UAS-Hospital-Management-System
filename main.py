from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from modules.routes import auth, clinics, doctors, queues, visits, statistics
from modules.items.users import users_db
from modules.items.clinics import clinics_db
from modules.items.doctors import doctors_db
from modules.items.queues import queues_db


app = FastAPI(
    title="Hospital Queue Management System",
    description="API for hospital queue management system",
    version="1.2.3",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============== JINJA TEMPLATE SETUP ===============
# Pastikan folder "templates" ada di root project
templates = Jinja2Templates(directory="templates")

# =============== ROUTERS API =======================
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(clinics.router, prefix="/api/clinics", tags=["Clinics"])
app.include_router(doctors.router, prefix="/api/doctors", tags=["Doctors"])
app.include_router(queues.router, prefix="/api/queues", tags=["Queue Management"])
app.include_router(visits.router, prefix="/api/visit-history", tags=["Visit History"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["Statistics"])


# =============== ROOT INFO API (JSON) ==============
@app.get("/", tags=["System"])
async def root():
    """Info singkat API (JSON), cocok buat laporan / cek cepat."""
    return {
        "message": "Hospital Queue Management System API",
        "version": "1.2.3",
        "status": "running",
        "documentation": "/docs",
        "demo_page": "/demo-visit",
    }


# =============== HALAMAN DEMO HTML =================
@app.get("/demo-visit", response_class=HTMLResponse, tags=["Demo"])
async def demo_visit(request: Request):
    """
    Halaman web demo kunjungan pasien.
    Menggunakan templates/index.html
    """
    return templates.TemplateResponse("index.html", {"request": request})


# =============== HEALTH CHECK ======================
@app.get("/health", tags=["System"])
async def health_check():
    from modules.schema.schemas import QueueStatus

    active_queues = len(
        [
            q
            for q in queues_db.values()
            if q.status in [QueueStatus.WAITING, QueueStatus.IN_SERVICE]
        ]
    )

    return {
        "status": "healthy",
        "storage_type": "In-Memory",
        "statistics": {
            "total_users": len(users_db),
            "total_clinics": len(clinics_db),
            "total_doctors": len(doctors_db),
            "active_queues": active_queues,
            "total_queues": len(queues_db),
        },
    }
    