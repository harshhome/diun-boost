import os
import sys
from argparse import ArgumentParser

from loguru import logger

from app.docker_client import get_docker_client, get_running_containers
from app.yaml_helper import (compare_yaml_files, create_diun_yaml,
                             create_empty_yaml, write_yaml_to_file)


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


def run_tasks(output_path: str, m_all: bool, compose_track: bool) -> None:
    client = get_docker_client()
    containers = get_running_containers(client, m_all)
    diun_entries = create_diun_yaml(containers, m_all, compose_track)

    if compare_yaml_files(output_path, diun_entries):
        write_yaml_to_file(diun_entries, output_path)


def main():
    parser = ArgumentParser(description="diun-boost")
    parser.add_argument(
        "--first-run", action="store_true",
        help="Indicates this is the first manual run after container start."
    )
    args = parser.parse_args()

    logging_level = os.getenv("LOG_LEVEL")
    setup_logging(logging_level)

    monitor_all = os.getenv("WATCHBYDEFAULT").lower() == "true"
    compose_track = os.getenv("DOCKER_COMPOSE_METADATA").lower() == "true"
    output_path = os.getenv("DIUN_YAML_PATH")

    if monitor_all:
        logger.info("🐳 Monitoring all containers by default...")
    else:
        logger.info(
            "🐳 Monitoring containers with DIUN labels i.e. diun.enable=true")

    if compose_track:
        logger.info("🐳 Tracking Docker Compose metadata...")

    if args.first_run:
        logger.info("✨ Running initial setup...")
        create_empty_yaml(output_path)
    else:
        logger.info("⏰ Running scheduled cron job...")

    run_tasks(output_path, monitor_all, compose_track)


if __name__ == "__main__":
    main()
