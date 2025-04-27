import os
import sys
from argparse import ArgumentParser

from loguru import logger


from app.docker_client import get_docker_client, get_running_containers
from app.yaml_helper import create_diun_yaml, write_yaml_to_file, compare_yaml_files


def setup_logging(level="INFO"):
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{level: <8}</level> {message}",
        level=level,
        colorize=True,
    )


def run_tasks(output_path: str) -> None:
    client = get_docker_client()
    containers = get_running_containers(client)
    diun_entries = create_diun_yaml(containers)

    if compare_yaml_files(output_path, diun_entries):
        write_yaml_to_file(diun_entries, output_path)

def main():
    parser = ArgumentParser(description="Generate and update DIUN config file based on running containers.")
    parser.add_argument(
        "--first-run", action="store_true", help="Indicates this is the first manual run after container start."
    )
    args = parser.parse_args()

    logging_level = os.getenv("LOG_LEVEL")
    setup_logging(logging_level)

    output_path = os.getenv("DIUN_YAML_PATH")

    if args.first_run:
        logger.info("Running initial setup (first manual run after container start)...")
    else:
        logger.info("Running scheduled cron job...")

    run_tasks(output_path)


if __name__ == "__main__":
    main()
