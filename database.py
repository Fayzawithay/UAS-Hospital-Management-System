# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Tanpa password
DATABASE_URL = "mysql+pymysql://root:@localhost/myhospital"
# kalau MySQL pakai password:
# DATABASE_URL = "mysql+pymysql://root:PASSWORD@localhost:3306/hospital_app"

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()