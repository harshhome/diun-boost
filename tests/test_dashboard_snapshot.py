from datetime import datetime, timezone

from app.dashboard_snapshot import build_dashboard_snapshot


def test_build_dashboard_snapshot_groups_and_summarizes_updates():
    generated_at = datetime(2026, 6, 10, 17, 0, tzinfo=timezone.utc)
    config_entries = [
        {
            "name": "registry.example.test/sample/service-gamma:4.0.17",
            "metadata": {
                "compose_project": "sample-stack",
                "compose_service": "service-gamma",
                "current_tag": "4.0.17",
                "current_digest": "sha256:old-service-gamma",
            },
            "include_tags": [r"^4\.0\..+$"],
        },
        {
            "name": "registry.example.test/sample/service-beta:6.1.1",
            "metadata": {
                "compose_project": "sample-stack",
                "compose_service": "service-beta",
                "current_tag": "6.1.1",
                "current_digest": "sha256:old-service-beta",
            },
            "include_tags": [r"^6\.1\..+$"],
        },
    ]
    latest_by_image = {
        "registry.example.test/sample/service-gamma": {
            "name": "registry.example.test/sample/service-gamma",
            "latest": {
                "tag": "4.0.18",
                "digest": "sha256:new-service-gamma",
                "created": "2026-06-10T15:00:00Z",
            },
        },
        "registry.example.test/sample/service-beta": {
            "name": "registry.example.test/sample/service-beta",
            "latest": {
                "tag": "6.1.1",
                "digest": "sha256:new-service-beta",
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
    assert [project["name"] for project in snapshot["projects"]] == ["sample-stack"]

    services = snapshot["projects"][0]["services"]
    assert [service["service"] for service in services] == ["service-beta", "service-gamma"]
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
                "name": "registry.example.test/sample/service-delta:2.3.5",
                "metadata": {
                    "compose_project": "sample-stack",
                    "compose_service": "service-delta",
                    "current_tag": "2.3.5",
                    "current_digest": "sha256:same",
                },
            }
        ],
        {
            "registry.example.test/sample/service-delta": {
                "name": "registry.example.test/sample/service-delta",
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



def test_build_dashboard_snapshot_skips_digest_refresh_when_latest_is_in_repo_digests():
    snapshot = build_dashboard_snapshot(
        [
            {
                "name": "sample-cache:8.8.0",
                "metadata": {
                    "compose_project": "sample-app",
                    "compose_service": "sample-cache",
                    "current_tag": "8.8.0",
                    "current_digest": "sha256:027002f3",
                    "current_repo_digests": (
                        '["sha256:027002f3","sha256:2838d552"]'
                    ),
                },
            }
        ],
        {
            "library/sample-cache": {
                "name": "library/sample-cache",
                "latest": {
                    "tag": "8.8.0",
                    "digest": "sha256:2838d552",
                    "created": "2026-06-10T16:00:00Z",
                },
            }
        },
    )

    assert snapshot["summary"]["digest_refreshes"] == 0
    assert snapshot["projects"] == []


def test_build_dashboard_snapshot_reports_digest_refresh_when_latest_missing_from_repo_digests():
    snapshot = build_dashboard_snapshot(
        [
            {
                "name": "sample-cache:8.8.0",
                "metadata": {
                    "compose_project": "sample-app",
                    "compose_service": "sample-cache",
                    "current_tag": "8.8.0",
                    "current_digest": "sha256:027002f3",
                    "current_repo_digests": '["sha256:027002f3"]',
                },
            }
        ],
        {
            "library/sample-cache": {
                "name": "library/sample-cache",
                "latest": {
                    "tag": "8.8.0",
                    "digest": "sha256:2838d552",
                    "created": "2026-06-10T16:00:00Z",
                },
            }
        },
    )

    assert snapshot["summary"]["digest_refreshes"] == 1
    assert snapshot["projects"] == [
        {
            "name": "sample-app",
            "services": [
                {
                    "service": "sample-cache",
                    "update_type": "digest_refresh",
                    "current": "8.8.0",
                    "latest": "8.8.0",
                    "metadata": {
                        "compose_project": "sample-app",
                        "compose_service": "sample-cache",
                        "current_tag": "8.8.0",
                        "current_digest": "sha256:027002f3",
                        "current_repo_digests": '["sha256:027002f3"]',
                    },
                }
            ],
        }
    ]


def test_build_dashboard_snapshot_includes_valid_release_notes_url():
    snapshot = build_dashboard_snapshot(
        [
            {
                "name": "sample-cache:8.8.0",
                "metadata": {
                    "compose_project": "sample-app",
                    "compose_service": "sample-cache",
                    "current_tag": "8.8.0",
                    "current_digest": "sha256:027002f3",
                    "release_notes_url": "https://releases.example.test/cache",
                },
            }
        ],
        {
            "library/sample-cache": {
                "name": "library/sample-cache",
                "latest": {
                    "tag": "8.8.0",
                    "digest": "sha256:2838d552",
                    "created": "2026-06-10T16:00:00Z",
                },
            }
        },
    )

    service = snapshot["projects"][0]["services"][0]
    assert service["release_notes_url"] == "https://releases.example.test/cache"


def test_build_dashboard_snapshot_omits_release_notes_url_when_missing():
    snapshot = build_dashboard_snapshot(
        [
            {
                "name": "sample-cache:8.8.0",
                "metadata": {
                    "compose_project": "sample-app",
                    "compose_service": "sample-cache",
                    "current_tag": "8.8.0",
                    "current_digest": "sha256:027002f3",
                },
            }
        ],
        {
            "library/sample-cache": {
                "name": "library/sample-cache",
                "latest": {
                    "tag": "8.8.0",
                    "digest": "sha256:2838d552",
                    "created": "2026-06-10T16:00:00Z",
                },
            }
        },
    )

    service = snapshot["projects"][0]["services"][0]
    assert "release_notes_url" not in service


def test_build_dashboard_snapshot_ignores_invalid_release_notes_url_values():
    invalid_values = [
        "releases.example.test/cache",
        "ftp://releases.example.test/cache",
        123,
        None,
    ]

    for invalid_value in invalid_values:
        snapshot = build_dashboard_snapshot(
            [
                {
                    "name": "sample-cache:8.8.0",
                    "metadata": {
                        "compose_project": "sample-app",
                        "compose_service": "sample-cache",
                        "current_tag": "8.8.0",
                        "current_digest": "sha256:027002f3",
                        "release_notes_url": invalid_value,
                    },
                }
            ],
            {
                "library/sample-cache": {
                    "name": "library/sample-cache",
                    "latest": {
                        "tag": "8.8.0",
                        "digest": "sha256:2838d552",
                        "created": "2026-06-10T16:00:00Z",
                    },
                }
            },
        )

        service = snapshot["projects"][0]["services"][0]
        assert "release_notes_url" not in service


def test_build_dashboard_snapshot_preserves_digest_compatibility_without_repo_digests():
    snapshot = build_dashboard_snapshot(
        [
            {
                "name": "sample-cache:8.8.0",
                "metadata": {
                    "compose_project": "sample-app",
                    "compose_service": "sample-cache",
                    "current_tag": "8.8.0",
                    "current_digest": "sha256:027002f3",
                },
            }
        ],
        {
            "library/sample-cache": {
                "name": "library/sample-cache",
                "latest": {
                    "tag": "8.8.0",
                    "digest": "sha256:2838d552",
                    "created": "2026-06-10T16:00:00Z",
                },
            }
        },
    )

    assert snapshot["summary"]["digest_refreshes"] == 1

def test_build_dashboard_snapshot_does_not_fall_back_to_latest_outside_include_tags():
    snapshot = build_dashboard_snapshot(
        [
            {
                "name": "registry.example.test/sample/telemetry:4.0.1",
                "metadata": {
                    "compose_project": "sample-telemetry",
                    "compose_service": "sample-telemetry",
                    "current_tag": "4.0.1",
                    "current_digest": "sha256:current",
                },
                "include_tags": [r"^4\.0\.(?:[1-9]|\d{2,})$"],
            }
        ],
        {
            "registry.example.test/sample/telemetry": {
                "name": "registry.example.test/sample/telemetry",
                "latest": {
                    "tag": "4.0.0",
                    "digest": "sha256:old",
                    "created": "2026-06-10T16:00:00Z",
                },
            }
        },
        manifest_lookup={
            "registry.example.test/sample/telemetry": [
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
                "name": "registry.example.test/sample/telemetry:4.0.1",
                "metadata": {
                    "compose_project": "sample-telemetry",
                    "compose_service": "sample-telemetry",
                    "current_tag": "4.0.1",
                    "current_digest": "sha256:current",
                },
            }
        ],
        {
            "registry.example.test/sample/telemetry": {
                "name": "registry.example.test/sample/telemetry",
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
