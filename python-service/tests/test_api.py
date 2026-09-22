from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP", "service": "python-service"}


def test_internal_answer_endpoint() -> None:
    response = client.post(
        "/internal/answer",
        json={
            "tenant": "Atlas",
            "role": "employee",
            "as_of": "2026-09-21",
            "question": "What is my annual certification reimbursement limit?",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ANSWERED"
    assert response.json()["citations"][0]["chunk_id"] == "atlas-cert-current"


def test_invalid_date_is_rejected() -> None:
    response = client.post(
        "/internal/answer",
        json={
            "tenant": "Atlas",
            "role": "employee",
            "as_of": "21-09-2026",
            "question": "What is my annual certification reimbursement limit?",
        },
    )

    assert response.status_code == 422
