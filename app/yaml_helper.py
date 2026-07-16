import json
import re
from typing import Dict, List

import yaml
from docker.models.containers import Container
from loguru import logger

from app.docker_client import canonical_repo_name, get_container_repo_digests
from app.regex_helper import build_tag_regex

AUTO_METADATA_KEYS = {
    "current_tag",
    "current_digest",
    "current_digest_unavailable",
    "current_repo_digests",
    "compose_project",
    "compose_service",
}


def parse_repo_digests(value) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str) and item]


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
            configured_image = container.attrs["Config"]["Image"]
            if not isinstance(configured_image, str) or re.fullmatch(
                r"sha256:[0-9a-fA-F]{64}", configured_image
            ):
                logger.warning(
                    f"Skipping container {container.name}: Config.Image is an image ID"
                )
                continue
            if "@sha256" in configured_image:
                configured_image, digest = configured_image.split("@sha256:")
                image = configured_image
                digest = f"sha256:{digest}"
            elif ":" in configured_image.rsplit("/", 1)[-1]:
                # Docker can lose RepoTags after an image update/prune while the
                # container still retains the exact tagged reference it started with.
                image = configured_image
            else:
                logger.warning(f"Skipping container {container.name}: no tags")
                continue

        image_name, tag = image.rsplit(":", 1)
        current_repo_digests = get_container_repo_digests(container, image_name)
        current_digest = current_repo_digests[0] if current_repo_digests else digest
        metadata: Dict[str, object] = {"current_tag": tag}
        if current_digest:
            metadata["current_digest"] = current_digest
        else:
            metadata["current_digest_unavailable"] = True
        if current_repo_digests:
            metadata["current_repo_digests"] = json.dumps(
                current_repo_digests,
                separators=(",", ":"),
            )
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


def compose_service_identity(entry: Dict) -> tuple[str, str] | None:
    """Return the stable Compose project/service identity for an entry."""
    if not isinstance(entry, dict):
        return None
    metadata = entry.get("metadata")
    if not isinstance(metadata, dict):
        return None
    project = metadata.get("compose_project")
    service = metadata.get("compose_service")
    if not isinstance(project, str) or not project:
        return None
    if not isinstance(service, str) or not service:
        return None
    return project, service


def image_repository_name(image_reference: str) -> str | None:
    """Return a canonical repository name without a tag or digest."""
    if not image_reference:
        return None
    repository = image_reference.split("@", 1)[0]
    if ":" in repository.rsplit("/", 1)[-1]:
        repository = repository.rsplit(":", 1)[0]
    return canonical_repo_name(repository) if repository else None


def extract_custom_metadata_by_compose_service(
    entries: List[Dict],
) -> Dict[tuple[str, str, str], Dict]:
    """Extract custom metadata keyed by Compose identity and image repository."""
    custom_metadata = {}
    for entry in entries:
        identity = compose_service_identity(entry)
        if identity is None:
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        repository = image_repository_name(name)
        if repository is None:
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
            custom_metadata[(*identity, repository)] = custom
    return custom_metadata


def extract_legacy_custom_metadata_by_name(entries: List[Dict]) -> Dict[str, Dict]:
    """Extract custom metadata from entries that predate Compose metadata."""
    custom_metadata = {}
    for entry in entries:
        if not isinstance(entry, dict) or compose_service_identity(entry) is not None:
            continue
        name = entry.get("name")
        metadata = entry.get("metadata")
        if not name or not isinstance(metadata, dict):
            continue
        custom = {
            key: value
            for key, value in metadata.items()
            if key not in AUTO_METADATA_KEYS
        }
        if custom:
            custom_metadata[name] = custom
    return custom_metadata


def extract_unambiguous_legacy_custom_metadata_by_repository(
    entries: List[Dict],
) -> Dict[str, Dict]:
    """Index legacy custom metadata by repository only when migration is safe."""
    grouped: Dict[str, List[Dict]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or compose_service_identity(entry) is not None:
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        repository = image_repository_name(name)
        if repository is None:
            continue
        metadata = entry.get("metadata")
        custom = (
            {
                key: value
                for key, value in metadata.items()
                if key not in AUTO_METADATA_KEYS
            }
            if isinstance(metadata, dict)
            else {}
        )
        grouped.setdefault(repository, []).append(custom)

    return {
        repository: candidates[0]
        for repository, candidates in grouped.items()
        if candidates[0]
        and all(candidate == candidates[0] for candidate in candidates[1:])
    }


def count_compose_services_by_repository(entries: List[Dict]) -> Dict[str, int]:
    """Count unique generated Compose services per image repository."""
    identities_by_repository: Dict[str, set[tuple[str, str]]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identity = compose_service_identity(entry)
        if identity is None:
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        repository = image_repository_name(name)
        if repository is not None:
            identities_by_repository.setdefault(repository, set()).add(identity)
    return {
        repository: len(identities)
        for repository, identities in identities_by_repository.items()
    }


def merge_custom_metadata(
    entries: List[Dict], existing_entries: List[Dict]
) -> List[Dict]:
    """
    Merge user-defined metadata into generated entries.

    Compose project/service identity plus image repository is preferred because it
    remains stable when a tag changes, distinguishes services sharing an image, and
    avoids carrying image-specific metadata across repository changes. Entries without
    Compose metadata retain the legacy exact-name matching behavior.

    Args:
        entries (List[Dict]): Newly generated DIUN entries.
        existing_entries (List[Dict]): Existing YAML entries.

    Returns:
        List[Dict]: Updated entries with custom metadata preserved.
    """
    custom_by_service = extract_custom_metadata_by_compose_service(existing_entries)
    legacy_custom_by_name = extract_legacy_custom_metadata_by_name(existing_entries)
    legacy_custom_by_repository = (
        extract_unambiguous_legacy_custom_metadata_by_repository(existing_entries)
    )
    generated_compose_repository_counts = count_compose_services_by_repository(entries)
    custom_by_name = extract_custom_metadata(existing_entries)
    if (
        not custom_by_service
        and not legacy_custom_by_name
        and not legacy_custom_by_repository
        and not custom_by_name
    ):
        return entries

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name:
            continue
        identity = compose_service_identity(entry)
        if identity is not None:
            repository = image_repository_name(name)
            custom = (
                custom_by_service.get((*identity, repository))
                if repository is not None
                else None
            )
            if custom is None:
                custom = legacy_custom_by_name.get(name)
            if custom is None:
                if (
                    repository is not None
                    and generated_compose_repository_counts.get(repository) == 1
                ):
                    custom = legacy_custom_by_repository.get(repository)
        else:
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
    from app.dashboard_snapshot import canonical_image_name

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
        if metadata.get("current_digest_unavailable") is True:
            continue
        image_name = canonical_image_name(name.split(":", 1)[0])
        manifests = manifest_lookup.get(image_name, [])
        for manifest in manifests:
            if manifest.get("tag") != current_tag:
                continue
            if metadata.get("current_digest"):
                break
            digest = manifest.get("digest")
            if isinstance(digest, str) and digest:
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
