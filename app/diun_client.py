from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from docker.client import DockerClient
from loguru import logger

from app.dashboard_snapshot import canonical_image_name


class DiunClientError(RuntimeError):
    pass


def _exec_json(client: DockerClient, container_name: str, command: list[str]) -> dict:
    container = client.containers.get(container_name)
    result = container.exec_run(command)
    if result.exit_code != 0:
        output = result.output.decode("utf-8", errors="replace")
        raise DiunClientError(output.strip() or f"Command failed: {' '.join(command)}")
    output = result.output.decode("utf-8")
    return json.loads(output)


def load_diun_latest(client: DockerClient, container_name: str) -> dict[str, dict]:
    payload = _exec_json(client, container_name, ["diun", "image", "list", "--raw"])
    images = payload.get("images", [])
    if not isinstance(images, Sequence):
        raise DiunClientError("Unexpected DIUN image list payload")

    latest_by_image = {}
    for item in images:
        if not isinstance(item, Mapping):
            continue
        name = item.get("name")
        if not isinstance(name, str):
            continue
        latest_by_image[canonical_image_name(name)] = dict(item)
    logger.info(f"📊 Loaded DIUN latest state for {len(latest_by_image)} images")
    return latest_by_image


def load_diun_manifests(client: DockerClient, container_name: str, image_name: str) -> list[dict]:
    payload = _exec_json(
        client,
        container_name,
        ["diun", "image", "inspect", "--image", image_name, "--raw"],
    )
    image = payload.get("image", {})
    manifests = image.get("manifests", []) if isinstance(image, Mapping) else []
    if not isinstance(manifests, Sequence):
        return []
    return [dict(manifest) for manifest in manifests if isinstance(manifest, Mapping)]
