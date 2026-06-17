# diun-boost

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/harshhome/diun-boost?style=flat)](https://github.com/harshhome/diun-boost/releases/latest)
[![Docker Image Size (latest by tag)](https://img.shields.io/docker/image-size/harshbaldwa/diun-boost/latest?style=flat)](https://hub.docker.com/r/harshbaldwa/diun-boost)
[![GitHub Stars](https://img.shields.io/github/stars/harshhome/diun-boost?style=flat)](https://github.com/harshhome/diun-boost/stargazers)
[![Docker Pulls](https://img.shields.io/docker/pulls/harshbaldwa/diun-boost?style=flat)](https://hub.docker.com/r/harshbaldwa/diun-boost)
[![Issues](https://img.shields.io/github/issues/harshhome/diun-boost?style=flat)](https://github.com/harshhome/diun-boost/issues)

[![GitHub Repo](https://img.shields.io/badge/GitHub-Repo-black?logo=github&style=flat)](https://github.com/harshhome/diun-boost)
[![DockerHub](https://img.shields.io/badge/DockerHub-Repo-blue?logo=docker&style=flat)](https://hub.docker.com/r/harshbaldwa/diun-boost)
[![Made with Python](https://img.shields.io/badge/Made%20with-Python-yellow?logo=python&style=flat)](https://www.python.org/)

![Unit Tests](https://byob.yarr.is/harshhome/diun-boost/unit-tests)
![Docker Tests](https://byob.yarr.is/harshhome/diun-boost/docker-tests)

Automated DIUN file-provider config generation plus a lightweight dashboard for reviewing pending Docker image updates.

## What diun-boost does

diun-boost is a companion tool for [DIUN](https://crazymax.dev/diun/):

- it scans your running Docker containers
- generates a DIUN file-provider YAML (`config.yml`)
- preserves your custom metadata across regenerations
- builds a dashboard snapshot (`dashboard.json`) from DIUN state
- serves a small web UI for grouped, review-friendly update visibility

Important:
- diun-boost does not replace DIUN
- DIUN still performs the actual update monitoring
- diun-boost prepares DIUN input and presents pending results in a cleaner dashboard

## What's new in the current version

Recent changes added a proper dashboard-oriented workflow:

- built-in FastAPI dashboard UI
- generated `dashboard.json` snapshot alongside `config.yml`
- initial `dashboard.json` generation during container startup
- separate cron schedules for config refreshes and dashboard refreshes
- manual modes for `--config-only` and `--dashboard-only`
- targeted dashboard refreshes for currently pending Compose services
- refresh API endpoint at `POST /api/report/refresh`
- hard refresh API endpoint at `POST /api/report/hard-refresh`
- dashboard filtering now respects generated `include_tags` rules
- dashboard downgrade protection skips latest tags that are numerically older than the current tag
- preserved custom metadata on YAML regeneration
- initial startup now creates the YAML file only if it does not already exist

## Features

### Smart version-aware tag matching

Version matching is depth-aware, so only tags with the same number of version segments are compared.

Examples:
- `1.0.0` matches `1.0.1`, `1.1.0`, `2.0.0`
- `1.0` matches `1.1`, `2.0`
- `1.2.3.4` matches `1.2.3.5`, `1.2.4.0`, `2.0.0.0`
- `1.0.0` does not match `1.0`, `1`, or `1.0.0.1`

### Prefix-aware tags

Arbitrary prefixes are preserved in generated matching rules.

Examples:
- `v1.0.0`
- `pg13.5.1`
- `nodejs-18.16.0`
- `nginx1.25.3`

### Suffix-aware comparisons

Suffixes are handled independently from the main version.

Example:
- `v1.2.0.12-build12` can match `v1.2.0.12-build13`
- `v1.2.0.12-build12` can also match `v1.2.0.13-build11`

### Exact matching for non-semver tags

Non-semver or static tags are matched exactly.

Examples:
- `latest`
- `20240518`
- `final-build`
- `beta`

### Custom metadata preservation

You can add your own keys under `metadata` in generated DIUN entries. diun-boost keeps those keys when it regenerates the file, while still updating its own auto-managed metadata:

- `current_tag`
- `current_digest`
- `compose_project`
- `compose_service`

### Dashboard for pending updates

The dashboard snapshot groups updates by Compose project and shows:

- service name
- update type (`tag_bump` or `digest_refresh`)
- current tag
- latest tag
- summary counts for projects, services, tag bumps, and digest refreshes

Dashboard candidate selection follows the same generated `include_tags` rules used by DIUN. This prevents the dashboard from showing an update candidate that DIUN itself would not watch. It also skips numeric downgrades, so a registry-reported `4.0.0` latest tag will not be reported as pending when the running container is already on `4.0.1`.

### Split refresh pipeline

The container now runs two cron-driven refresh paths:

- config refresh: updates `config.yml`
- dashboard refresh: updates `dashboard.json`

This makes it possible to tune config generation and dashboard refresh cadence separately.

### Dashboard refresh modes

The web UI has two refresh actions:

- `Refresh data` uses `POST /api/report/refresh`. This is the normal fast path: it refreshes only the Compose services currently shown as pending. If there are no pending services, it reuses the existing empty snapshot without calling Docker or DIUN again.
- `Hard refresh` uses `POST /api/report/hard-refresh`. This runs the full dashboard generator, scans containers using the current `WATCHBYDEFAULT` and `DOCKER_COMPOSE_METADATA` settings, refreshes `config.yml` when needed, and writes a fresh `dashboard.json`.

## How it works

At container startup:

1. diun-boost creates the output YAML file if it does not already exist
2. it performs an initial config-only refresh
3. it generates an initial `dashboard.json` snapshot from the saved config and DIUN state
4. it starts cron for scheduled refreshes
5. it starts the dashboard web server with Uvicorn

Scheduled jobs:

- `CRON_SCHEDULE` runs `python /app/app/main.py --config-only`
- `DIUN_DASHBOARD_CRON_SCHEDULE` runs `python /app/app/main.py --dashboard-only`

Manual modes:

- combined refresh: `python /app/app/main.py`
- first run marker: `python /app/app/main.py --first-run`
- config only: `python /app/app/main.py --config-only`
- dashboard only: `python /app/app/main.py --dashboard-only`

## Dashboard requirements

For the dashboard to group updates by project and service, your generated YAML entries need Docker Compose metadata.

Recommended setting:

```env
DOCKER_COMPOSE_METADATA=true
```

If Compose metadata is disabled, diun-boost can still generate `config.yml`, but the grouped dashboard view will have little or no useful project/service data.

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `DIUN_YAML_PATH` | Path to the generated DIUN file-provider YAML. | `/config/config.yml` |
| `DIUN_DASHBOARD_JSON_PATH` | Path to the generated dashboard snapshot JSON. | `/config/dashboard.json` |
| `CRON_SCHEDULE` | Cron expression for regenerating `config.yml`. | `0 */6 * * *` |
| `DIUN_DASHBOARD_CRON_SCHEDULE` | Cron expression for regenerating `dashboard.json`. | `7 */6 * * *` |
| `LOG_LEVEL` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. | `INFO` |
| `WATCHBYDEFAULT` | If `true`, watch all running containers except those explicitly labeled `diun.enable=false`. If `false`, only watch containers labeled `diun.enable=true`. | `false` |
| `DOCKER_COMPOSE_METADATA` | If `true`, include `compose_project` and `compose_service` metadata in generated entries. Strongly recommended for dashboard use. | `false` |
| `DIUN_CONTAINER_NAME` | Name of the running DIUN container that diun-boost queries for latest/manifests data. | `diun` |
| `DIUN_DASHBOARD_APP_NAME` | Display name shown in the dashboard UI. | `DIUN Dashboard` |
| `DIUN_DASHBOARD_BIND_HOST` | Host interface for the dashboard web server. | `0.0.0.0` |
| `DIUN_DASHBOARD_BIND_PORT` | Port for the dashboard web server. | `8000` |

## Docker run

```bash
docker run -d \
  --name diun-boost \
  -p 8000:8000 \
  -e DIUN_YAML_PATH="/config/config.yml" \
  -e DIUN_DASHBOARD_JSON_PATH="/config/dashboard.json" \
  -e CRON_SCHEDULE="0 */6 * * *" \
  -e DIUN_DASHBOARD_CRON_SCHEDULE="7 */6 * * *" \
  -e LOG_LEVEL="INFO" \
  -e WATCHBYDEFAULT="false" \
  -e DOCKER_COMPOSE_METADATA="true" \
  -e DIUN_CONTAINER_NAME="diun" \
  -v "$(pwd)/config:/config" \
  -v "/var/run/docker.sock:/var/run/docker.sock" \
  harshbaldwa/diun-boost:latest
```

Then open:

- dashboard UI: `http://localhost:8000/`
- raw snapshot: `http://localhost:8000/api/report`
- health check: `http://localhost:8000/healthz`

## Docker Compose example

```yaml
services:
  diun:
    container_name: diun
    image: crazymax/diun:latest
    volumes:
      - ./data:/data
      - ./diun.yml:/diun.yml:ro
      - ./config:/config:ro
    environment:
      - TZ=America/New_York
    restart: unless-stopped

  diun-boost:
    container_name: diun-boost
    image: harshbaldwa/diun-boost:latest
    depends_on:
      - diun
    ports:
      - "8000:8000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./config:/config
    environment:
      - DIUN_YAML_PATH=/config/config.yml
      - DIUN_DASHBOARD_JSON_PATH=/config/dashboard.json
      - CRON_SCHEDULE=0 */6 * * *
      - DIUN_DASHBOARD_CRON_SCHEDULE=7 */6 * * *
      - LOG_LEVEL=INFO
      - WATCHBYDEFAULT=false
      - DOCKER_COMPOSE_METADATA=true
      - DIUN_CONTAINER_NAME=diun
      - DIUN_DASHBOARD_APP_NAME=DIUN Dashboard
    restart: unless-stopped
```

## DIUN configuration example

Base `diun.yml` for DIUN:

```yaml
watch:
  workers: 20
  schedule: "2 */6 * * *"

defaults:
  sortTags: semver
  maxTags: 10

providers:
  file:
    filename: /config/config.yml
```

## Example generated entry

```yaml
- name: linuxserver/sonarr:4.0.17
  notify_on:
    - new
    - update
  metadata:
    current_tag: 4.0.17
    current_digest: sha256:...
    compose_project: arr-stack
    compose_service: sonarr
    team: media
    severity: normal
  watch_repo: true
  include_tags:
    - ^((?:5|[6-9]\d*)\.\d+\.\d+|4\.(?:1|[2-9]\d*)\.\d+|4.0\.(?:17|[1-9]\d*))$
```

User-defined metadata like `team` and `severity` is preserved across future regenerations.

## Dashboard API

- `GET /` - HTML dashboard
- `GET /api/report` - return the current `dashboard.json`
- `POST /api/report/refresh` - perform a targeted live refresh and return the refreshed snapshot
- `POST /api/report/hard-refresh` - perform a full live refresh, update `config.yml` if needed, and return the refreshed snapshot
- `GET /healthz` - simple health endpoint

## Notes and behavior

- Containers with `diun.enable=false` are always excluded.
- When `WATCHBYDEFAULT=false`, only containers with `diun.enable=true` are included.
- When `WATCHBYDEFAULT=true`, all running containers are included except explicit opt-outs.
- The dashboard distinguishes between:
  - `tag_bump`: current tag differs from latest tag
  - `digest_refresh`: tag is unchanged but image digest changed
- `dashboard.json` is only rewritten when content changes.
- `config.yml` is only rewritten when content changes.
- If `dashboard.json` already shows no pending services, the targeted refresh path returns that snapshot as-is.
- The dashboard ignores latest tags that do not match an entry's `include_tags` rules.
- The dashboard ignores numeric downgrades when both the current and latest tags contain version numbers.
- Use hard refresh when you want to rescan all eligible containers instead of only refreshing services already shown as pending.

## Local development

Run the test suite from the repository root:

```bash
pytest
```

## Support

If you find diun-boost useful, consider supporting the project:

[Buy Me A Coffee](https://www.buymeacoffee.com/harshbaldwa)

## License

This project is licensed under the MIT License.
