from database import Base, engine
from modules.db_models import ClinicDB, UserDB, DoctorDB, QueueDB, VisitHistoryDB

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created!")
