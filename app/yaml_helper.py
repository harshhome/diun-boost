from typing import Dict, List

import yaml
from docker.models.containers import Container
from loguru import logger

from app.dashboard_snapshot import canonical_image_name
from app.docker_client import get_container_current_digest
from app.regex_helper import build_tag_regex

AUTO_METADATA_KEYS = {
    "current_tag",
    "current_digest",
    "compose_project",
    "compose_service",
}


def create_diun_yaml(
    containers: List[Container], m_all: bool, compose_track: bool
) -> List[Dict]:
    """
    Create a YAML configuration for DIUN based on running containers.

    Args:
        containers (List[Container]): A list of running Docker containers.
        m_all (bool): Flag to indicate whether to monitor all containers or only those with specific labels.
        compose_track (bool): Flag to indicate whether to track Docker Compose information. If True, include Docker Compose project and service names in the YAML configuration.

    Returns:
        List[Dict]: A list of dictionaries representing the YAML configuration.
    """
    entries = []
    if m_all:
        logger.info(f"🔍 Found {len(containers)} containers")
    else:
        logger.info(f"🔍 Found {len(containers)} containers with DIUN labels")
    
    logger.debug(f"  - {'Container':<20} {'Image':<50}")

    for container in containers:
        image = container.image.tags[0] if container.image.tags else None
        digest = None
        if not image:
            img = container.attrs["Config"]["Image"]
            if "@sha256" in img:
                img, digest = img.split("@sha256:")
                image = img
                digest = f"sha256:{digest}"
            else:
                logger.warning(f"Skipping container {container.name}: no tags")
                continue

        image_name, tag = image.rsplit(":", 1)
        current_digest = get_container_current_digest(container) or digest
        metadata = {"current_tag": tag}
        if current_digest:
            metadata["current_digest"] = current_digest
        entry = {"name": image, "notify_on": ["update"], "metadata": metadata}

        if "com.docker.compose.project" in container.labels and compose_track:
            compose_project = container.labels["com.docker.compose.project"]
            compose_service = container.labels["com.docker.compose.service"]
            entry["metadata"].update({
                "compose_project": compose_project,
                "compose_service": compose_service,
            })
        
        tag_regex = build_tag_regex(tag)
        if tag_regex:
            entry.update({
                "notify_on": ["new", "update"],
                "watch_repo": True,
                "include_tags": [tag_regex],
            })
        
        entries.append(entry)
        if digest:
            logger.debug(f"📌- {container.name:<20} {image_name:<50}")
        else:            
            logger.debug(f"  - {container.name:<20} {image_name:<50}")
    return entries


def load_yaml_entries(file_path: str) -> List[Dict]:
    """
    Load existing DIUN entries from a YAML file.

    Args:
        file_path (str): The path to the YAML file.

    Returns:
        List[Dict]: A list of entries from the YAML file.
    """
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f) or []
    except FileNotFoundError:
        return []

    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data

    logger.warning(
        f"📄 YAML file {file_path} has unexpected structure; "
        "skipping custom metadata merge."
    )
    return []


def extract_custom_metadata(entries: List[Dict]) -> Dict[str, Dict]:
    """
    Extract user-defined metadata from existing YAML entries.

    Args:
        entries (List[Dict]): Existing YAML entries.

    Returns:
        Dict[str, Dict]: Mapping of entry name to custom metadata.
    """
    custom_metadata = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name:
            continue
        metadata = entry.get("metadata")
        if not isinstance(metadata, dict):
            continue
        custom = {
            key: value
            for key, value in metadata.items()
            if key not in AUTO_METADATA_KEYS
        }
        if custom:
            custom_metadata[name] = custom
    return custom_metadata


def merge_custom_metadata(
    entries: List[Dict], existing_entries: List[Dict]
) -> List[Dict]:
    """
    Merge user-defined metadata into generated entries.

    Args:
        entries (List[Dict]): Newly generated DIUN entries.
        existing_entries (List[Dict]): Existing YAML entries.

    Returns:
        List[Dict]: Updated entries with custom metadata preserved.
    """
    custom_by_name = extract_custom_metadata(existing_entries)
    if not custom_by_name:
        return entries

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name:
            continue
        custom = custom_by_name.get(name)
        if not custom:
            continue
        metadata = entry.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        merged_metadata = dict(metadata)
        for key, value in custom.items():
            if key not in merged_metadata:
                merged_metadata[key] = value
        entry["metadata"] = merged_metadata

    return entries


def enrich_missing_current_digests(
    entries: List[Dict], manifest_lookup: Dict[str, List[Dict]]
) -> List[Dict]:
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        metadata = entry.get("metadata")
        if not isinstance(metadata, dict):
            continue
        name = entry.get("name")
        current_tag = metadata.get("current_tag")
        if not isinstance(name, str) or not isinstance(current_tag, str) or ":" not in name:
            continue
        image_name = canonical_image_name(name.split(":", 1)[0])
        manifests = manifest_lookup.get(image_name, [])
        for manifest in manifests:
            if manifest.get("tag") != current_tag:
                continue
            digest = manifest.get("digest")
            if isinstance(digest, str) and digest:
                if metadata.get("current_digest") != digest:
                    metadata["current_digest"] = digest
                break
    return entries


def compare_yaml_files(file: str, yaml_data: List[Dict]) -> bool:
    """
    Compare the existing YAML file with the new YAML data.

    Args:
        file (str): The path to the existing YAML file.
        yaml_data (List[Dict]): The new YAML data to compare against.

    Returns:
        bool: True if the files are different, False otherwise.
    """
    try:
        with open(file, "r") as f:
            existing_data = yaml.safe_load(f) or []
            if isinstance(existing_data, dict):
                existing_data = [existing_data]
            if existing_data != yaml_data:
                logger.info("📄 YAML configuration has changed.")
                return True
            else:
                logger.info("📄 YAML configuration is unchanged.")
                return False
    except FileNotFoundError:
        logger.warning(f"📄 File {file} not found. Creating a new one.")
        return True
    

def create_empty_yaml(file_path: str) -> None:
    """
    Create an empty YAML file if it doesn't exist.

    Args:
        file_path (str): The path to the YAML file.
    """
    try:
        with open(file_path, "x") as file:
            file.write("\n")
        logger.info(f"📄 Empty YAML file created at {file_path}")
    except FileExistsError:
        logger.info(f"📄 YAML file already exists at {file_path}")

    
def write_yaml_to_file(yaml_data: List[Dict], file_path: str) -> None:
    """
    Write the YAML data to a file.

    Args:
        yaml_data (List[Dict]): The YAML data to write.
        file_path (str): The path to the output YAML file.
    """
    with open(file_path, "w") as file:
        for entry in yaml_data:
            yaml.dump([entry], file, default_flow_style=False, sort_keys=False)
            file.write("\n")

    logger.info(f"📝 YAML configuration written to {file_path}")
