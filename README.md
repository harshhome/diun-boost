# diun-boost  🚀 🐳 📦

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

Automated [DIUN](https://crazymax.dev/diun/) File Provider YAML Generator for Smarter Docker Image Monitoring

## 📄 General Description

**diun-boost** is a ⚡ **utility tool** ⚡ that dynamically generates a `config.yml` file designed to be used with DIUN's [File Provider](https://crazymax.dev/diun/providers/file/).

> *Important*: diun-boost **only generates** the configuration file (`config.yml`) for DIUN. It does **NOT monitor** container updates itself. DIUN will use the generated file to monitor images! 🔍

This tool simplifies managing large DIUN configurations by automatically creating version-aware watch entries based on your running Docker containers and generate rules that monitors only newer [semver](https://semver.org) tags.

## ✨ Features

### 🧠 Smart Semantic Versioning Support

Version matching is **depth-aware** — only tags with the **same number of components** (segments) are compared:

- ✅ `1.0.0` matches:
  - `1.0.1`, `1.1.0`, `2.0.0`
- ✅ `1.0` matches:
  - `1.1`, `2.0`
- ✅ `1.2.3.4` matches:
  - `1.2.3.5`, `1.2.4.0`, `2.0.0.0`
- ❌ No match to shorter (`1.0`, `1`) or longer (`1.0.0.1`) tags

> 📏 All segments must match in **depth** and be **equal or greater** in value.

### 🏷️ Arbitrary Prefix Support

Supports any prefix (e.g. `v`, `pg`, `nodejs-`, `redis-`), preserving it in all matches:

- Examples:
  - `v1.0.0`, `pg13.5.1`, `nodejs-18.16.0`, `nginx1.25.3`

### 🎯 Suffix-Aware Version Comparison

Suffixes and their versions are independently compared:

- A tag like `v1.2.0.12-build12` will match:
  - `v1.2.0.12-build13` ✅ (same main version, higher suffix version)
  - `v1.2.0.13-build11` ✅ (higher main version, lower suffix version still okay)
- Both the **main version** and **suffix version** are evaluated using depth-aware comparison

### ✅ Non-Semver & Static Tag Matching

Tags that don’t follow semantic versioning — like:
- `latest`, `20240518`, `final-build`, `beta`
- Are matched **exactly**, no version logic is applied.

### 🔍 Test Regex Live
👉 Explore the version matching logic and patterns here: [Regex 101 pattern](https://regex101.com/r/u8sAuo/1)

### 🤏 Minimal Setup:
- Works out of the box using Docker 🐳.

- Supports linux/amd64 and linux/arm64 architectures.

- Small and lightweight image (~50MB) 💾

- No external dependencies required.

- Built using `python:slim` base image with minimal runtime footprint.

## 🛠️ How to Run

### Using `docker run`

```bash
docker run -d \
  --name diun-boost \
  -e DIUN_YAML_PATH="/config/config.yml" \
  -e CRON_SCHEDULE="0 */6 * * *" \
  -e LOG_LEVEL="INFO" \
  -e WATCHBYDEFAULT="false" \
  -e DOCKER_COMPOSE_METADATA="false" \
  -v "$(pwd)/config:/config" \
  -v "/var/run/docker.sock:/var/run/docker.sock" \
  harshbaldwa/diun-boost:1.2.1
```

#### Environment Variables

| Variable        | Description                                                                                                                                           | Default Value        |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------|
| `DIUN_YAML_PATH` | Path to the shared `config.yml` file that DIUN will read.                                                                                               | `/config/config.yml`  |
| `CRON_SCHEDULE`  | Cron schedule expression to control how often the YAML file is regenerated.                                                                           | `0 */6 * * *`          |
| `LOG_LEVEL`      | Logging level for diun-boost. Available options: `DEBUG`, `INFO`, `WARNING`, `ERROR`.                                                                  | `INFO`                |
| `WATCHBYDEFAULT` | Set to `true` to watch **all running containers** by default. <br> However, any container explicitly labeled with `diun.enable=false` will always be excluded. <br> If set to `false`, only containers with the label `diun.enable=true` are watched. | `false`               |
| `DOCKER_COMPOSE_METADATA` | Set to `true` to include Docker Compose metadata in the generated YAML file. <br> This is useful for identifying containers in a multi-container setup as well as for notifications with DIUN. <br> If set to `false`, only the container name will be used. | `false`               |


#### Volume Mounts

| Mount Path               | Description                                           |
|----------------------------|-------------------------------------------------------|
| `/var/run/docker.sock`     | Required for accessing the Docker API from the container. |
| `$(pwd)/config`            | Local directory to store the generated `config.yml` file.  |

### Using Docker Compose

```yaml
services:
  diun-boost:
    container_name: diun-boost
    image: harshbaldwa/diun-boost:1.2.1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./config:/config
    environment:
      - DIUN_YAML_PATH=/config/config.yml
      - CRON_SCHEDULE=0 */6 * * *
      - LOG_LEVEL=INFO
      - WATCHBYDEFAULT=false
      - DOCKER_COMPOSE_METADATA=false
    restart: unless-stopped
```

>**🔥 Tip**: Adjust volume mounts to match your environment.

### 📜 Sample Dummy Code for Diun
Example base `diun.yml` file for DIUN:

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
`docker-compose.yml` file for DIUN and **diun-boost**:

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
      - "TZ=America/New_York"
    restart: unless-stopped
    
  diun-boost:
    container_name: diun-boost
    image: harshbaldwa/diun-boost:1.2.1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./config:/config
    environment:
      - DIUN_YAML_PATH=/config/config.yml
      - CRON_SCHEDULE=0 */6 * * *
      - LOG_LEVEL=INFO
      - WATCHBYDEFAULT=false
      - DOCKER_COMPOSE_METADATA=false
    restart: unless-stopped
```

## ❤️ Support This Project

If you find diun-boost useful, fuel its growth by buying me a coffee!

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/harshbaldwa)

Every coffee helps keep open-source alive and thriving! 🚀

## 📜 License

This project is licensed under the MIT License.

> Made with ❤️ by **Harshvardhan Baldwa** for the homelab and DevOps community!
