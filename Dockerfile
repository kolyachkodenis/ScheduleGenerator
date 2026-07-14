FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

RUN addgroup --system schedule-generator \
    && adduser --system --ingroup schedule-generator schedule-generator \
    && mkdir -p /data \
    && chown schedule-generator:schedule-generator /data

COPY --chown=schedule-generator:schedule-generator src ./src
COPY --chown=schedule-generator:schedule-generator examples ./examples
COPY --chown=schedule-generator:schedule-generator schemas ./schemas
COPY --chown=schedule-generator:schedule-generator scripts ./scripts

USER schedule-generator
EXPOSE 8765
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health/ready', timeout=3)"]

ENTRYPOINT ["python", "-m", "schedule_generator.web"]
