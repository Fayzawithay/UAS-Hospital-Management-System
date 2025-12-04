
class TestSystem:
    
    def test_root_endpoint(self, client):
        
        response = client.get("/")
        assert response.status_code == 200
        assert "Hospital Queue Management System API" in response.json()["message"]
    
    def test_health_check(self, client):
        
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuthentication:
    
    def test_register_patient_success(self, client):
        
        response = client.post("/api/auth/register", json={
            "name": "Test Patient",
            "email": "patient@test.com",
            "password": "password123",
            "phone": "08123456789",
            "role": "patient"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Registrasi berhasil"
        assert data["user"]["role"] == "patient"
        assert data["user"]["medical_record_number"] is not None
    
    def test_login_success(self, client):
        
        client.post("/api/auth/register", json={
            "name": "Test User",
            "email": "user@test.com",
            "password": "password123",
            "phone": "08123456789",
            "role": "patient"
        })
        
        response = client.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "session_token" in data
        assert data["user"]["email"] == "user@test.com"
    
    def test_login_wrong_password(self, client):
        
        client.post("/api/auth/register", json={
            "name": "Test User",
            "email": "user@test.com",
            "password": "password123",
            "phone": "08123456789",
            "role": "patient"
        })
        
        response = client.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401


class TestClinics:
    
    def test_create_clinic(self, client):
        
        client.post("/api/auth/register", json={
            "name": "Admin", "email": "admin@test.com",
            "password": "admin123", "phone": "08123456789", "role": "admin"
        })
        token = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }).json()["session_token"]
        
        response = client.post(
            "/api/clinics",
            headers={"X-Session-Token": token},
            json={"name": "Klinik Umum", "description": "Klinik untuk pemeriksaan umum"}
        )
        
        assert response.status_code == 201
        assert response.json()["clinic"]["name"] == "Klinik Umum"
    
    def test_get_all_clinics(self, client):

        response = client.get("/api/clinics")
        
        assert response.status_code == 200
        assert "clinics" in response.json()
        assert "total" in response.json()
    
    def test_update_clinic(self, client):

        client.post("/api/auth/register", json={
            "name": "Admin", "email": "admin@test.com",
            "password": "admin123", "phone": "08123456789", "role": "admin"
        })
        token = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }).json()["session_token"]
        
        clinic = client.post(
            "/api/clinics",
            headers={"X-Session-Token": token},
            json={"name": "Klinik Test"}
        ).json()["clinic"]
        
        response = client.put(
            f"/api/clinics/{clinic['id']}",
            headers={"X-Session-Token": token},
            json={"name": "Klinik Updated"}
        )
        
        assert response.status_code == 200
        assert response.json()["clinic"]["name"] == "Klinik Updated"
    
    def test_delete_clinic(self, client):
        
        client.post("/api/auth/register", json={
            "name": "Admin", "email": "admin@test.com",
            "password": "admin123", "phone": "08123456789", "role": "admin"
        })
        token = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }).json()["session_token"]
        
        clinic = client.post(
            "/api/clinics",
            headers={"X-Session-Token": token},
            json={"name": "Klinik Test"}
        ).json()["clinic"]
        
        response = client.delete(
            f"/api/clinics/{clinic['id']}",
            headers={"X-Session-Token": token}
        )
        
        assert response.status_code == 200
        assert "berhasil dihapus" in response.json()["message"]


class TestDoctors:
    
    def test_create_doctor(self, client):
        client.post("/api/auth/register", json={
            "name": "Admin", "email": "admin@test.com",
            "password": "admin123", "phone": "08123456789", "role": "admin"
        })
        token = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }).json()["session_token"]
        
        clinic = client.post(
            "/api/clinics",
            headers={"X-Session-Token": token},
            json={"name": "Klinik Test"}
        ).json()["clinic"]
        
        response = client.post(
            "/api/doctors",
            headers={"X-Session-Token": token},
            json={
                "name": "Dr. Ahmad",
                "specialization": "Dokter Umum",
                "clinic_id": clinic["id"],
                "phone": "08123456789"
            }
        )
        
        assert response.status_code == 201
        assert response.json()["doctor"]["name"] == "Dr. Ahmad"
    
    def test_get_all_doctors(self, client):
        response = client.get("/api/doctors")
        
        assert response.status_code == 200
        assert "doctors" in response.json()
    
    def test_update_doctor(self, client):
        client.post("/api/auth/register", json={
            "name": "Admin", "email": "admin@test.com",
            "password": "admin123", "phone": "08123456789", "role": "admin"
        })
        token = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }).json()["session_token"]
        
        clinic = client.post(
            "/api/clinics",
            headers={"X-Session-Token": token},
            json={"name": "Klinik Test"}
        ).json()["clinic"]
        
        doctor = client.post(
            "/api/doctors",
            headers={"X-Session-Token": token},
            json={
                "name": "Dr. Test",
                "specialization": "Dokter Umum",
                "clinic_id": clinic["id"],
                "phone": "08123456789"
            }
        ).json()["doctor"]
        
        response = client.put(
            f"/api/doctors/{doctor['id']}",
            headers={"X-Session-Token": token},
            json={"name": "Dr. Updated"}
        )
        
        assert response.status_code == 200
        assert response.json()["doctor"]["name"] == "Dr. Updated"
    
    def test_delete_doctor(self, client):
    
        client.post("/api/auth/register", json={
            "name": "Admin", "email": "admin@test.com",
            "password": "admin123", "phone": "08123456789", "role": "admin"
        })
        token = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }).json()["session_token"]
        
        clinic = client.post(
            "/api/clinics",
            headers={"X-Session-Token": token},
            json={"name": "Klinik Test"}
        ).json()["clinic"]
        
        doctor = client.post(
            "/api/doctors",
            headers={"X-Session-Token": token},
            json={
                "name": "Dr. Test",
                "specialization": "Dokter Umum",
                "clinic_id": clinic["id"],
                "phone": "08123456789"
            }
        ).json()["doctor"]
        
        response = client.delete(
            f"/api/doctors/{doctor['id']}",
            headers={"X-Session-Token": token}
        )
        
        assert response.status_code == 200


class TestQueueManagement:
    
    def test_patient_register_queue(self, client):
        client.post("/api/auth/register", json={
            "name": "Admin", "email": "admin@test.com",
            "password": "admin123", "phone": "08123456789", "role": "admin"
        })
        admin_token = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }).json()["session_token"]
        
        clinic = client.post(
            "/api/clinics",
            headers={"X-Session-Token": admin_token},
            json={"name": "Klinik Test"}
        ).json()["clinic"]
        
        client.post("/api/auth/register", json={
            "name": "Patient", "email": "patient@test.com",
            "password": "patient123", "phone": "08123456790", "role": "patient"
        })
        patient_token = client.post("/api/auth/login", json={
            "email": "patient@test.com", "password": "patient123"
        }).json()["session_token"]
        
        response = client.post(
            "/api/queues/register",
            headers={"X-Session-Token": patient_token},
            json={"clinic_id": clinic["id"]}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["queue"]["status"] == "menunggu"
        assert "queue_number" in data["queue"]
    
    def test_complete_queue_flow(self, client):
        
        client.post("/api/auth/register", json={
            "name": "Admin", "email": "admin@test.com",
            "password": "admin123", "phone": "08123456789", "role": "admin"
        })
        admin_token = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }).json()["session_token"]
        
        clinic = client.post(
            "/api/clinics",
            headers={"X-Session-Token": admin_token},
            json={"name": "Klinik Test"}
        ).json()["clinic"]
        
        client.post("/api/auth/register", json={
            "name": "Patient", "email": "patient@test.com",
            "password": "patient123", "phone": "08123456790", "role": "patient"
        })
        patient_token = client.post("/api/auth/login", json={
            "email": "patient@test.com", "password": "patient123"
        }).json()["session_token"]
        
        client.post("/api/auth/register", json={
            "name": "Doctor", "email": "doctor@test.com",
            "password": "doctor123", "phone": "08123456791", "role": "doctor"
        })
        doctor_token = client.post("/api/auth/login", json={
            "email": "doctor@test.com", "password": "doctor123"
        }).json()["session_token"]
        
        queue_response = client.post(
            "/api/queues/register",
            headers={"X-Session-Token": patient_token},
            json={"clinic_id": clinic["id"]}
        )
        queue = queue_response.json()["queue"]
        assert queue["status"] == "menunggu"
        
        call_response = client.patch(
            f"/api/queues/{queue['id']}/call",
            headers={"X-Session-Token": doctor_token}
        )
        assert call_response.status_code == 200
        assert call_response.json()["queue"]["status"] == "sedang_dilayani"
        
        complete_response = client.patch(
            f"/api/queues/{queue['id']}/complete?diagnosis=Flu&treatment=Paracetamol",
            headers={"X-Session-Token": doctor_token}
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["queue"]["status"] == "selesai"
        assert "visit_history" in complete_response.json()

class TestVisitHistory:
    
    def test_visit_history_auto_created(self, client):
        client.post("/api/auth/register", json={
            "name": "Admin", "email": "admin@test.com",
            "password": "admin123", "phone": "08123456789", "role": "admin"
        })
        admin_token = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }).json()["session_token"]
        
        clinic = client.post(
            "/api/clinics",
            headers={"X-Session-Token": admin_token},
            json={"name": "Klinik Test"}
        ).json()["clinic"]
        
        client.post("/api/auth/register", json={
            "name": "Patient", "email": "patient@test.com",
            "password": "patient123", "phone": "08123456790", "role": "patient"
        })
        patient_token = client.post("/api/auth/login", json={
            "email": "patient@test.com", "password": "patient123"
        }).json()["session_token"]
        
        client.post("/api/auth/register", json={
            "name": "Doctor", "email": "doctor@test.com",
            "password": "doctor123", "phone": "08123456791", "role": "doctor"
        })
        doctor_token = client.post("/api/auth/login", json={
            "email": "doctor@test.com", "password": "doctor123"
        }).json()["session_token"]
        
        queue = client.post(
            "/api/queues/register",
            headers={"X-Session-Token": patient_token},
            json={"clinic_id": clinic["id"]}
        ).json()["queue"]
        
        client.patch(
            f"/api/queues/{queue['id']}/call",
            headers={"X-Session-Token": doctor_token}
        )
        
        client.patch(
            f"/api/queues/{queue['id']}/complete?diagnosis=Flu&treatment=Istirahat",
            headers={"X-Session-Token": doctor_token}
        )
        
        response = client.get(
            "/api/visit-history",
            headers={"X-Session-Token": patient_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["visit_history"][0]["diagnosis"] == "Flu"


class TestStatistics:
    
    def test_queue_summary(self, client):
        client.post("/api/auth/register", json={
            "name": "Admin", "email": "admin@test.com",
            "password": "admin123", "phone": "08123456789", "role": "admin"
        })
        admin_token = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "admin123"
        }).json()["session_token"]
        
        response = client.get(
            "/api/statistics/queue-summary",
            headers={"X-Session-Token": admin_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_queues" in data
        assert "waiting" in data
        assert "completed" in data
        assert "average_service_time_minutes" in data