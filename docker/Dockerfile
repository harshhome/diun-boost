FROM python:3.13.3-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    cron && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app

LABEL org.opencontainers.image.title="diun-boost"
LABEL org.opencontainers.image.description="Generate config.yml automatically from running containers"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="Harshvardhan Baldwa docker@harshbaldwa.com"

ENTRYPOINT ["/entrypoint.sh"]