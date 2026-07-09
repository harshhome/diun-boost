import importlib

import yaml

from app import main


def test_default_dashboard_commands_path_is_dedicated_dashboard_yml(monkeypatch):
    monkeypatch.delenv("DIUN_DASHBOARD_COMMANDS_PATH", raising=False)

    reloaded = importlib.reload(main)

    assert reloaded.DEFAULT_DASHBOARD_COMMANDS_PATH == "/config/dashboard.yml"


def test_dashboard_commands_path_env_override(monkeypatch):
    monkeypatch.setenv("DIUN_DASHBOARD_COMMANDS_PATH", "/custom/dashboard.yml")

    reloaded = importlib.reload(main)

    assert reloaded.DEFAULT_DASHBOARD_COMMANDS_PATH == "/custom/dashboard.yml"
    monkeypatch.delenv("DIUN_DASHBOARD_COMMANDS_PATH", raising=False)
    importlib.reload(main)


def test_generate_dashboard_snapshot_from_yaml_does_not_read_commands_from_diun_yaml_by_default(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yml"
    dashboard_path = tmp_path / "dashboard.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "dashboard": {
                    "commands": [
                        {
                            "name": "wrong-place",
                            "scope": "service",
                            "label": "Wrong place",
                            "template": "{service}",
                        }
                    ]
                }
            }
        )
    )
    calls = []

    monkeypatch.setattr(main, "DEFAULT_DASHBOARD_COMMANDS_PATH", str(dashboard_path))
    monkeypatch.setattr(
        main,
        "build_snapshot_from_entries",
        lambda entries, container_name, dashboard_commands: calls.append(dashboard_commands)
        or {"commands": dashboard_commands},
    )

    snapshot = main.generate_dashboard_snapshot_from_yaml(str(config_path), "diun")

    assert snapshot == {"commands": []}
    assert calls == [[]]


def test_generate_dashboard_snapshot_from_yaml_loads_commands_from_dashboard_yml(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yml"
    dashboard_path = tmp_path / "dashboard.yml"
    config_path.write_text("[]\n")
    dashboard_path.write_text(
        yaml.safe_dump(
            {
                "dashboard": {
                    "commands": [
                        {
                            "name": "update-note",
                            "scope": "service",
                            "label": "Update note",
                            "template": "{service}: {latest}",
                        }
                    ]
                }
            }
        )
    )

    monkeypatch.setattr(main, "DEFAULT_DASHBOARD_COMMANDS_PATH", str(dashboard_path))
    monkeypatch.setattr(
        main,
        "build_snapshot_from_entries",
        lambda entries, container_name, dashboard_commands: {"commands": dashboard_commands},
    )

    snapshot = main.generate_dashboard_snapshot_from_yaml(str(config_path), "diun")

    assert snapshot == {
        "commands": [
            {
                "name": "update-note",
                "scope": "service",
                "label": "Update note",
                "icon": "code",
                "template": "{service}: {latest}",
            }
        ]
    }


def test_generate_dashboard_snapshot_from_yaml_uses_saved_config(monkeypatch):
    entries = [
        {
            "name": "linuxserver/sonarr:4.0.17",
            "metadata": {
                "compose_project": "arr-stack",
                "compose_service": "sonarr",
                "current_tag": "4.0.17",
            },
        }
    ]
    latest_by_image = {
        "linuxserver/sonarr": {
            "latest": {"tag": "4.0.18", "digest": "sha256:new"}
        }
    }
    manifest_lookup = {"linuxserver/sonarr": [{"tag": "4.0.18", "digest": "sha256:new"}]}
    expected_snapshot = {"generated_at": "2026-06-11T00:00:00+00:00", "projects": [], "summary": {}}

    monkeypatch.setattr(main, "load_yaml_entries", lambda path: entries)
    monkeypatch.setattr(main, "get_docker_client", lambda: object())
    monkeypatch.setattr(main, "load_diun_latest", lambda client, container_name: latest_by_image)
    monkeypatch.setattr(
        main,
        "build_manifest_lookup",
        lambda client, container_name, source_entries, latest: manifest_lookup,
    )
    monkeypatch.setattr(
        main,
        "build_dashboard_snapshot",
        lambda source_entries, latest, manifest_lookup=None, dashboard_commands=None: expected_snapshot,
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not scan running containers for dashboard-only refresh")

    monkeypatch.setattr(main, "get_running_containers", fail_if_called)

    snapshot = main.generate_dashboard_snapshot_from_yaml("/tmp/config.yml", "diun")

    assert snapshot == expected_snapshot


def test_generate_targeted_dashboard_snapshot_filters_to_pending_services(monkeypatch):
    existing_entries = [
        {
            "name": "linuxserver/sonarr:4.0.17",
            "metadata": {
                "compose_project": "arr-stack",
                "compose_service": "sonarr",
                "current_tag": "4.0.17",
            },
        },
        {
            "name": "linuxserver/radarr:6.1.1",
            "metadata": {
                "compose_project": "arr-stack",
                "compose_service": "radarr",
                "current_tag": "6.1.1",
            },
        },
    ]
    dashboard_snapshot = {
        "projects": [
            {
                "name": "arr-stack",
                "services": [
                    {"service": "sonarr", "current": "4.0.17", "latest": "4.0.18"}
                ],
            }
        ]
    }
    live_entries = [
        {
            "name": "linuxserver/sonarr:4.0.18",
            "metadata": {
                "compose_project": "arr-stack",
                "compose_service": "sonarr",
                "current_tag": "4.0.18",
            },
        }
    ]
    expected_snapshot = {"generated_at": "2026-06-11T00:07:00+00:00", "projects": [], "summary": {}}

    monkeypatch.setattr(main, "load_yaml_entries", lambda path: existing_entries)
    monkeypatch.setattr(main, "load_dashboard_json", lambda path: dashboard_snapshot)
    monkeypatch.setattr(main, "get_docker_client", lambda: object())
    monkeypatch.setattr(
        main,
        "get_containers_for_compose_services",
        lambda client, scope: ["sonarr-container"],
    )
    monkeypatch.setattr(
        main,
        "create_diun_yaml",
        lambda containers, m_all, compose_track: live_entries,
    )
    monkeypatch.setattr(main, "merge_custom_metadata", lambda entries, existing: entries)
    monkeypatch.setattr(main, "load_diun_latest", lambda client, container_name: {})
    monkeypatch.setattr(main, "build_manifest_lookup", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        main,
        "build_dashboard_snapshot",
        lambda source_entries, latest, manifest_lookup=None, dashboard_commands=None: expected_snapshot,
    )

    snapshot = main.generate_targeted_dashboard_snapshot(
        "/tmp/config.yml",
        "/tmp/dashboard.json",
        compose_track=True,
        diun_container_name="diun",
    )

    assert snapshot == expected_snapshot


def test_generate_targeted_dashboard_snapshot_returns_existing_empty_snapshot(monkeypatch):
    empty_snapshot = {
        "generated_at": "2026-06-11T00:10:00+00:00",
        "projects": [],
        "summary": {
            "projects": 0,
            "services": 0,
            "tag_bumps": 0,
            "digest_refreshes": 0,
        },
    }

    monkeypatch.setattr(main, "load_dashboard_json", lambda path: empty_snapshot)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("empty snapshot refresh should not call Docker or DIUN")

    monkeypatch.setattr(main, "load_yaml_entries", fail_if_called)
    monkeypatch.setattr(main, "generate_dashboard_snapshot_from_yaml", fail_if_called)
    monkeypatch.setattr(main, "get_docker_client", fail_if_called)

    snapshot = main.generate_targeted_dashboard_snapshot(
        "/tmp/config.yml",
        "/tmp/dashboard.json",
        compose_track=True,
        diun_container_name="diun",
    )

    assert snapshot == empty_snapshot
