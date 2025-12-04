from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from modules.routes import auth, clinics, doctors, queues, visits, statistics
from modules.config.database import Base, engine, SessionLocal


# =================================================
# FASTAPI APP
# =================================================
app = FastAPI(
    title="Hospital Queue Management System",
    version="1.2.3",
    docs_url="/docs",
    redoc_url="/redoc"
)

# =================================================
# DATABASE INIT
# =================================================
# create all tables
Base.metadata.create_all(bind=engine)

# DB session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =================================================
# JINJA TEMPLATE SETUP
# =================================================
templates = Jinja2Templates(directory="templates")


# =================================================
# ROUTERS
# =================================================
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(clinics.router, prefix="/api/clinics", tags=["Clinics"])
app.include_router(doctors.router, prefix="/api/doctors", tags=["Doctors"])
app.include_router(queues.router, prefix="/api/queues", tags=["Queues"])
app.include_router(visits.router, prefix="/api/visit-history", tags=["Visit History"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["Statistics"])


# =================================================
# ROOT PAGE
# =================================================
@app.get("/")
async def root():
    return {
        "message": "Hospital Queue Management System API",
        "version": "1.2.3",
        "status": "running",
        "docs": "/docs"
    }


# =================================================
# DEMO HTML
# =================================================
@app.get("/demo-visit", response_class=HTMLResponse)
async def demo_visit(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
