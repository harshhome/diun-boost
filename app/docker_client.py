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


def get_container_current_digest(container: Container) -> str | None:
    image_name = None
    image_tags = container.image.tags or []
    if image_tags:
        image_name = image_tags[0].rsplit(":", 1)[0]
    repo_digests = container.image.attrs.get("RepoDigests", [])
    return extract_digest_from_repo_digests(repo_digests, image_name=image_name)
