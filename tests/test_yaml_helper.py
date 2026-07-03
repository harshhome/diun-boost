from types import SimpleNamespace

from app.yaml_helper import (
    create_diun_yaml,
    create_empty_yaml,
    enrich_missing_current_digests,
    merge_custom_metadata,
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
            "release_notes_url": "https://github.com/example/releases",
            "note": "keep",
        }}
    ]
    generated = [
        {"name": "repo:1", "metadata": {"current_tag": "1"}}
    ]

    merged = merge_custom_metadata(generated, existing)

    assert merged[0]["metadata"]["current_tag"] == "1"
    assert merged[0]["metadata"]["release_notes_url"] == "https://github.com/example/releases"
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


def test_create_diun_yaml_includes_current_digest_metadata():
    container = make_container(
        name="sonarr",
        image_tag="linuxserver/sonarr:4.0.17",
        repo_digests=["linuxserver/sonarr@sha256:abcdef123456"],
        labels={
            "com.docker.compose.project": "arr-stack",
            "com.docker.compose.service": "sonarr",
        },
    )

    entries = create_diun_yaml([container], m_all=True, compose_track=True)

    assert entries[0]["metadata"]["current_tag"] == "4.0.17"
    assert entries[0]["metadata"]["current_digest"] == "sha256:abcdef123456"
    assert entries[0]["metadata"]["current_repo_digests"] == ["sha256:abcdef123456"]
    assert entries[0]["metadata"]["compose_project"] == "arr-stack"
    assert entries[0]["metadata"]["compose_service"] == "sonarr"


def test_create_diun_yaml_includes_all_current_repo_digests():
    container = make_container(
        name="redis",
        image_tag="redis:8.8.0",
        repo_digests=[
            "redis@sha256:027002f3",
            "docker.io/library/redis@sha256:2838d552",
            "library/redis@sha256:2838d552",
        ],
    )

    entries = create_diun_yaml([container], m_all=True, compose_track=True)

    assert entries[0]["metadata"]["current_digest"] == "sha256:027002f3"
    assert entries[0]["metadata"]["current_repo_digests"] == [
        "sha256:027002f3",
        "sha256:2838d552",
    ]


def test_enrich_missing_current_digests_uses_matching_manifest_digest():
    entries = [
        {
            "name": "harshbaldwa/diun-boost:1.4.0",
            "metadata": {
                "current_tag": "1.4.0",
                "compose_project": "docker-monitoring",
                "compose_service": "diun-boost",
            },
        }
    ]
    manifest_lookup = {
        "harshbaldwa/diun-boost": [
            {"tag": "1.4.0", "digest": "sha256:manifest-digest"},
            {"tag": "1.3.1", "digest": "sha256:old-digest"},
        ]
    }

    enrich_missing_current_digests(entries, manifest_lookup)

    assert entries[0]["metadata"]["current_digest"] == "sha256:manifest-digest"


def test_enrich_missing_current_digests_does_not_overwrite_docker_digest():
    entries = [
        {
            "name": "redis:8.8.0",
            "metadata": {
                "current_tag": "8.8.0",
                "current_digest": "sha256:docker-digest",
            },
        }
    ]
    manifest_lookup = {
        "library/redis": [
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
