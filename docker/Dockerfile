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

ENTRYPOINT ["/entrypoint.sh"]