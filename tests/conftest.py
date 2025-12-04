import pytest
from fastapi.testclient import TestClient
from main import app
from modules.items import users, clinics, doctors, queues, visits

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_all_data():
    users.users_db.clear()
    users.passwords_db.clear()
    users.sessions_db.clear()
    clinics.clinics_db.clear()
    doctors.doctors_db.clear()
    queues.queues_db.clear()
    queues.queue_counters.clear()
    visits.visits_db.clear()
    
    yield
    
    users.users_db.clear()
    users.passwords_db.clear()
    users.sessions_db.clear()
    clinics.clinics_db.clear()
    doctors.doctors_db.clear()
    queues.queues_db.clear()
    queues.queue_counters.clear()
    visits.visits_db.clear()


@pytest.fixture
def client():
    return TestClient(app)