from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any
from datetime import datetime, timezone
from pathlib import Path

import yaml


def canonical_image_name(name: str) -> str:
    name = name.removeprefix("docker.io/")
    if "/" not in name:
        return f"library/{name}"
    return name


def version_key(tag: str | None):
    if not isinstance(tag, str):
        return None
    nums = re.findall(r"\d+", tag)
    if not nums:
        return None
    return tuple(int(n) for n in nums)


def matches_include_tags(tag: str, include_tags: Sequence[str] | None) -> bool:
    patterns = [re.compile(pattern) for pattern in (include_tags or [])]
    return not patterns or any(pattern.match(tag) for pattern in patterns)


def select_latest_manifest(
    image_name: str,
    include_tags: Sequence[str] | None,
    current_tag: str,
    manifest_lookup: Mapping[str, Sequence[Mapping[str, object]]] | None,
):
    if not manifest_lookup:
        return None
    manifests = manifest_lookup.get(image_name) or []
    patterns = [re.compile(pattern) for pattern in (include_tags or [])]
    filtered = []
    for manifest in manifests:
        tag = manifest.get("tag")
        if patterns and not any(pattern.match(tag or "") for pattern in patterns):
            continue
        filtered.append(manifest)

    if not filtered:
        return None

    current_manifest = next((m for m in filtered if m.get("tag") == current_tag), None)
    current_created = current_manifest.get("created") if current_manifest else None
    if current_created:
        newer_or_equal = [m for m in filtered if (m.get("created") or "") >= current_created]
        if newer_or_equal:
            filtered = newer_or_equal

    return max(
        filtered,
        key=lambda manifest: (
            version_key(manifest.get("tag")) is not None,
            version_key(manifest.get("tag")) or (),
            manifest.get("created") or "",
        ),
    )


def build_dashboard_snapshot(
    config_entries: Sequence[Mapping[str, object]],
    latest_by_image: Mapping[str, Mapping[str, object]],
    manifest_lookup: Mapping[str, Sequence[Mapping[str, object]]] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    tag_bumps = 0
    digest_refreshes = 0

    for entry in config_entries:
        metadata = entry.get("metadata")
        if not isinstance(metadata, Mapping):
            continue

        project = metadata.get("compose_project")
        service = metadata.get("compose_service")
        current_tag = metadata.get("current_tag")
        current_digest = metadata.get("current_digest")
        raw_current_repo_digests = metadata.get("current_repo_digests")
        current_repo_digests = (
            [digest for digest in raw_current_repo_digests if isinstance(digest, str) and digest]
            if isinstance(raw_current_repo_digests, Sequence)
            and not isinstance(raw_current_repo_digests, (str, bytes))
            else []
        )
        full_image = entry.get("name")
        if not all(isinstance(value, str) and value for value in [project, service, current_tag, full_image]):
            continue

        image_name = canonical_image_name(full_image.split(":", 1)[0])
        latest_record = latest_by_image.get(image_name)
        if not isinstance(latest_record, Mapping):
            continue

        raw_include_tags = entry.get("include_tags")
        include_tags = (
            [pattern for pattern in raw_include_tags if isinstance(pattern, str)]
            if isinstance(raw_include_tags, Sequence)
            and not isinstance(raw_include_tags, (str, bytes))
            else None
        )
        latest = select_latest_manifest(
            image_name,
            include_tags,
            current_tag,
            manifest_lookup,
        )
        if not latest:
            latest = latest_record.get("latest")
        if not isinstance(latest, Mapping):
            continue

        latest_tag = latest.get("tag")
        latest_digest = latest.get("digest")
        if not isinstance(latest_tag, str) or not latest_tag:
            continue
        if not matches_include_tags(latest_tag, include_tags):
            continue
        current_version = version_key(current_tag)
        latest_version = version_key(latest_tag)
        if current_version is not None and latest_version is not None and latest_version < current_version:
            continue
        if not isinstance(latest_digest, str) or not latest_digest:
            continue

        update_type = None
        if current_tag != latest_tag:
            update_type = "tag_bump"
            tag_bumps += 1
        elif latest_digest in current_repo_digests:
            continue
        elif isinstance(current_digest, str) and current_digest and current_digest != latest_digest:
            update_type = "digest_refresh"
            digest_refreshes += 1
        else:
            continue

        grouped[project].append(
            {
                "service": service,
                "update_type": update_type,
                "current": current_tag,
                "latest": latest_tag,
            }
        )

    projects = [
        {"name": project, "services": sorted(services, key=lambda item: item["service"])}
        for project, services in sorted(grouped.items())
    ]
    service_count = sum(len(project["services"]) for project in projects)
    summary = {
        "projects": len(projects),
        "services": service_count,
        "tag_bumps": tag_bumps,
        "digest_refreshes": digest_refreshes,
    }

    return {
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "projects": projects,
        "summary": summary,
    }


def load_yaml_entries(file_path: str | Path) -> list[dict]:
    path = Path(file_path)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


def write_dashboard_json(snapshot: Mapping[str, object], file_path: str | Path) -> bool:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, indent=2, sort_keys=False)
    if path.exists() and path.read_text() == payload + "\n":
        return False
    path.write_text(payload + "\n")
    return True


def load_dashboard_json(file_path: str | Path) -> dict[str, object]:
    path = Path(file_path)
    return json.loads(path.read_text())


def extract_pending_service_scope(snapshot: Mapping[str, Any] | None) -> set[tuple[str, str]]:
    if not isinstance(snapshot, Mapping):
        return set()

    scope: set[tuple[str, str]] = set()
    projects = snapshot.get("projects")
    if not isinstance(projects, Sequence):
        return scope

    for project in projects:
        if not isinstance(project, Mapping):
            continue
        project_name = project.get("name")
        services = project.get("services")
        if not isinstance(project_name, str) or not isinstance(services, Sequence):
            continue
        for service in services:
            if not isinstance(service, Mapping):
                continue
            service_name = service.get("service")
            if isinstance(service_name, str) and service_name:
                scope.add((project_name, service_name))
    return scope
