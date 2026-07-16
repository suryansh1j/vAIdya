"""Tests for patient update, delete, and search endpoints."""
from backend.models import Patient, User


def _doctor_id(db_session, username):
    return db_session.query(User).filter(User.username == username).one().id


def _create_patient(db_session, doctor_id, name, complaint=None, transcript=None):
    patient = Patient(
        doctor_id=doctor_id,
        patient_name=name,
        chief_complaint=complaint,
        transcript_text=transcript,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


def test_update_patient_fields(client, auth_headers, db_session, registered_user):
    doctor_id = _doctor_id(db_session, registered_user["username"])
    patient = _create_patient(db_session, doctor_id, "Before Edit")

    response = client.patch(
        f"/api/v1/patients/{patient.id}",
        headers=auth_headers,
        json={"patient_name": "After Edit", "allergies": "Penicillin"},
    )
    assert response.status_code == 200
    assert sorted(response.json()["updated_fields"]) == ["allergies", "patient_name"]

    detail = client.get(f"/api/v1/patients/{patient.id}", headers=auth_headers).json()
    assert detail["patient_name"] == "After Edit"
    assert detail["allergies"] == "Penicillin"
    # Untouched fields stay untouched
    assert detail["chief_complaint"] is None


def test_update_ignores_unset_fields(client, auth_headers, db_session, registered_user):
    doctor_id = _doctor_id(db_session, registered_user["username"])
    patient = _create_patient(db_session, doctor_id, "Keep Me", complaint="Headache")

    response = client.patch(
        f"/api/v1/patients/{patient.id}",
        headers=auth_headers,
        json={"lifestyle": "Non-smoker"},
    )
    assert response.status_code == 200

    detail = client.get(f"/api/v1/patients/{patient.id}", headers=auth_headers).json()
    assert detail["patient_name"] == "Keep Me"
    assert detail["chief_complaint"] == "Headache"
    assert detail["lifestyle"] == "Non-smoker"


def test_update_other_doctors_patient_404(client, auth_headers, db_session):
    client.post("/api/v1/auth/register", json={
        "username": "otherdoc2",
        "email": "otherdoc2@example.com",
        "password": "anothergoodpw1",
    })
    other_id = _doctor_id(db_session, "otherdoc2")
    patient = _create_patient(db_session, other_id, "Not Yours")

    response = client.patch(
        f"/api/v1/patients/{patient.id}",
        headers=auth_headers,
        json={"patient_name": "Hijacked"},
    )
    assert response.status_code == 404


def test_delete_patient(client, auth_headers, db_session, registered_user):
    doctor_id = _doctor_id(db_session, registered_user["username"])
    patient = _create_patient(db_session, doctor_id, "To Delete")

    response = client.delete(f"/api/v1/patients/{patient.id}", headers=auth_headers)
    assert response.status_code == 200

    assert client.get(f"/api/v1/patients/{patient.id}", headers=auth_headers).status_code == 404


def test_delete_requires_ownership(client, auth_headers, db_session):
    client.post("/api/v1/auth/register", json={
        "username": "otherdoc3",
        "email": "otherdoc3@example.com",
        "password": "anothergoodpw1",
    })
    other_id = _doctor_id(db_session, "otherdoc3")
    patient = _create_patient(db_session, other_id, "Protected")

    response = client.delete(f"/api/v1/patients/{patient.id}", headers=auth_headers)
    assert response.status_code == 404


def test_search_patients(client, auth_headers, db_session, registered_user):
    doctor_id = _doctor_id(db_session, registered_user["username"])
    _create_patient(db_session, doctor_id, "Alice Johnson", complaint="Migraine")
    _create_patient(db_session, doctor_id, "Bob Smith", complaint="Back pain")
    _create_patient(db_session, doctor_id, "Carol White", transcript="patient reports migraine episodes")

    # Search by name
    body = client.get("/api/v1/patients?q=alice", headers=auth_headers).json()
    assert body["count"] == 1
    assert body["patients"][0]["patient_name"] == "Alice Johnson"

    # Search matches complaint and transcript
    body = client.get("/api/v1/patients?q=migraine", headers=auth_headers).json()
    assert body["count"] == 2

    # No matches
    body = client.get("/api/v1/patients?q=zzznope", headers=auth_headers).json()
    assert body["count"] == 0
