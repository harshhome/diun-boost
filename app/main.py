from __future__ import annotations

import os
import sys
from argparse import ArgumentParser

from loguru import logger

from app.dashboard_snapshot import (
    build_dashboard_snapshot,
    canonical_image_name,
    write_dashboard_json,
)
from app.diun_client import DiunClientError, load_diun_latest, load_diun_manifests
from app.docker_client import get_docker_client, get_running_containers
from app.yaml_helper import (
    compare_yaml_files,
    create_diun_yaml,
    create_empty_yaml,
    enrich_missing_current_digests,
    load_yaml_entries,
    merge_custom_metadata,
    write_yaml_to_file,
)


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


def run_tasks(
    output_path: str,
    dashboard_json_path: str,
    m_all: bool,
    compose_track: bool,
    diun_container_name: str,
) -> None:
    client = get_docker_client()
    containers = get_running_containers(client, m_all)
    existing_entries = load_yaml_entries(output_path)
    diun_entries = create_diun_yaml(containers, m_all, compose_track)
    diun_entries = merge_custom_metadata(diun_entries, existing_entries)

    latest_by_image = load_diun_latest(client, diun_container_name)
    manifest_lookup = build_manifest_lookup(
        client,
        diun_container_name,
        diun_entries,
        latest_by_image,
    )
    diun_entries = enrich_missing_current_digests(diun_entries, manifest_lookup)
    if compare_yaml_files(output_path, diun_entries):
        write_yaml_to_file(diun_entries, output_path)

    snapshot = build_dashboard_snapshot(
        diun_entries,
        latest_by_image,
        manifest_lookup=manifest_lookup,
    )
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
    args = parser.parse_args()

    logging_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(logging_level)

    monitor_all = os.getenv("WATCHBYDEFAULT", "false").lower() == "true"
    compose_track = os.getenv("DOCKER_COMPOSE_METADATA", "false").lower() == "true"
    output_path = os.getenv("DIUN_YAML_PATH", "/config/config.yml")
    dashboard_json_path = os.getenv("DIUN_DASHBOARD_JSON_PATH", "/config/dashboard.json")
    diun_container_name = os.getenv("DIUN_CONTAINER_NAME", "diun")

    if monitor_all:
        logger.info("🐳 Monitoring all containers by default...")
    else:
        logger.info("🐳 Monitoring containers with DIUN labels i.e. diun.enable=true")

    if compose_track:
        logger.info("🐳 Tracking Docker Compose metadata...")

    logger.info(f"📊 Dashboard snapshot path: {dashboard_json_path}")
    logger.info(f"🐳 DIUN container: {diun_container_name}")

    if args.first_run:
        logger.info("✨ Running initial setup...")
        create_empty_yaml(output_path)
    else:
        logger.info("⏰ Running scheduled cron job...")

    try:
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
