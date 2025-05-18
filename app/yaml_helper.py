from typing import Dict, List

import yaml
from docker.models.containers import Container
from loguru import logger

from app.regex_helper import build_tag_regex


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
            else:
                logger.warning(f"Skipping container {container.name}: no tags")
                continue

        image_name, tag = image.rsplit(":", 1)
        entry = {"name": image, "notify_on": ["update"], "metadata": {
            "current_tag": tag}}
        
        if "com.docker.compose.project" in container.labels and compose_track:
            compose_project = container.labels["com.docker.compose.project"]
            compose_service = container.labels["com.docker.compose.service"]
            entry.update({
                "metadata": {
                    "current_tag": tag,
                    "compose_project": compose_project,
                    "compose_service": compose_service
                }
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
    with open(file_path, "w") as file:
        file.write("\n")
    logger.info(f"📄 Empty YAML file created at {file_path}")

    
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
