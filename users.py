import uuid
import hashlib
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from modules.schema.schemas import User, UserRole
from modules.db_models import UserDB
from database import SessionLocal


# Cache ringan supaya kode lama yang mungkin masih baca users_db nggak langsung rusak.
# Tapi sumber data utama sekarang ada di MySQL (tabel users).
users_db: Dict[str, User] = {}
sessions_db: Dict[str, Dict] = {}


def hash_password(password: str) -> str:
    """Hash password dengan SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_session_token() -> str:
    """Generate token sesi acak."""
    return str(uuid.uuid4())


def _to_schema(db_obj: UserDB) -> User:
    """Konversi UserDB (SQLAlchemy) -> User (Pydantic)."""
    return User(
        id=db_obj.id,
        name=db_obj.name,
        email=db_obj.email,
        phone=db_obj.phone,
        role=UserRole(db_obj.role),
        medical_record_number=db_obj.medical_record_number,
        created_at=db_obj.created_at.isoformat() if db_obj.created_at else datetime.now().isoformat(),
    )


def create_user(
    name: str,
    email: str,
    password: str,
    phone: str,
    role: UserRole = UserRole.PATIENT,
) -> User:
    """Buat user baru dan simpan ke MySQL."""
    db: Session = SessionLocal()
    try:
        # Cek email sudah dipakai atau belum
        existing = db.query(UserDB).filter(UserDB.email == email).first()
        if existing:
            raise ValueError("Email sudah terdaftar")

        user_id = str(uuid.uuid4())

        # Generate medical record kalau role = PATIENT
        medical_record_number = None
        if role == UserRole.PATIENT:
            patient_count = (
                db.query(UserDB)
                .filter(UserDB.role == UserRole.PATIENT.value)
                .count()
            )
            medical_record_number = f"MR{patient_count + 1:06d}"

        db_user = UserDB(
            id=user_id,
            name=name,
            email=email,
            phone=phone,
            role=role.value,
            medical_record_number=medical_record_number,
            password_hash=hash_password(password),
            created_at=datetime.now(),
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        user_schema = _to_schema(db_user)
        users_db[user_schema.id] = user_schema  # sync ringan ke cache
        return user_schema
    finally:
        db.close()


def read_user(user_id: str) -> Optional[User]:
    """Ambil user dari MySQL berdasarkan id."""
    db: Session = SessionLocal()
    try:
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not db_user:
            return None
        user_schema = _to_schema(db_user)
        users_db[user_schema.id] = user_schema
        return user_schema
    finally:
        db.close()


def read_user_by_email(email: str) -> Optional[User]:
    """Ambil user dari MySQL berdasarkan email."""
    db: Session = SessionLocal()
    try:
        db_user = db.query(UserDB).filter(UserDB.email == email).first()
        if not db_user:
            return None
        user_schema = _to_schema(db_user)
        users_db[user_schema.id] = user_schema
        return user_schema
    finally:
        db.close()


def read_all_users(role: Optional[UserRole] = None) -> List[User]:
    """Ambil semua user, bisa difilter berdasarkan role."""
    db: Session = SessionLocal()
    try:
        q = db.query(UserDB)
        if role is not None:
            q = q.filter(UserDB.role == role.value)

        db_users = q.all()
        users: List[User] = []
        users_db.clear()

        for u in db_users:
            user_schema = _to_schema(u)
            users.append(user_schema)
            users_db[user_schema.id] = user_schema

        return users
    finally:
        db.close()


def update_user(user_id: str, **kwargs) -> Optional[User]:
    """Update data user di MySQL."""
    db: Session = SessionLocal()
    try:
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not db_user:
            return None

        # field yang boleh di-update
        allowed_fields = {"name", "phone", "role", "medical_record_number"}

        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                if key == "role" and isinstance(value, UserRole):
                    setattr(db_user, key, value.value)
                else:
                    setattr(db_user, key, value)

        db.commit()
        db.refresh(db_user)

        user_schema = _to_schema(db_user)
        users_db[user_schema.id] = user_schema
        return user_schema
    finally:
        db.close()


def delete_user(user_id: str) -> bool:
    """Hapus user dari MySQL."""
    db: Session = SessionLocal()
    try:
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not db_user:
            return False

        db.delete(db_user)
        db.commit()

        if user_id in users_db:
            del users_db[user_id]

        # kalau ada session yang pakai user ini, bisa dibersihkan di sini kalau mau
        return True
    finally:
        db.close()


def verify_password(user_id: str, password: str) -> bool:
    """Cek password user terhadap hash di database."""
    db: Session = SessionLocal()
    try:
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not db_user:
            return False
        return db_user.password_hash == hash_password(password)
    finally:
        db.close()


def create_session(user_id: str) -> tuple[str, datetime]:
    """Buat session token di memory (RAM)."""
    session_token = generate_session_token()
    expires_at = datetime.now() + timedelta(hours=24)

    sessions_db[session_token] = {
        "user_id": user_id,
        "expires_at": expires_at,
    }

    return session_token, expires_at


def verify_session(session_token: str) -> Optional[User]:
    """Verifikasi session token, lalu ambil user dari DB."""
    if session_token not in sessions_db:
        return None

    session = sessions_db[session_token]

    if datetime.now() > session["expires_at"]:
        del sessions_db[session_token]
        return None

    return read_user(session["user_id"])


def delete_session(session_token: str) -> bool:
    """Hapus session dari memory."""
    if session_token in sessions_db:
        del sessions_db[session_token]
        return True
    return False
