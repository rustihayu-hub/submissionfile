import os

os.environ["DATABASE_PATH"] = "./storage/test_submissions.db"
os.environ["UPLOAD_DIR"] = "./storage/test_uploads"
os.environ["AUTH_SERVICE_URL"] = "http://auth.test"
os.environ["ASSIGNMENT_SERVICE_URL"] = "http://assignment.test"
os.environ["NOTIFICATION_SERVICE_URL"] = "http://notification.test"

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database.connection import init_db
from app.main import app

ORIGINAL_ASYNC_CLIENT = httpx.AsyncClient


@pytest.fixture(autouse=True)
def reset_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "8")
    get_settings.cache_clear()
    init_db()


def client_with_transport(handler):
    transport = httpx.MockTransport(handler)

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return ORIGINAL_ASYNC_CLIENT(*args, **kwargs)

    return factory


@pytest.fixture
def api(monkeypatch):
    def handler(request):
        if "auth.test" in request.url.host:
            if request.headers.get("authorization") == "Bearer good":
                return httpx.Response(200, json={"valid": True, "user": {"id": "user-1"}})
            return httpx.Response(401, json={})
        if "assignment.test" in request.url.host:
            return httpx.Response(200, json={"exists": True})
        return httpx.Response(503, json={})  # Notification failure must not undo creation.

    monkeypatch.setattr("app.services.auth_service.httpx.AsyncClient", client_with_transport(handler))
    monkeypatch.setattr("app.services.assignment_service.httpx.AsyncClient", client_with_transport(handler))
    monkeypatch.setattr("app.services.notification_service.httpx.AsyncClient", client_with_transport(handler))
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_request_id(api):
    response = api.get("/health", headers={"X-Request-ID": "req-test"})
    assert response.status_code == 200
    assert response.json()["meta"]["request_id"] == "req-test"


def test_missing_token_is_401(api):
    response = api.get("/api/submissions?assignment_id=a1")
    assert response.status_code == 401


def test_list_empty(api):
    response = api.get("/api/submissions?assignment_id=a1", headers={"Authorization": "Bearer good"})
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 0


def test_upload_success_notification_failure_and_delete(api):
    response = api.post("/api/submissions", data={"assignment_id": "a1"},
                        files={"file": ("answer.txt", b"abc", "text/plain")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 201
    record = response.json()["data"]["submission"]
    file_path = get_settings().uploads_path / record["stored_filename"]
    assert file_path.is_file()
    listed = api.get("/api/submissions?assignment_id=a1", headers={"Authorization": "Bearer good"})
    assert listed.status_code == 200
    assert listed.json()["data"]["count"] == 1
    assert listed.json()["data"]["items"][0]["id"] == record["id"]
    deleted = api.delete(f"/api/submissions/{record['id']}", headers={"Authorization": "Bearer good"})
    assert deleted.status_code == 200
    assert not file_path.exists()
    assert api.delete(f"/api/submissions/{record['id']}", headers={"Authorization": "Bearer good"}).status_code == 404


def test_empty_assignment_is_400(api):
    response = api.post("/api/submissions", data={"assignment_id": ""},
                        files={"file": ("answer.txt", b"abc", "text/plain")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 400


def test_invalid_assignment(api, monkeypatch):
    def handler(request):
        if "auth.test" in request.url.host:
            return httpx.Response(200, json={"valid": True, "user": {"id": "user-1"}})
        return httpx.Response(404, json={})

    monkeypatch.setattr("app.services.assignment_service.httpx.AsyncClient", client_with_transport(handler))
    response = api.post("/api/submissions", data={"assignment_id": "bad"},
                        files={"file": ("answer.txt", b"abc", "text/plain")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 400


def test_assignment_unavailable(api, monkeypatch):
    def handler(request):
        if "auth.test" in request.url.host:
            return httpx.Response(200, json={"valid": True, "user": {"id": "user-1"}})
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr("app.services.assignment_service.httpx.AsyncClient", client_with_transport(handler))
    response = api.post("/api/submissions", data={"assignment_id": "a1"},
                        files={"file": ("answer.txt", b"abc", "text/plain")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 503


def test_upload_size_and_type_validation(api):
    headers = {"Authorization": "Bearer good"}
    too_big = api.post("/api/submissions", data={"assignment_id": "a1"},
                       files={"file": ("answer.txt", b"123456789", "text/plain")}, headers=headers)
    assert too_big.status_code == 413
    unsupported = api.post("/api/submissions", data={"assignment_id": "a1"},
                           files={"file": ("payload.exe", b"x", "application/octet-stream")}, headers=headers)
    assert unsupported.status_code == 415


def test_empty_file_rejected(api):
    response = api.post("/api/submissions", data={"assignment_id": "a1"},
                        files={"file": ("empty.txt", b"", "text/plain")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_file"


def test_mime_type_mismatch_rejected(api):
    response = api.post("/api/submissions", data={"assignment_id": "a1"},
                        files={"file": ("answer.txt", b"abc", "application/pdf")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 415


def test_missing_submission_gets_404(api):
    response = api.delete("/api/submissions/missing-id", headers={"Authorization": "Bearer good"})
    assert response.status_code == 404
