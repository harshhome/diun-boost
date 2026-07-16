from types import SimpleNamespace

import yaml

from app.yaml_helper import (
    create_diun_yaml,
    create_empty_yaml,
    enrich_missing_current_digests,
    merge_custom_metadata,
    parse_repo_digests,
)


def make_container(*, name, image_tag, repo_digests=None, labels=None, config_image=None):
    image = SimpleNamespace(
        tags=[image_tag] if image_tag else [],
        attrs={"RepoDigests": repo_digests or []},
    )
    return SimpleNamespace(
        name=name,
        image=image,
        labels=labels or {},
        attrs={"Config": {"Image": config_image or image_tag or ""}},
    )


def test_merge_custom_metadata_preserves_custom_keys():
    existing = [
        {"name": "repo:1", "metadata": {
            "current_tag": "1",
            "team": "infra",
            "priority": 2,
        }}
    ]
    generated = [
        {"name": "repo:1", "notify_on": ["update"], "metadata": {
            "current_tag": "1",
        }}
    ]

    merged = merge_custom_metadata(generated, existing)

    assert merged[0]["metadata"]["current_tag"] == "1"
    assert merged[0]["metadata"]["team"] == "infra"
    assert merged[0]["metadata"]["priority"] == 2


def test_merge_custom_metadata_ignores_auto_keys():
    existing = [
        {"name": "repo:1", "metadata": {
            "compose_project": "app",
            "compose_service": "web",
            "current_digest": "sha256:old",
            "current_repo_digests": ["sha256:old"],
            "release_notes_url": "https://releases.example.test/component",
            "note": "keep",
        }}
    ]
    generated = [
        {"name": "repo:1", "metadata": {"current_tag": "1"}}
    ]

    merged = merge_custom_metadata(generated, existing)

    assert merged[0]["metadata"]["current_tag"] == "1"
    assert merged[0]["metadata"]["release_notes_url"] == "https://releases.example.test/component"
    assert merged[0]["metadata"]["note"] == "keep"
    assert "compose_project" not in merged[0]["metadata"]
    assert "compose_service" not in merged[0]["metadata"]
    assert "current_digest" not in merged[0]["metadata"]
    assert "current_repo_digests" not in merged[0]["metadata"]


def test_merge_custom_metadata_matches_by_name():
    existing = [{"name": "repo:1", "metadata": {"team": "infra"}}]
    generated = [{"name": "repo:2", "metadata": {"current_tag": "2"}}]

    merged = merge_custom_metadata(generated, existing)

    assert "team" not in merged[0]["metadata"]


def test_merge_custom_metadata_survives_tag_change_for_compose_service():
    existing = [
        {
            "name": "sample-database:17-alpine",
            "metadata": {
                "current_tag": "17-alpine",
                "compose_project": "project-beta",
                "compose_service": "sample-database",
                "release_notes_url": "https://releases.example.test/database",
            },
        }
    ]
    generated = [
        {
            "name": "sample-database:18-alpine",
            "metadata": {
                "current_tag": "18-alpine",
                "compose_project": "project-beta",
                "compose_service": "sample-database",
            },
        }
    ]

    merged = merge_custom_metadata(generated, existing)

    assert (
        merged[0]["metadata"]["release_notes_url"]
        == "https://releases.example.test/database"
    )


def test_merge_custom_metadata_survives_digest_pinned_tag_change():
    existing = [
        {
            "name": "registry.example.test/sample/component:1.0@sha256:old",
            "metadata": {
                "current_tag": "1.0",
                "compose_project": "sample-stack",
                "compose_service": "sample-component",
                "release_notes_url": "https://releases.example.test/component",
            },
        }
    ]
    generated = [
        {
            "name": "registry.example.test/sample/component:2.0@sha256:new",
            "metadata": {
                "current_tag": "2.0",
                "compose_project": "sample-stack",
                "compose_service": "sample-component",
            },
        }
    ]

    merged = merge_custom_metadata(generated, existing)

    assert (
        merged[0]["metadata"]["release_notes_url"]
        == "https://releases.example.test/component"
    )


def test_merge_custom_metadata_does_not_survive_compose_repository_change():
    existing = [
        {
            "name": "registry.example.test/sample/component-a:1.0",
            "metadata": {
                "current_tag": "1.0",
                "compose_project": "sample-stack",
                "compose_service": "sample-component",
                "release_notes_url": "https://releases.example.test/component-a",
            },
        }
    ]
    generated = [
        {
            "name": "registry.example.test/sample/component-b:1.0",
            "metadata": {
                "current_tag": "1.0",
                "compose_project": "sample-stack",
                "compose_service": "sample-component",
            },
        }
    ]

    merged = merge_custom_metadata(generated, existing)

    assert "release_notes_url" not in merged[0]["metadata"]


def test_merge_custom_metadata_survives_enabling_compose_tracking():
    existing = [
        {
            "name": "repo:1",
            "metadata": {
                "current_tag": "1",
                "release_notes_url": "https://releases.example.test/component",
            },
        }
    ]
    generated = [
        {
            "name": "repo:1",
            "metadata": {
                "current_tag": "1",
                "compose_project": "example",
                "compose_service": "app",
            },
        }
    ]

    merged = merge_custom_metadata(generated, existing)

    assert merged[0]["metadata"]["release_notes_url"] == "https://releases.example.test/component"


def test_merge_custom_metadata_survives_compose_migration_with_tag_change():
    existing = [
        {
            "name": "registry.example.test/sample/component:1.0",
            "metadata": {
                "current_tag": "1.0",
                "release_notes_url": "https://releases.example.test/component",
            },
        }
    ]
    generated = [
        {
            "name": "registry.example.test/sample/component:2.0",
            "metadata": {
                "current_tag": "2.0",
                "compose_project": "sample-stack",
                "compose_service": "sample-component",
            },
        }
    ]

    merged = merge_custom_metadata(generated, existing)

    assert (
        merged[0]["metadata"]["release_notes_url"]
        == "https://releases.example.test/component"
    )


def test_merge_custom_metadata_does_not_guess_between_legacy_repository_entries():
    existing = [
        {
            "name": "registry.example.test/sample/component:1.0",
            "metadata": {"current_tag": "1.0", "team": "alpha"},
        },
        {
            "name": "registry.example.test/sample/component:1.1",
            "metadata": {"current_tag": "1.1", "team": "beta"},
        },
    ]
    generated = [
        {
            "name": "registry.example.test/sample/component:2.0",
            "metadata": {
                "current_tag": "2.0",
                "compose_project": "sample-stack",
                "compose_service": "sample-component",
            },
        }
    ]

    merged = merge_custom_metadata(generated, existing)

    assert "team" not in merged[0]["metadata"]


def test_merge_custom_metadata_does_not_copy_one_legacy_entry_to_two_services():
    existing = [
        {
            "name": "registry.example.test/sample/cache:1.0",
            "metadata": {"current_tag": "1.0", "team": "alpha"},
        }
    ]
    generated = [
        {
            "name": "registry.example.test/sample/cache:2.0",
            "metadata": {
                "current_tag": "2.0",
                "compose_project": "sample-stack",
                "compose_service": "cache-primary",
            },
        },
        {
            "name": "registry.example.test/sample/cache:2.0",
            "metadata": {
                "current_tag": "2.0",
                "compose_project": "sample-stack",
                "compose_service": "cache-secondary",
            },
        },
    ]

    merged = merge_custom_metadata(generated, existing)

    assert all("team" not in entry["metadata"] for entry in merged)


def test_merge_custom_metadata_preserves_legacy_entry_for_scaled_service():
    existing = [
        {
            "name": "registry.example.test/sample/cache:1.0",
            "metadata": {"current_tag": "1.0", "team": "alpha"},
        }
    ]
    generated = [
        {
            "name": "registry.example.test/sample/cache:2.0",
            "metadata": {
                "current_tag": "2.0",
                "compose_project": "sample-stack",
                "compose_service": "cache-primary",
            },
        },
        {
            "name": "registry.example.test/sample/cache:2.0",
            "metadata": {
                "current_tag": "2.0",
                "compose_project": "sample-stack",
                "compose_service": "cache-primary",
            },
        },
    ]

    merged = merge_custom_metadata(generated, existing)

    assert all(entry["metadata"]["team"] == "alpha" for entry in merged)


def test_merge_custom_metadata_does_not_cross_compose_service_boundaries():
    existing = [
        {
            "name": "sample-database:18-alpine",
            "metadata": {
                "compose_project": "project-alpha",
                "compose_service": "project-alpha-database",
                "team": "documents",
            },
        },
        {
            "name": "sample-database:18-alpine",
            "metadata": {
                "compose_project": "project-beta",
                "compose_service": "sample-database",
            },
        },
    ]
    generated = [
        {
            "name": "sample-database:18-alpine",
            "metadata": {
                "compose_project": "project-beta",
                "compose_service": "sample-database",
            },
        }
    ]

    merged = merge_custom_metadata(generated, existing)

    assert "team" not in merged[0]["metadata"]


def test_create_diun_yaml_includes_current_digest_metadata():
    container = make_container(
        name="service-gamma",
        image_tag="registry.example.test/sample/service-gamma:4.0.17",
        repo_digests=["registry.example.test/sample/service-gamma@sha256:abcdef123456"],
        labels={
            "com.docker.compose.project": "sample-stack",
            "com.docker.compose.service": "service-gamma",
        },
    )

    entries = create_diun_yaml([container], m_all=True, compose_track=True)

    assert entries[0]["metadata"]["current_tag"] == "4.0.17"
    assert entries[0]["metadata"]["current_digest"] == "sha256:abcdef123456"
    assert entries[0]["metadata"]["current_repo_digests"] == '["sha256:abcdef123456"]'
    assert entries[0]["metadata"]["compose_project"] == "sample-stack"
    assert entries[0]["metadata"]["compose_service"] == "service-gamma"


def test_create_diun_yaml_uses_config_image_when_repo_tags_are_missing():
    container = make_container(
        name="sample-database",
        image_tag=None,
        config_image="sample-database:18.4-alpine",
        repo_digests=["sample-database@sha256:sample-database-digest"],
        labels={
            "com.docker.compose.project": "project-beta",
            "com.docker.compose.service": "sample-database",
        },
    )

    entries = create_diun_yaml([container], m_all=True, compose_track=True)

    assert len(entries) == 1
    assert entries[0]["name"] == "sample-database:18.4-alpine"
    assert entries[0]["metadata"]["current_tag"] == "18.4-alpine"
    assert entries[0]["metadata"]["current_digest"] == "sha256:sample-database-digest"
    assert entries[0]["metadata"]["compose_project"] == "project-beta"
    assert entries[0]["metadata"]["compose_service"] == "sample-database"


def test_create_diun_yaml_skips_config_image_id_when_repo_tags_are_missing():
    container = make_container(
        name="sample-component",
        image_tag=None,
        config_image=f"sha256:{'a' * 64}",
    )

    entries = create_diun_yaml(
        [container], m_all=True, compose_track=True  # type: ignore[arg-type]
    )

    assert entries == []


def test_create_diun_yaml_filters_repo_digests_to_config_image_when_tags_are_missing():
    container = make_container(
        name="sample-database",
        image_tag=None,
        config_image="registry.example.test/sample/database:18.4-alpine",
        repo_digests=[
            "registry.example.test/sample/mirror@sha256:wrong-digest",
            "registry.example.test/sample/database@sha256:expected-digest",
        ],
    )

    entries = create_diun_yaml(
        [container], m_all=True, compose_track=True  # type: ignore[arg-type]
    )

    assert entries[0]["metadata"]["current_digest"] == "sha256:expected-digest"
    assert (
        entries[0]["metadata"]["current_repo_digests"]
        == '["sha256:expected-digest"]'
    )


def test_manifest_enrichment_does_not_guess_missing_docker_digest():
    container = make_container(
        name="sample-channel",
        image_tag=None,
        config_image="registry.example.test/sample/channel:stable",
        repo_digests=[
            "registry.example.test/sample/mirror@sha256:unrelated-digest",
        ],
    )
    entries = create_diun_yaml(
        [container], m_all=True, compose_track=True  # type: ignore[arg-type]
    )
    metadata = entries[0]["metadata"]
    assert "current_digest" not in metadata

    enrich_missing_current_digests(
        entries,
        {
            "registry.example.test/sample/channel": [
                {"tag": "stable", "digest": "sha256:registry-latest"},
            ]
        },
    )

    assert "current_digest" not in metadata
    assert metadata["current_digest_unavailable"] is True


def test_manifest_enrichment_does_not_guess_tagged_image_digest():
    container = make_container(
        name="sample-channel",
        image_tag="registry.example.test/sample/channel:stable",
        repo_digests=[
            "registry.example.test/sample/mirror@sha256:unrelated-digest",
        ],
    )
    entries = create_diun_yaml(
        [container], m_all=True, compose_track=True  # type: ignore[arg-type]
    )
    metadata = entries[0]["metadata"]

    enrich_missing_current_digests(
        entries,
        {
            "registry.example.test/sample/channel": [
                {"tag": "stable", "digest": "sha256:registry-latest"},
            ]
        },
    )

    assert "current_digest" not in metadata
    assert metadata["current_digest_unavailable"] is True


def test_create_diun_yaml_includes_all_current_repo_digests():
    container = make_container(
        name="sample-cache",
        image_tag="sample-cache:8.8.0",
        repo_digests=[
            "sample-cache@sha256:027002f3",
            "docker.io/library/sample-cache@sha256:2838d552",
            "library/sample-cache@sha256:2838d552",
        ],
    )

    entries = create_diun_yaml([container], m_all=True, compose_track=True)

    assert entries[0]["metadata"]["current_digest"] == "sha256:027002f3"
    assert (
        entries[0]["metadata"]["current_repo_digests"]
        == '["sha256:027002f3","sha256:2838d552"]'
    )


def test_parse_repo_digests_parses_json_string():
    assert parse_repo_digests('["sha256:027002f3","sha256:2838d552"]') == [
        "sha256:027002f3",
        "sha256:2838d552",
    ]


def test_parse_repo_digests_filters_non_string_and_empty_items():
    assert parse_repo_digests('["sha256:027002f3", "", null, 3]') == [
        "sha256:027002f3",
    ]


def test_parse_repo_digests_returns_empty_for_missing_empty_invalid_or_non_list_json():
    invalid_values = [
        None,
        "",
        "   ",
        "not json",
        '{"digest":"sha256:027002f3"}',
        '"sha256:027002f3"',
        ["sha256:027002f3"],
    ]

    for value in invalid_values:
        assert parse_repo_digests(value) == []


def test_create_diun_yaml_keeps_notify_on_and_include_tags_as_yaml_lists():
    container = make_container(
        name="sample-cache",
        image_tag="sample-cache:8.8.0",
        repo_digests=["sample-cache@sha256:027002f3"],
    )

    entries = create_diun_yaml([container], m_all=True, compose_track=True)
    loaded = yaml.safe_load(yaml.safe_dump(entries))

    assert loaded[0]["notify_on"] == ["new", "update"]
    assert isinstance(loaded[0]["notify_on"], list)
    assert isinstance(loaded[0]["include_tags"], list)
    assert isinstance(loaded[0]["metadata"]["current_repo_digests"], str)


def test_create_diun_yaml_does_not_emit_dashboard_commands():
    container = make_container(
        name="sample-cache",
        image_tag="sample-cache:8.8.0",
        repo_digests=["sample-cache@sha256:027002f3"],
    )

    dumped = yaml.safe_dump(create_diun_yaml([container], m_all=True, compose_track=True))  # type: ignore[arg-type]

    assert "dashboard:" not in dumped
    assert "commands:" not in dumped


def test_enrich_missing_current_digests_uses_matching_manifest_digest():
    entries = [
        {
            "name": "registry.example.test/sample/update-monitor:1.4.0",
            "metadata": {
                "current_tag": "1.4.0",
                "compose_project": "sample-stack",
                "compose_service": "update-monitor",
            },
        }
    ]
    manifest_lookup = {
        "registry.example.test/sample/update-monitor": [
            {"tag": "1.4.0", "digest": "sha256:manifest-digest"},
            {"tag": "1.3.1", "digest": "sha256:old-digest"},
        ]
    }

    enrich_missing_current_digests(entries, manifest_lookup)

    assert entries[0]["metadata"]["current_digest"] == "sha256:manifest-digest"


def test_enrich_missing_current_digests_does_not_overwrite_docker_digest():
    entries = [
        {
            "name": "sample-cache:8.8.0",
            "metadata": {
                "current_tag": "8.8.0",
                "current_digest": "sha256:docker-digest",
            },
        }
    ]
    manifest_lookup = {
        "library/sample-cache": [
            {"tag": "8.8.0", "digest": "sha256:registry-digest"},
        ]
    }

    enrich_missing_current_digests(entries, manifest_lookup)

    assert entries[0]["metadata"]["current_digest"] == "sha256:docker-digest"


def test_create_empty_yaml_does_not_overwrite_existing(tmp_path):
    file_path = tmp_path / "config.yml"

    create_empty_yaml(str(file_path))
    file_path.write_text("keep\n")

    create_empty_yaml(str(file_path))

    assert file_path.read_text() == "keep\n"
