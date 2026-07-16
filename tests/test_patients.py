"""Tests for patient endpoints: pagination, isolation between doctors, symptoms parsing."""
import json

from backend.models import Patient, User


def _create_patient(db_session, doctor_id, name, symptoms=None):
    patient = Patient(
        doctor_id=doctor_id,
        patient_name=name,
        age="42",
        gender="Male",
        symptoms_extracted=json.dumps(symptoms) if symptoms is not None else None,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


def _doctor_id(db_session, username):
    return db_session.query(User).filter(User.username == username).one().id


def test_patients_requires_auth(client):
    assert client.get("/api/v1/patients").status_code == 401


def test_patients_empty(client, auth_headers):
    response = client.get("/api/v1/patients", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["patients"] == []


def test_patients_pagination(client, auth_headers, db_session, registered_user):
    doctor_id = _doctor_id(db_session, registered_user["username"])
    for i in range(5):
        _create_patient(db_session, doctor_id, f"Patient {i}")

    response = client.get("/api/v1/patients?limit=2&offset=0", headers=auth_headers)
    body = response.json()
    assert body["count"] == 5
    assert len(body["patients"]) == 2

    response = client.get("/api/v1/patients?limit=2&offset=4", headers=auth_headers)
    body = response.json()
    assert len(body["patients"]) == 1


def test_patient_detail_parses_symptoms_json(client, auth_headers, db_session, registered_user):
    doctor_id = _doctor_id(db_session, registered_user["username"])
    symptoms = {"affirmed": ["fever", "cough"], "negated": ["chest pain"]}
    patient = _create_patient(db_session, doctor_id, "Jane Doe", symptoms=symptoms)

    response = client.get(f"/api/v1/patients/{patient.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["symptoms"] == symptoms


def test_patient_detail_tolerates_legacy_symptoms(client, auth_headers, db_session, registered_user):
    doctor_id = _doctor_id(db_session, registered_user["username"])
    patient = Patient(
        doctor_id=doctor_id,
        patient_name="Legacy Row",
        symptoms_extracted="{'affirmed': ['fever'], 'negated': []}",  # old str(dict) format
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    response = client.get(f"/api/v1/patients/{patient.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["symptoms"] == {"raw": "{'affirmed': ['fever'], 'negated': []}"}


def test_patient_not_found(client, auth_headers):
    response = client.get("/api/v1/patients/9999", headers=auth_headers)
    assert response.status_code == 404


def test_patient_isolated_between_doctors(client, auth_headers, db_session, registered_user):
    # Another doctor with their own patient
    other = client.post("/api/v1/auth/register", json={
        "username": "otherdoc",
        "email": "otherdoc@example.com",
        "password": "anothergoodpw1",
    })
    assert other.status_code == 200
    other_id = _doctor_id(db_session, "otherdoc")
    other_patient = _create_patient(db_session, other_id, "Not Yours")

    # First doctor must not see it
    response = client.get(f"/api/v1/patients/{other_patient.id}", headers=auth_headers)
    assert response.status_code == 404
