# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = "mysql+pymysql://root:Zxcvbn123432@localhost:3306/myhospital_new"
# kalau MySQL pakai password:
# DATABASE_URL = "mysql+pymysql://root:PASSWORD@localhost:3306/myhospital_new"

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# deps.py

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
