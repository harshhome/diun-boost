from __future__ import annotations

import os
import sys
from argparse import ArgumentParser

from loguru import logger

from app.dashboard_snapshot import (
    build_dashboard_snapshot,
    canonical_image_name,
    extract_pending_service_scope,
    load_dashboard_commands_from_yaml,
    load_dashboard_json,
    write_dashboard_json,
)
from app.diun_client import DiunClientError, load_diun_latest, load_diun_manifests
from app.docker_client import (
    get_containers_for_compose_services,
    get_docker_client,
    get_running_containers,
)
from app.yaml_helper import (
    compare_yaml_files,
    create_diun_yaml,
    create_empty_yaml,
    enrich_missing_current_digests,
    load_yaml_entries,
    merge_custom_metadata,
    write_yaml_to_file,
)

DEFAULT_MONITOR_ALL = os.getenv("WATCHBYDEFAULT", "false").lower() == "true"
DEFAULT_COMPOSE_TRACK = os.getenv("DOCKER_COMPOSE_METADATA", "false").lower() == "true"
DEFAULT_OUTPUT_PATH = os.getenv("DIUN_YAML_PATH", "/config/config.yml")
DEFAULT_DASHBOARD_JSON_PATH = os.getenv("DIUN_DASHBOARD_JSON_PATH", "/config/dashboard.json")
DEFAULT_DASHBOARD_COMMANDS_PATH = os.getenv("DIUN_DASHBOARD_COMMANDS_PATH", "/config/dashboard.yml")
DEFAULT_DIUN_CONTAINER_NAME = os.getenv("DIUN_CONTAINER_NAME", "diun")
DEFAULT_DASHBOARD_CRON_SCHEDULE = os.getenv("DIUN_DASHBOARD_CRON_SCHEDULE", "7 */6 * * *")


def setup_logging(level: str) -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green>"
            "<level>{level: <8}</level> {message}"
        ),
        level=level,
        colorize=True,
    )


def build_manifest_lookup(
    client,
    diun_container_name: str,
    entries: list[dict],
    latest_by_image: dict[str, dict],
) -> dict[str, list[dict]]:
    lookup: dict[str, list[dict]] = {}
    for entry in entries:
        name = entry.get("name")
        if not isinstance(name, str) or ":" not in name:
            continue
        image_name = canonical_image_name(name.split(":", 1)[0])
        if image_name in lookup or image_name not in latest_by_image:
            continue
        try:
            lookup[image_name] = load_diun_manifests(client, diun_container_name, image_name)
        except DiunClientError as exc:
            logger.warning(f"Skipping manifest lookup for {image_name}: {exc}")
    return lookup


def build_snapshot_from_entries(
    entries: list[dict],
    diun_container_name: str,
    dashboard_commands: list[dict] | None = None,
) -> dict[str, object]:
    client = get_docker_client()
    latest_by_image = load_diun_latest(client, diun_container_name)
    manifest_lookup = build_manifest_lookup(
        client,
        diun_container_name,
        entries,
        latest_by_image,
    )
    entries = enrich_missing_current_digests(entries, manifest_lookup)
    return build_dashboard_snapshot(
        entries,
        latest_by_image,
        manifest_lookup=manifest_lookup,
        dashboard_commands=dashboard_commands,
    )


def filter_entries_for_scope(
    entries: list[dict],
    scope: set[tuple[str, str]],
) -> list[dict]:
    filtered: list[dict] = []
    for entry in entries:
        metadata = entry.get("metadata")
        if not isinstance(metadata, dict):
            continue
        project = metadata.get("compose_project")
        service = metadata.get("compose_service")
        if isinstance(project, str) and isinstance(service, str) and (project, service) in scope:
            filtered.append(entry)
    return filtered


def generate_dashboard_snapshot(
    output_path: str,
    m_all: bool,
    compose_track: bool,
    diun_container_name: str,
    *,
    persist_yaml: bool = True,
) -> dict[str, object]:
    client = get_docker_client()
    containers = get_running_containers(client, m_all)
    existing_entries = load_yaml_entries(output_path)
    diun_entries = create_diun_yaml(containers, m_all, compose_track)
    diun_entries = merge_custom_metadata(diun_entries, existing_entries)

    if persist_yaml and compare_yaml_files(output_path, diun_entries):
        write_yaml_to_file(diun_entries, output_path)

    return build_snapshot_from_entries(
        diun_entries,
        diun_container_name,
        load_dashboard_commands_from_yaml(DEFAULT_DASHBOARD_COMMANDS_PATH),
    )


def generate_dashboard_snapshot_from_yaml(
    output_path: str,
    diun_container_name: str,
) -> dict[str, object]:
    return build_snapshot_from_entries(
        load_yaml_entries(output_path),
        diun_container_name,
        load_dashboard_commands_from_yaml(DEFAULT_DASHBOARD_COMMANDS_PATH),
    )


def generate_targeted_dashboard_snapshot(
    output_path: str,
    dashboard_json_path: str,
    *,
    compose_track: bool,
    diun_container_name: str,
) -> dict[str, object]:
    try:
        current_snapshot = load_dashboard_json(dashboard_json_path)
        scope = extract_pending_service_scope(current_snapshot)
    except FileNotFoundError:
        current_snapshot = None
        scope = set()

    if current_snapshot is not None and not scope:
        return current_snapshot

    if not scope:
        return generate_dashboard_snapshot_from_yaml(output_path, diun_container_name)

    existing_entries = load_yaml_entries(output_path)
    client = get_docker_client()
    containers = get_containers_for_compose_services(client, scope)
    scoped_existing_entries = filter_entries_for_scope(existing_entries, scope)
    diun_entries = create_diun_yaml(containers, True, compose_track)
    diun_entries = merge_custom_metadata(diun_entries, scoped_existing_entries)
    return build_snapshot_from_entries(
        diun_entries,
        diun_container_name,
        load_dashboard_commands_from_yaml(DEFAULT_DASHBOARD_COMMANDS_PATH),
    )


def run_tasks(
    output_path: str,
    dashboard_json_path: str,
    m_all: bool,
    compose_track: bool,
    diun_container_name: str,
) -> None:
    snapshot = generate_dashboard_snapshot(
        output_path,
        m_all,
        compose_track,
        diun_container_name,
    )
    changed = write_dashboard_json(snapshot, dashboard_json_path)
    if changed:
        logger.info(f"📊 Dashboard snapshot written to {dashboard_json_path}")
    else:
        logger.info(f"📊 Dashboard snapshot is unchanged at {dashboard_json_path}")


def run_config_only(
    output_path: str,
    m_all: bool,
    compose_track: bool,
) -> None:
    client = get_docker_client()
    containers = get_running_containers(client, m_all)
    existing_entries = load_yaml_entries(output_path)
    diun_entries = create_diun_yaml(containers, m_all, compose_track)
    diun_entries = merge_custom_metadata(diun_entries, existing_entries)

    if compare_yaml_files(output_path, diun_entries):
        write_yaml_to_file(diun_entries, output_path)


def run_dashboard_only(
    output_path: str,
    dashboard_json_path: str,
    diun_container_name: str,
) -> None:
    snapshot = generate_dashboard_snapshot_from_yaml(output_path, diun_container_name)
    changed = write_dashboard_json(snapshot, dashboard_json_path)
    if changed:
        logger.info(f"📊 Dashboard snapshot written to {dashboard_json_path}")
    else:
        logger.info(f"📊 Dashboard snapshot is unchanged at {dashboard_json_path}")


def main():
    parser = ArgumentParser(description="diun-boost")
    parser.add_argument(
        "--first-run",
        action="store_true",
        help="Indicates this is the first manual run after container start.",
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Refresh only the generated DIUN config.yml file.",
    )
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Refresh only dashboard.json from the saved config.yml and DIUN state.",
    )
    args = parser.parse_args()

    logging_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(logging_level)

    monitor_all = DEFAULT_MONITOR_ALL
    compose_track = DEFAULT_COMPOSE_TRACK
    output_path = DEFAULT_OUTPUT_PATH
    dashboard_json_path = DEFAULT_DASHBOARD_JSON_PATH
    diun_container_name = DEFAULT_DIUN_CONTAINER_NAME

    if monitor_all:
        logger.info("🐳 Monitoring all containers by default...")
    else:
        logger.info("🐳 Monitoring containers with DIUN labels i.e. diun.enable=true")

    if compose_track:
        logger.info("🐳 Tracking Docker Compose metadata...")

    logger.info(f"📊 Dashboard snapshot path: {dashboard_json_path}")
    logger.info(f"🕒 Dashboard cron schedule: {DEFAULT_DASHBOARD_CRON_SCHEDULE}")
    logger.info(f"🐳 DIUN container: {diun_container_name}")

    if args.first_run:
        logger.info("✨ Running initial setup...")
        create_empty_yaml(output_path)
    elif args.dashboard_only:
        logger.info("📊 Running dashboard-only refresh...")
    elif args.config_only:
        logger.info("📄 Running config-only refresh...")
    else:
        logger.info("⏰ Running combined refresh...")

    try:
        if args.dashboard_only:
            run_dashboard_only(
                output_path,
                dashboard_json_path,
                diun_container_name,
            )
        elif args.config_only:
            run_config_only(
                output_path,
                monitor_all,
                compose_track,
            )
        else:
            run_tasks(
                output_path,
                dashboard_json_path,
                monitor_all,
                compose_track,
                diun_container_name,
            )
    except DiunClientError as exc:
        logger.error(f"Failed to refresh DIUN dashboard data: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
