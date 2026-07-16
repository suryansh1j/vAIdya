"""Tests for the audio upload endpoint (with ML dependencies absent)."""
import io

from backend import nlp_processor


def test_upload_requires_auth(client):
    response = client.post(
        "/api/v1/upload-audio",
        files={"file": ("test.wav", io.BytesIO(b"RIFF....WAVE"), "audio/wav")},
    )
    assert response.status_code == 401


def test_upload_returns_503_when_nlp_unavailable(client, auth_headers):
    if nlp_processor.NLP_AVAILABLE:
        return  # environment has ML deps installed; nothing to assert here
    response = client.post(
        "/api/v1/upload-audio",
        headers=auth_headers,
        files={"file": ("test.wav", io.BytesIO(b"RIFF....WAVE"), "audio/wav")},
    )
    assert response.status_code == 503


def test_health_reports_nlp_status(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["nlp_available"] == nlp_processor.NLP_AVAILABLE
