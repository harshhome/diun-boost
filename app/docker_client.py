from typing import List

from loguru import logger

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


def get_running_containers(client: DockerClient, m_all: bool) -> List[Container]:
    """
    Returns a list of running containers
    
    Args:
        client (docker.DockerClient): A Docker client instance.
        m_all (bool): If True, monitor all containers, else only those with the label "diun.enable=true".
    
    Returns:
        List[docker.models.containers.Container]: A list of running containers.
    """
    filters = {"status": "running"}
    if not m_all:
        filters["label"] = "diun.enable=true"
    containers = client.containers.list(filters=filters)
    containers = [c for c in containers if c.labels.get("diun.enable") != "false"]
    return containers
