from database import SessionLocal
from modules.db_models import VisitHistoryDB
from datetime import datetime

db = SessionLocal()

new_visit = VisitHistoryDB(
    queue_id=1,
    patient_id=1,
    patient_name="TEST PASIEN",
    clinic_id=1,
    clinic_name="TEST KLINIK",
    doctor_id=1,
    doctor_name="TEST DOKTER",
    visit_date=datetime.now(),
    reason="Test Visit Insert",
    payment_amount=50000,
    mode_of_payment="cash",
    mode_of_appointment="direct"
)

db.add(new_visit)
db.commit()
db.close()

print("✅ DATA VISIT BERHASIL DITAMBAHKAN")
