from app.yaml_helper import create_empty_yaml, merge_custom_metadata


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
            "note": "keep",
        }}
    ]
    generated = [
        {"name": "repo:1", "metadata": {"current_tag": "1"}}
    ]

    merged = merge_custom_metadata(generated, existing)

    assert merged[0]["metadata"]["current_tag"] == "1"
    assert merged[0]["metadata"]["note"] == "keep"
    assert "compose_project" not in merged[0]["metadata"]
    assert "compose_service" not in merged[0]["metadata"]


def test_merge_custom_metadata_matches_by_name():
    existing = [{"name": "repo:1", "metadata": {"team": "infra"}}]
    generated = [{"name": "repo:2", "metadata": {"current_tag": "2"}}]

    merged = merge_custom_metadata(generated, existing)

    assert "team" not in merged[0]["metadata"]


def test_create_empty_yaml_does_not_overwrite_existing(tmp_path):
    file_path = tmp_path / "config.yml"

    create_empty_yaml(str(file_path))
    file_path.write_text("keep\n")

    create_empty_yaml(str(file_path))

    assert file_path.read_text() == "keep\n"
