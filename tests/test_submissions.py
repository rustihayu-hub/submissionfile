from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database.connection import init_db
from app.main import app

ORIGINAL_ASYNC_CLIENT = httpx.AsyncClient


@pytest.fixture(autouse=True)
def reset_db(tmp_path, monkeypatch):
    test_root = tmp_path
    monkeypatch.setenv("SUBMISSION_TESTING", "1")
    monkeypatch.setenv("DATABASE_PATH", str(test_root / "test.db"))
    monkeypatch.setenv("UPLOAD_DIR", str(test_root / "uploads"))
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "8")
    monkeypatch.setenv("AUTH_SERVICE_URL", "http://auth.test")
    monkeypatch.setenv("AUTH_VALIDATE_PATH", "/api/v1/auth/me")
    monkeypatch.setenv("ASSIGNMENT_SERVICE_URL", "http://assignment.test")
    monkeypatch.setenv("ASSIGNMENT_VALIDATE_PATH", "/api/assignments/{assignment_id}")
    monkeypatch.setenv("NOTIFICATION_SERVICE_URL", "http://notification.test")
    monkeypatch.setenv("NOTIFICATION_SUBMISSION_PATH", "/api/notifications")
    get_settings.cache_clear()
    init_db()
    yield


def client_with_transport(handler):
    transport = httpx.MockTransport(handler)

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return ORIGINAL_ASYNC_CLIENT(*args, **kwargs)

    return factory


@pytest.fixture
def api(monkeypatch):
    # Keep tests independent of a developer's local .env (which may contain
    # machine-specific or stale integration endpoints).
    monkeypatch.setenv("AUTH_SERVICE_URL", "http://auth.test")
    monkeypatch.setenv("AUTH_VALIDATE_PATH", "/api/v1/auth/me")
    monkeypatch.setenv("ASSIGNMENT_SERVICE_URL", "http://assignment.test")
    monkeypatch.setenv("ASSIGNMENT_VALIDATE_PATH", "/api/assignments/{assignment_id}")
    monkeypatch.setenv("NOTIFICATION_SERVICE_URL", "http://notification.test")
    monkeypatch.setenv("NOTIFICATION_SUBMISSION_PATH", "/api/notifications")
    get_settings.cache_clear()

    def handler(request):
        if "auth.test" in request.url.host:
            if request.headers.get("authorization") == "Bearer good":
                assert request.method == "GET"
                assert request.url.path == "/api/v1/auth/me"
                return httpx.Response(200, json={"id": "user-1", "role": "mahasiswa"})
            return httpx.Response(401, json={})
        if "assignment.test" in request.url.host:
            assert request.headers.get("authorization") == "Bearer good"
            return httpx.Response(200, json={"success": True, "data": {"id": "a1"}})
        if "notification.test" in request.url.host:
            assert request.headers.get("authorization") == "Bearer good"
            assert request.url.path == "/api/notifications"
            return httpx.Response(503, json={})  # Notification failure must not undo creation.
        return httpx.Response(500)

    factory = client_with_transport(handler)
    monkeypatch.setattr("app.services.auth_service.httpx.AsyncClient", factory)
    monkeypatch.setattr("app.services.assignment_service.httpx.AsyncClient", factory)
    monkeypatch.setattr("app.services.notification_service.httpx.AsyncClient", factory)
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_request_id(api):
    response = api.get("/health", headers={"X-Request-ID": "req-test"})
    assert response.status_code == 200
    assert response.json()["meta"]["request_id"] == "req-test"


def test_openapi_documents_submission_contract(api):
    schema = api.get("/openapi.json").json()
    post = schema["paths"]["/api/submissions"]["post"]
    assert "multipart/form-data" in post["requestBody"]["content"]
    assert "201" in post["responses"]
    assert "400" in post["responses"]
    assert "422" not in post["responses"]
    response_schema = post["responses"]["201"]["content"]["application/json"]["schema"]
    assert response_schema["$ref"].endswith("SubmissionCreateResponse")
    assert {"get", "post"}.issubset(schema["paths"]["/api/submissions"])
    assert "delete" in schema["paths"]["/api/submissions/{submission_id}"]


def test_missing_token_is_401(api):
    response = api.get("/api/submissions?assignment_id=a1")
    assert response.status_code == 401


def test_auth_invalid_token_is_401(api, monkeypatch):
    def handler(request):
        return httpx.Response(401, json={"error": "Unauthorized"})

    monkeypatch.setattr("app.services.auth_service.httpx.AsyncClient", client_with_transport(handler))
    response = api.get("/api/submissions?assignment_id=a1", headers={"Authorization": "Bearer expired"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_auth_profile_data_envelope(api, monkeypatch):
    def handler(request):
        assert request.method == "GET"
        assert request.headers["authorization"] == "Bearer good"
        return httpx.Response(200, json={"success": True, "data": {"sub": "user-envelope"}})

    monkeypatch.setattr("app.services.auth_service.httpx.AsyncClient", client_with_transport(handler))
    response = api.get("/api/submissions?assignment_id=a1", headers={"Authorization": "Bearer good"})
    assert response.status_code == 200


def test_list_empty(api):
    response = api.get("/api/submissions?assignment_id=a1", headers={"Authorization": "Bearer good"})
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 0


def test_upload_success_notification_failure_and_delete(api):
    response = api.post("/api/submissions", data={"assignment_id": "a1"},
                        files={"file": ("answer.txt", b"abc", "text/plain")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 201, response.text
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
            return httpx.Response(200, json={"id": "user-1"})
        return httpx.Response(404, json={"success": False})

    monkeypatch.setattr("app.services.assignment_service.httpx.AsyncClient", client_with_transport(handler))
    response = api.post("/api/submissions", data={"assignment_id": "bad"},
                        files={"file": ("answer.txt", b"abc", "text/plain")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 400


def test_assignment_success_and_notification_payload(api, monkeypatch):
    seen = {}

    def handler(request):
        if request.url.host == "auth.test":
            return httpx.Response(200, json={"id": "user-1"})
        if request.url.host == "assignment.test":
            seen["assignment"] = request
            return httpx.Response(200, json={"success": True, "data": {"id": "a1", "title": "Task"}})
        if request.url.host == "notification.test":
            seen["notification"] = request
            return httpx.Response(201, json={"success": True, "data": {"id": "notif-1"}})
        return httpx.Response(500)

    def unused_assignment_handler(request):
        seen["assignment"] = request
        return httpx.Response(200, json={"success": True, "data": {"id": "a1", "title": "Task"}})

    def unused_notification_handler(request):
        seen["notification"] = request
        return httpx.Response(201, json={"success": True, "data": {"id": "notif-1"}})

    factory = client_with_transport(handler)
    monkeypatch.setattr("app.services.assignment_service.httpx.AsyncClient", factory)
    monkeypatch.setattr("app.services.notification_service.httpx.AsyncClient", factory)
    monkeypatch.setattr("app.services.auth_service.httpx.AsyncClient", factory)
    response = api.post("/api/submissions", data={"assignment_id": "a1"},
                        files={"file": ("answer.txt", b"abc", "text/plain")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 201
    assert seen["assignment"].method == "GET"
    assert seen["assignment"].url.path == "/api/assignments/a1"
    assert seen["assignment"].headers["authorization"] == "Bearer good"
    assert seen["notification"].method == "POST"
    assert seen["notification"].url.path == "/api/notifications"
    assert seen["notification"].headers["authorization"] == "Bearer good"
    payload = __import__("json").loads(seen["notification"].content)
    assert payload["user_id"] == "user-1"
    assert payload["submission_id"] == response.json()["data"]["submission"]["id"]
    assert payload["type"] == "submission"
    assert payload["message"]


def test_assignment_upstream_error_is_503(api, monkeypatch):
    def handler(request):
        if request.url.host == "auth.test":
            return httpx.Response(200, json={"id": "user-1"})
        return httpx.Response(500, json={})

    monkeypatch.setattr("app.services.assignment_service.httpx.AsyncClient", client_with_transport(handler))
    response = api.post("/api/submissions", data={"assignment_id": "a1"},
                        files={"file": ("answer.txt", b"abc", "text/plain")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 503


def test_notification_connection_failure_does_not_undo_submission(api, monkeypatch):
    def fail(request):
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr("app.services.notification_service.httpx.AsyncClient", client_with_transport(fail))
    monkeypatch.setattr("app.services.auth_service.httpx.AsyncClient", client_with_transport(
        lambda request: httpx.Response(200, json={"id": "user-1"})))
    response = api.post("/api/submissions", data={"assignment_id": "a1"},
                        files={"file": ("answer.txt", b"abc", "text/plain")},
                        headers={"Authorization": "Bearer good"})
    assert response.status_code == 201
    assert response.json()["data"]["submission"]["status"] == "submitted"


def test_assignment_unavailable(api, monkeypatch):
    def handler(request):
        if "auth.test" in request.url.host:
            return httpx.Response(200, json={"id": "user-1"})
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


def test_invalid_submission_input_is_400(api):
    missing_file = api.post("/api/submissions", data={"assignment_id": "a1"},
                            headers={"Authorization": "Bearer good"})
    assert missing_file.status_code == 400
    blank_assignment = api.post("/api/submissions", data={"assignment_id": "   "},
                                files={"file": ("answer.txt", b"abc", "text/plain")},
                                headers={"Authorization": "Bearer good"})
    assert blank_assignment.status_code == 400


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
