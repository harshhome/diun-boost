import re
import yaml

from typing import List, Dict
from docker.models.containers import Container
from loguru import logger

from app.regex_helper import generate_version_regex


def create_diun_yaml(containers: List[Container], m_all: bool) -> List[Dict]:
    """
    Create a YAML configuration for DIUN based on running containers.

    Args:
        containers (List[Container]): A list of running Docker containers.
        m_all (bool): Flag to indicate whether to monitor all containers or only those with specific labels.

    Returns:
        List[Dict]: A list of dictionaries representing the YAML configuration.
    """
    entries = []
    if m_all:
        logger.info(f"🔍 Found {len(containers)} running containers")
    else:
        logger.info(f"🔍 Found {len(containers)} running containers with DIUN labels")

    for container in containers:
        image = container.image.tags[0] if container.image.tags else None
        if not image or ":" not in image:
            continue

        image_name, tag = image.rsplit(":", 1)

        entry = {"name": image, "notify_on": ["update"]}
        if re.match(r"^v?\d+(\.\d+){0,2}$", tag):
            regex = generate_version_regex(tag)
            if regex:
                entry.update({
                    "notify_on": ["new", "update"],
                    "watch_repo": True,
                    "include_tags": [regex],
                })
        entries.append(entry)
        logger.debug(f"  - {container.name}: {image_name} ({tag})")
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
                logger.info("YAML configuration has changed.")
                return True
            else:
                logger.info("YAML configuration is unchanged.")
                return False
    except FileNotFoundError:
        logger.warning(f"File {file} not found. Creating a new one.")
        return True
    

def create_empty_yaml(file_path: str) -> None:
    """
    Create an empty YAML file if it doesn't exist.

    Args:
        file_path (str): The path to the YAML file.
    """
    with open(file_path, "w") as file:
        file.write("\n")
    logger.info(f"Empty YAML file created at {file_path}")

    
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

    logger.info(f"YAML configuration written to {file_path}")
