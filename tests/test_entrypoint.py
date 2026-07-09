from pathlib import Path


ENTRYPOINT = Path("docker/entrypoint.sh")


def test_container_startup_generates_config_before_dashboard_snapshot():
    script = ENTRYPOINT.read_text()

    first_run_config = "/usr/local/bin/python /app/app/main.py --first-run --config-only"
    dashboard_refresh = "/usr/local/bin/python /app/app/main.py --dashboard-only"

    startup_section = script.rsplit(". /etc/cron.d/env-vars", 1)[1].split("cron", 1)[0]

    assert first_run_config in startup_section
    assert dashboard_refresh in startup_section
    assert startup_section.index(first_run_config) < startup_section.index(dashboard_refresh)


def test_entrypoint_defaults_dashboard_commands_path_to_dashboard_yml():
    script = ENTRYPOINT.read_text()

    assert 'echo "export DIUN_DASHBOARD_COMMANDS_PATH=\\"${DIUN_DASHBOARD_COMMANDS_PATH:-/config/dashboard.yml}\\""' in script
    assert 'DIUN_DASHBOARD_COMMANDS_PATH=\"${DIUN_DASHBOARD_COMMANDS_PATH:-${DIUN_YAML_PATH' not in script
