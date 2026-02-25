from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.main import app


client = TestClient(app)


def test_ping_returns_pong() -> None:
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"message": "pong"}
