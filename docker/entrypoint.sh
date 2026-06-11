#!/bin/sh

set -e

trap 'echo "Received SIGTERM, stopping cron..."; pkill cron || true; exit 0' TERM INT

export CRON_SANTIZED=$(echo "${CRON_SCHEDULE:-0 */6 * * *}" | tr -d '"'\''')
export DASHBOARD_CRON_SANTIZED=$(echo "${DIUN_DASHBOARD_CRON_SCHEDULE:-7 */6 * * *}" | tr -d '"'\''')
{
    echo "export DIUN_YAML_PATH=\"${DIUN_YAML_PATH:-/config/config.yml}\""
    echo "export DIUN_DASHBOARD_JSON_PATH=\"${DIUN_DASHBOARD_JSON_PATH:-/config/dashboard.json}\""
    echo "export DIUN_DASHBOARD_CRON_SCHEDULE=\"${DIUN_DASHBOARD_CRON_SCHEDULE:-7 */6 * * *}\""
    echo "export DIUN_CONTAINER_NAME=\"${DIUN_CONTAINER_NAME:-diun}\""
    echo "export LOG_LEVEL=\"${LOG_LEVEL:-INFO}\""
    echo "export WATCHBYDEFAULT=\"${WATCHBYDEFAULT:-false}\""
    echo "export DOCKER_COMPOSE_METADATA=\"${DOCKER_COMPOSE_METADATA:-false}\""
    echo "export DIUN_DASHBOARD_APP_NAME=\"${DIUN_DASHBOARD_APP_NAME:-DIUN Dashboard}\""
    echo "export PYTHONPATH=/app"
} > /etc/cron.d/env-vars

{
    echo "${CRON_SANTIZED} root /bin/sh -c '. /etc/cron.d/env-vars && /usr/local/bin/python /app/app/main.py --config-only >> /proc/1/fd/1 2>&1'"
    echo "${DASHBOARD_CRON_SANTIZED} root /bin/sh -c '. /etc/cron.d/env-vars && /usr/local/bin/python /app/app/main.py --dashboard-only >> /proc/1/fd/1 2>&1'"
} > /etc/cron.d/diunboost

chmod 0644 /etc/cron.d/env-vars /etc/cron.d/diunboost
crontab /etc/cron.d/diunboost

. /etc/cron.d/env-vars
/usr/local/bin/python /app/app/main.py --first-run --config-only

cron
exec uvicorn app.web:app --host "${DIUN_DASHBOARD_BIND_HOST:-0.0.0.0}" --port "${DIUN_DASHBOARD_BIND_PORT:-8000}"
