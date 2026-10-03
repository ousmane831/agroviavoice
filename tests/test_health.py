from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_sante():
    reponse = client.get("/api/v1/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok", "service": "sama-agri-ai"}
