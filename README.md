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
- repository-aware custom metadata preservation across Compose tag changes, with ambiguity safeguards
- tagged `Config.Image` fallback when Docker has no `RepoTags`, while skipping raw image IDs
- strict repository matching for running-image digests, with explicit `current_digest_unavailable` metadata when Docker cannot prove one
- optional manually configured release-notes links in the dashboard
- configurable Custom Action Buttons that copy rendered dashboard commands/text
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
- `current_digest_unavailable`
- `current_repo_digests`
- `compose_project`
- `compose_service`

Because `release_notes_url` is not auto-managed, it is treated as custom metadata and is preserved across config regeneration. Compose-managed entries are matched by `compose_project`, `compose_service`, and image repository, so custom metadata survives tag changes and remains isolated between services without carrying image-specific links across repository changes. Entries without Compose metadata retain exact image-name matching, with repository-only migration fallback only when the legacy metadata is unambiguous and exactly one generated Compose service uses that repository.

### Manually configured release-notes links

You can manually add `metadata.release_notes_url` to an entry in `/config/config.yml` to show a release-notes link for that service in the dashboard. The URL is preserved across config regeneration because it is custom metadata.

The dashboard shows a `Release notes ↗` link only when `release_notes_url` is configured and starts with `http://` or `https://`. If `release_notes_url` is missing, invalid, or empty, no release-notes link, placeholder, disabled link, or extra text is displayed.

This feature does not auto-discover changelogs or release notes, call the GitHub API, scrape websites, or substitute template variables. It is manually configured and static.

Example:

```yaml
- name: registry.example.test/sample/cache:8.8.0
  notify_on:
    - new
    - update
  metadata:
    current_tag: 8.8.0
    current_digest: sha256:...
    current_repo_digests: '["sha256:..."]'
    compose_project: sample-stack
    compose_service: sample-cache
    release_notes_url: https://releases.example.test/cache
  watch_repo: true
  include_tags:
    - ^8\.8\..+$
```

### Custom Action Buttons

Custom Action Buttons let you define copyable dashboard actions using update details and metadata. This makes diun-boost workflow-aware without making it workflow-specific. You can copy commands for Docker Compose, GitOps, Kubernetes, Ansible, custom scripts, commit messages, release notes, or any other workflow.

Custom Action Buttons are configured separately from DIUN's file-provider config. By default, diun-boost reads action button configuration from:

```text
/config/dashboard.yml
```

This file should contain a `dashboard.commands` section. Do not put `dashboard.commands` in `/config/config.yml`, because `config.yml` is generated for DIUN's file provider and should remain DIUN-compatible. If `/config/dashboard.yml` is missing or empty, no custom action buttons are shown. Override the path with `DIUN_DASHBOARD_COMMANDS_PATH` if needed.

Safety note: diun-boost only renders commands/text and copies the raw result to your clipboard. It does not execute commands, shell-escape values, quote values, or modify command text beyond placeholder replacement.

Supported scopes:

- `service`: renders one copy button per matching service row, beside the release-notes button. Requires `template`.
- `project`: renders one copy button near the project/card header. Use either:
  - `item_template` to render one fragment per matching service and join them with `join_with`, then wrap with optional `prefix` and `suffix`.
  - `template` to render one project-level command. For project-level `template`, only `{project}` is available.

Available icon names are `code`, `copy`, `file-text`, `play`, `refresh`, `rocket`, and `terminal`. Invalid or missing icons fall back to `code`.

`update_types` is a filter, not a scope. If omitted, the command applies to all update types. If set, only matching services are included. This is useful because `tag_bump` and `digest_refresh` often need different workflows: a `tag_bump` usually requires updating the declared image tag first, while a plain `docker compose pull` is usually only appropriate for `digest_refresh` where the tag is unchanged.

Supported built-in placeholders for service commands and project `item_template` commands:

- `{service}`
- `{current}`
- `{latest}`
- `{update_type}`
- `{release_notes_url}`
- `{project}`

All metadata keys are also available to service commands and project `item_template` commands, for example:

- `{compose_project}`
- `{compose_service}`
- `{image_repo}`
- `{current_tag}`
- `{current_digest}`
- `{current_repo_digests}`

If a placeholder is missing, the related button is disabled and its tooltip explains what is missing, for example `Missing placeholder: compose_service`. For project `item_template` commands, a service with missing placeholders is skipped and logged so the remaining services can still produce a copyable command.

Example `/config/dashboard.yml`:

```yaml
dashboard:
  commands:
    # Simple service-level workflow: copy an update note
    - name: update-note
      scope: service
      label: Update note
      icon: file-text
      template: "{service}: {current} → {latest} ({update_type})"

    # Advanced service-level workflow: refresh an unchanged tag/digest
    - name: refresh-digest
      scope: service
      label: Refresh digest
      icon: refresh
      update_types:
        - digest_refresh
      template: "docker compose -p {compose_project} pull {compose_service} && docker compose -p {compose_project} up -d {compose_service}"

    # Simple project-level workflow: copy one summary for all matching services
    - name: project-summary
      scope: project
      label: Project summary
      icon: file-text
      item_template: "{service}: {current} → {latest}"
      join_with: ", "

    # Project-level workflow: copy one command for the matching project
    - name: refresh-project
      scope: project
      label: Refresh project
      icon: rocket
      update_types:
        - digest_refresh
      template: "hc update {project}"

    # Advanced project-level workflow: bump all tag updates, then recreate the compose project
    - name: bump-all-tags
      scope: project
      label: Bump all tags
      icon: rocket
      update_types:
        - tag_bump
      item_template: "yq -i '.services.{compose_service}.image = \"{image_repo}:{latest}\"' docker-compose.yml"
      join_with: " && "
      suffix: " && docker compose -p {compose_project} up -d"
```

Digest refresh project workflow using one command fragment per matching service:

```yaml
dashboard:
  commands:
    - name: refresh-all-digests
      scope: project
      label: Refresh all digests
      icon: refresh
      update_types:
        - digest_refresh
      item_template: "docker compose -p {compose_project} pull {compose_service}"
      join_with: " && "
      suffix: " && docker compose -p {compose_project} up -d"
```

### Dashboard for pending updates

The dashboard snapshot groups updates by Compose project and shows:

- service name
- update type (`tag_bump` or `digest_refresh`)
- current tag
- latest tag
- optional `Release notes ↗` link when `metadata.release_notes_url` is configured
- optional Custom Action Buttons from `dashboard.commands`
- service metadata under each service's nested `metadata` object
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
| `DIUN_DASHBOARD_COMMANDS_PATH` | Path to `dashboard.yml` containing `dashboard.commands` for Custom Action Buttons. | `/config/dashboard.yml` |
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
  -e DIUN_DASHBOARD_COMMANDS_PATH="/config/dashboard.yml" \
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
      - DIUN_DASHBOARD_COMMANDS_PATH=/config/dashboard.yml
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
- name: registry.example.test/sample/service-gamma:4.0.17
  notify_on:
    - new
    - update
  metadata:
    current_tag: 4.0.17
    current_digest: sha256:...
    current_repo_digests: '["sha256:..."]'
    compose_project: sample-stack
    compose_service: service-gamma
    release_notes_url: https://releases.example.test/service-gamma
    team: platform
    severity: normal
  watch_repo: true
  include_tags:
    - ^((?:5|[6-9]\d*)\.\d+\.\d+|4\.(?:1|[2-9]\d*)\.\d+|4.0\.(?:17|[1-9]\d*))$
```

User-defined metadata like `team`, `severity`, and `release_notes_url` is preserved across future regenerations. Compose services are matched by project, service, and image repository; legacy entries can also migrate across a tag change when their repository metadata is unambiguous and exactly one generated Compose service uses that repository.

## Dashboard API

- `GET /` - HTML dashboard
- `GET /api/report` - return the current `dashboard.json`, including top-level `commands` and nested service `metadata`
- `POST /api/report/refresh` - perform a targeted live refresh and return the refreshed snapshot
- `POST /api/report/hard-refresh` - perform a full live refresh, update `config.yml` if needed, and return the refreshed snapshot
- `GET /healthz` - simple health endpoint

## Notes and behavior

- Containers with `diun.enable=false` are always excluded.
- When `WATCHBYDEFAULT=false`, only containers with `diun.enable=true` are included.
- When `WATCHBYDEFAULT=true`, all running containers are included except explicit opt-outs.
- If Docker reports no `RepoTags` for a running image, diun-boost falls back to the container's original `Config.Image` when it contains an explicit tag.
- Registry digests are filtered to that configured repository. If Docker cannot provide a matching digest, the entry is marked `current_digest_unavailable` and registry data is not substituted as the running digest.
- The dashboard distinguishes between:
  - `tag_bump`: current tag differs from latest tag
  - `digest_refresh`: tag is unchanged and DIUN's latest registry digest is not present in Docker's current repo digests
- `dashboard.json` is only rewritten when content changes.
- `config.yml` is only rewritten when content changes.
- If `dashboard.json` already shows no pending services, the targeted refresh path returns that snapshot as-is.
- The dashboard ignores latest tags that do not match an entry's `include_tags` rules.
- The dashboard ignores numeric downgrades when both the current and latest tags contain version numbers.
- Custom Action Buttons copy rendered raw text to the clipboard only; diun-boost never executes configured commands.
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
