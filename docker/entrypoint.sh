#!/bin/sh

set -e

trap 'echo "Received SIGTERM, stopping cron..."; pkill cron; exit 0' TERM INT

export CRON_SANTIZED=$(echo "${CRON_SCHEDULE:-0 */6 * * *}" | tr -d '"'\''')
{
    echo "export DIUN_YAML_PATH=\"${DIUN_YAML_PATH:-/config/config.yml}\""
    echo "export LOG_LEVEL=\"${LOG_LEVEL:-INFO}\""
    echo "export WATCHBYDEFAULT=\"${WATCHBYDEFAULT:-false}\""
    echo "export DOCKER_COMPOSE_METADATA=\"${DOCKER_COMPOSE_METADATA:-false}\""
    echo "export SWARM_MODE=\"${SWARM_MODE:-false}\""
    echo "export PYTHONPATH=/app"
} > /etc/cron.d/env-vars

{
    echo "${CRON_SANTIZED} root /bin/sh -c '. /etc/cron.d/env-vars && /usr/local/bin/python /app/app/main.py >> /proc/1/fd/1 2>&1'"
} > /etc/cron.d/diunboost

chmod 0644 /etc/cron.d/env-vars /etc/cron.d/diunboost

crontab /etc/cron.d/diunboost

. /etc/cron.d/env-vars
/usr/local/bin/python /app/app/main.py --first-run

exec cron -f &
wait $!