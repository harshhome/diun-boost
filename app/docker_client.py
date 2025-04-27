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


def get_running_containers(client: DockerClient) -> List[Container]:
    """
    Returns a list of running containers
    
    Args:
        client (docker.DockerClient): A Docker client instance.
    
    Returns:
        List[docker.models.containers.Container]: A list of running containers.
    """
    filters = {"status": "running"}
    return client.containers.list(filters=filters)
