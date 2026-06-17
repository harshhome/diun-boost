from datetime import datetime, timezone

from app.dashboard_snapshot import build_dashboard_snapshot


def test_build_dashboard_snapshot_groups_and_summarizes_updates():
    generated_at = datetime(2026, 6, 10, 17, 0, tzinfo=timezone.utc)
    config_entries = [
        {
            "name": "linuxserver/sonarr:4.0.17",
            "metadata": {
                "compose_project": "arr-stack",
                "compose_service": "sonarr",
                "current_tag": "4.0.17",
                "current_digest": "sha256:old-sonarr",
            },
            "include_tags": [r"^4\.0\..+$"],
        },
        {
            "name": "linuxserver/radarr:6.1.1",
            "metadata": {
                "compose_project": "arr-stack",
                "compose_service": "radarr",
                "current_tag": "6.1.1",
                "current_digest": "sha256:old-radarr",
            },
            "include_tags": [r"^6\.1\..+$"],
        },
    ]
    latest_by_image = {
        "linuxserver/sonarr": {
            "name": "linuxserver/sonarr",
            "latest": {
                "tag": "4.0.18",
                "digest": "sha256:new-sonarr",
                "created": "2026-06-10T15:00:00Z",
            },
        },
        "linuxserver/radarr": {
            "name": "linuxserver/radarr",
            "latest": {
                "tag": "6.1.1",
                "digest": "sha256:new-radarr",
                "created": "2026-06-10T16:00:00Z",
            },
        },
    }

    snapshot = build_dashboard_snapshot(
        config_entries,
        latest_by_image,
        generated_at=generated_at,
    )

    assert snapshot["generated_at"] == generated_at.isoformat()
    assert snapshot["summary"] == {
        "projects": 1,
        "services": 2,
        "tag_bumps": 1,
        "digest_refreshes": 1,
    }
    assert [project["name"] for project in snapshot["projects"]] == ["arr-stack"]

    services = snapshot["projects"][0]["services"]
    assert [service["service"] for service in services] == ["radarr", "sonarr"]
    assert services[0]["update_type"] == "digest_refresh"
    assert services[0]["current"] == "6.1.1"
    assert services[0]["latest"] == "6.1.1"
    assert services[1]["update_type"] == "tag_bump"
    assert services[1]["current"] == "4.0.17"
    assert services[1]["latest"] == "4.0.18"


def test_build_dashboard_snapshot_skips_entries_without_pending_updates():
    snapshot = build_dashboard_snapshot(
        [
            {
                "name": "linuxserver/prowlarr:2.3.5",
                "metadata": {
                    "compose_project": "arr-stack",
                    "compose_service": "prowlarr",
                    "current_tag": "2.3.5",
                    "current_digest": "sha256:same",
                },
            }
        ],
        {
            "linuxserver/prowlarr": {
                "name": "linuxserver/prowlarr",
                "latest": {
                    "tag": "2.3.5",
                    "digest": "sha256:same",
                    "created": "2026-06-10T16:00:00Z",
                },
            }
        },
    )

    assert snapshot["summary"] == {
        "projects": 0,
        "services": 0,
        "tag_bumps": 0,
        "digest_refreshes": 0,
    }
    assert snapshot["projects"] == []


def test_build_dashboard_snapshot_does_not_fall_back_to_latest_outside_include_tags():
    snapshot = build_dashboard_snapshot(
        [
            {
                "name": "teslamate/teslamate:4.0.1",
                "metadata": {
                    "compose_project": "teslamate",
                    "compose_service": "teslamate",
                    "current_tag": "4.0.1",
                    "current_digest": "sha256:current",
                },
                "include_tags": [r"^4\.0\.(?:[1-9]|\d{2,})$"],
            }
        ],
        {
            "teslamate/teslamate": {
                "name": "teslamate/teslamate",
                "latest": {
                    "tag": "4.0.0",
                    "digest": "sha256:old",
                    "created": "2026-06-10T16:00:00Z",
                },
            }
        },
        manifest_lookup={
            "teslamate/teslamate": [
                {"tag": "4.0.0", "digest": "sha256:old", "created": "2026-06-10T16:00:00Z"},
                {"tag": "3.1.0", "digest": "sha256:older", "created": "2026-06-09T16:00:00Z"},
            ]
        },
    )

    assert snapshot["summary"] == {
        "projects": 0,
        "services": 0,
        "tag_bumps": 0,
        "digest_refreshes": 0,
    }
    assert snapshot["projects"] == []


def test_build_dashboard_snapshot_does_not_report_numeric_downgrade():
    snapshot = build_dashboard_snapshot(
        [
            {
                "name": "teslamate/teslamate:4.0.1",
                "metadata": {
                    "compose_project": "teslamate",
                    "compose_service": "teslamate",
                    "current_tag": "4.0.1",
                    "current_digest": "sha256:current",
                },
            }
        ],
        {
            "teslamate/teslamate": {
                "name": "teslamate/teslamate",
                "latest": {
                    "tag": "4.0.0",
                    "digest": "sha256:old",
                    "created": "2026-06-10T16:00:00Z",
                },
            }
        },
    )

    assert snapshot["summary"] == {
        "projects": 0,
        "services": 0,
        "tag_bumps": 0,
        "digest_refreshes": 0,
    }
    assert snapshot["projects"] == []
