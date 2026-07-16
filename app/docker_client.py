from __future__ import annotations

from typing import List

from docker import from_env
from docker.client import DockerClient
from docker.models.containers import Container


def get_docker_client() -> DockerClient:
    """
    Returns a Docker client instance connected to the host Docker daemon.

    Returns:
        docker.DockerClient: A Docker client instance.
    """
    return from_env()


def get_running_containers(
    client: DockerClient, m_all: bool
) -> List[Container]:
    """
    Returns a list of running containers.

    Args:
        client (docker.DockerClient): A Docker client instance.
        m_all (bool): If True, monitor all containers,
            else only those with the label "diun.enable=true".

    Returns:
        List[docker.models.containers.Container]: A list of running containers.
    """
    filters = {"status": "running"}
    if not m_all:
        filters["label"] = "diun.enable=true"
    containers = client.containers.list(filters=filters)
    containers = [c for c in containers if c.labels.get("diun.enable") != "false"]
    return containers


def get_containers_for_compose_services(
    client: DockerClient,
    scope: set[tuple[str, str]],
) -> List[Container]:
    containers_by_id: dict[str, Container] = {}
    for project, service in scope:
        matches = client.containers.list(
            filters={
                "status": "running",
                "label": [
                    f"com.docker.compose.project={project}",
                    f"com.docker.compose.service={service}",
                ],
            }
        )
        for container in matches:
            if container.labels.get("diun.enable") == "false":
                continue
            container_id = container.id
            if not container_id:
                continue
            containers_by_id[container_id] = container
    return list(containers_by_id.values())


def extract_digest_from_repo_digests(
    repo_digests: list[str], image_name: str | None = None
) -> str | None:
    for repo_digest in repo_digests:
        if "@" not in repo_digest:
            continue
        repo_name, digest = repo_digest.split("@", 1)
        if image_name and repo_name != image_name:
            continue
        return digest

    if image_name:
        for repo_digest in repo_digests:
            if "@" in repo_digest:
                return repo_digest.split("@", 1)[1]
    return None


def canonical_repo_name(name: str) -> str:
    name = name.removeprefix("docker.io/")
    if "/" not in name:
        return f"library/{name}"
    return name


def get_container_repo_digests(
    container: Container, image_name: str | None = None
) -> list[str]:
    """Return all registry manifest/index digests Docker has for an image.

    Docker image IDs are local config digests and are intentionally not used here.
    RepoDigests are registry digests in the same sha256:<hex> form reported by DIUN.
    """
    image = container.image
    if image is None:
        return []

    strict_image_match = bool(image_name)
    image_names = []
    if image_name:
        image_names.append(canonical_repo_name(image_name))
    else:
        for image_tag in image.tags or []:
            if ":" not in image_tag:
                continue
            image_names.append(canonical_repo_name(image_tag.rsplit(":", 1)[0]))
    image_name_set = set(image_names)

    matching_digests: list[str] = []
    fallback_digests: list[str] = []
    seen_matching: set[str] = set()
    seen_fallback: set[str] = set()

    for repo_digest in image.attrs.get("RepoDigests", []) or []:
        if not isinstance(repo_digest, str) or "@" not in repo_digest:
            continue
        repo_name, digest = repo_digest.split("@", 1)
        if not digest:
            continue
        canonical_name = canonical_repo_name(repo_name)
        if not image_name_set or canonical_name in image_name_set:
            if digest not in seen_matching:
                matching_digests.append(digest)
                seen_matching.add(digest)
        elif not strict_image_match and digest not in seen_fallback:
            fallback_digests.append(digest)
            seen_fallback.add(digest)

    if matching_digests:
        return matching_digests
    return fallback_digests


def get_container_current_digest(
    container: Container, image_name: str | None = None
) -> str | None:
    repo_digests = get_container_repo_digests(container, image_name)
    return repo_digests[0] if repo_digests else None
