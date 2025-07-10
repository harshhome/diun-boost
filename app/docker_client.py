from typing import List

from docker.client import DockerClient
from docker.models.containers import Container
from docker.models.services import Service

from docker import from_env


def get_docker_client() -> DockerClient:
    """
    Returns a Docker client instance connected to the host Docker daemon.

    Returns:
        docker.DockerClient: A Docker client instance.
    """
    return from_env()


def get_running_containers(
        client: DockerClient, m_all: bool, swarm_mode: bool) -> List[Container | Service]:
    """
    Returns a list of running containers

    Args:
        client (docker.DockerClient): A Docker client instance.
        m_all (bool): If True, monitor all containers,
            else only those with the label "diun.enable=true".
        swarm_mode (bool): If True, query Docker Swarm mode services.

    Returns:
        List[docker.models.containers.Container | docker.models.services.Service]:
            A list of running containers.
    """
    filters = {}
    if not m_all:
        filters["label"] = "diun.enable=true"

    if swarm_mode:
        containers = client.services.list(filters=filters, status=True)
        containers = [c for c in containers if c.attrs.get("ServiceStatus", {}).get("DesiredTasks") > 0]
    else:
        filters["status"] = "running"
        containers = client.containers.list(filters=filters)
        containers = [c for c in containers
                      if c.labels.get("diun.enable") != "false"]

    return containers
