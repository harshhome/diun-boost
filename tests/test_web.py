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


def test_api_report_refresh_generates_live_snapshot(monkeypatch):
    snapshot = {
        "generated_at": "2026-06-10T17:05:00+00:00",
        "projects": [{"name": "arr-stack", "services": []}],
        "summary": {
            "projects": 1,
            "services": 0,
            "tag_bumps": 0,
            "digest_refreshes": 0,
        },
    }

    monkeypatch.setattr(web, "refresh_dashboard_snapshot", lambda: snapshot)

    client = TestClient(web.app)
    response = client.post("/api/report/refresh")

    assert response.status_code == 200
    assert response.json() == snapshot


def test_api_report_hard_refresh_generates_live_snapshot(monkeypatch):
    snapshot = {
        "generated_at": "2026-06-10T17:10:00+00:00",
        "projects": [{"name": "arr-stack", "services": []}],
        "summary": {
            "projects": 1,
            "services": 0,
            "tag_bumps": 0,
            "digest_refreshes": 0,
        },
    }

    monkeypatch.setattr(web, "refresh_dashboard_snapshot_hard", lambda: snapshot)

    client = TestClient(web.app)
    response = client.post("/api/report/hard-refresh")

    assert response.status_code == 200
    assert response.json() == snapshot


def test_refresh_dashboard_snapshot_hard_uses_full_generator_and_writes_snapshot(tmp_path, monkeypatch):
    snapshot_path = tmp_path / "dashboard.json"
    snapshot = {
        "generated_at": "2026-06-10T17:15:00+00:00",
        "projects": [],
        "summary": {
            "projects": 0,
            "services": 0,
            "tag_bumps": 0,
            "digest_refreshes": 0,
        },
    }
    calls = []

    def fake_generate_dashboard_snapshot(output_path, monitor_all, compose_track, diun_container_name):
        calls.append((output_path, monitor_all, compose_track, diun_container_name))
        return snapshot

    def fail_if_called(*args, **kwargs):
        raise AssertionError("hard refresh should not use targeted refresh")

    monkeypatch.setattr(web, "DASHBOARD_JSON_PATH", snapshot_path)
    monkeypatch.setattr(web, "DEFAULT_OUTPUT_PATH", "/tmp/config.yml")
    monkeypatch.setattr(web, "DEFAULT_MONITOR_ALL", True)
    monkeypatch.setattr(web, "DEFAULT_COMPOSE_TRACK", True)
    monkeypatch.setattr(web, "DEFAULT_DIUN_CONTAINER_NAME", "diun-test")
    monkeypatch.setattr(web, "generate_dashboard_snapshot", fake_generate_dashboard_snapshot)
    monkeypatch.setattr(web, "generate_targeted_dashboard_snapshot", fail_if_called)

    result = web.refresh_dashboard_snapshot_hard()

    assert result == snapshot
    assert calls == [("/tmp/config.yml", True, True, "diun-test")]
    assert json.loads(snapshot_path.read_text()) == snapshot


def test_healthz_returns_app_name():
    client = TestClient(web.app)
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"] == web.APP_NAME
