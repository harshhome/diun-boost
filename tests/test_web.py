import json

from fastapi.testclient import TestClient

from app import web


def test_api_report_reads_dashboard_snapshot(tmp_path, monkeypatch):
    snapshot_path = tmp_path / "dashboard.json"
    snapshot = {
        "generated_at": "2026-06-10T17:00:00+00:00",
        "projects": [{"name": "arr-stack", "services": []}],
        "summary": {
            "projects": 1,
            "services": 0,
            "tag_bumps": 0,
            "digest_refreshes": 0,
        },
    }
    snapshot_path.write_text(json.dumps(snapshot))
    monkeypatch.setattr(web, "DASHBOARD_JSON_PATH", snapshot_path)

    client = TestClient(web.app)
    response = client.get("/api/report")

    assert response.status_code == 200
    assert response.json() == snapshot


def test_healthz_returns_app_name():
    client = TestClient(web.app)
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"] == web.APP_NAME
