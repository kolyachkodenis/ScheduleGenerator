# Operations and observability

This guide is the operational contract for ScheduleGenerator 0.9.2. The application is a
single Python process backed by one persistent SQLite database and generated artifact folders.

## Runtime environments

Runtime settings use `SG_*` environment variables. Versioned examples live in
`config/environments/`; deployment secrets must be injected by the deployment platform and must
not be committed.

| Variable | Purpose | Production requirement |
| --- | --- | --- |
| `SG_ENVIRONMENT` | `development`, `test`, or `production` | `production` |
| `SG_DATABASE` | SQLite database path | persistent mounted path |
| `SG_HOST` / `SG_PORT` | listen address and port | private address behind TLS proxy |
| `SG_SECURE_COOKIE` | add `Secure` to session cookies | `true` |
| `SG_LOG_LEVEL` | Python log threshold | normally `INFO` |
| `SG_LOG_FORMAT` | `text` or newline-delimited `json` | `json` |
| `SG_METRICS_TOKEN` | bearer token for `/metrics` | required |

Invalid settings stop the process before it starts serving traffic. Development may be launched
directly with `python scripts/run_web_app.py` or in a container with `docker compose up --build`.
Set `SG_ENVIRONMENT=production` before Compose starts to select the production example. Replace
the example metrics token through a secret store.

## Container deployment

The image runs as an unprivileged user, listens on port 8765, and stores mutable data under
`/data`. The Compose definition creates a named volume for this directory. Put an HTTPS reverse
proxy in front of production and forward `X-Request-ID` when one already exists. Do not publish
the application or metrics port directly to an untrusted network.

Before deployment:

1. build the exact revision with `docker build --tag schedule-generator:<revision> .`;
2. run `docker run --rm --entrypoint python schedule-generator:<revision> -m compileall -q /app/src`;
3. configure a persistent `/data` volume and deployment secrets;
4. start one application replica for each SQLite volume;
5. wait for `/health/ready` before directing traffic to the process.

SQLite does not support multiple independently mounted writers. Horizontal scaling requires a
future move to a shared transactional database.

## Health and metrics

- `GET /health/live` confirms that the HTTP process is responsive.
- `GET /health/ready` checks that the database can be opened and the data directory is writable.
- `GET /metrics` returns Prometheus text and requires `Authorization: Bearer <token>` when a token
  is configured.

Metrics include process uptime, HTTP request counts and durations, and completed generation-job
counts and durations by outcome. Identifier-bearing routes are normalized to keep label counts
bounded. Alert on sustained readiness failure, server-error growth, generation failures, and
generation duration exceeding the agreed school-size budget.

JSON log records contain timestamp, level, logger, message, event name, request ID, route, status,
and duration where applicable. Collect stdout in the deployment platform. Treat `request.failed`,
`generation.crashed`, and `health.not_ready` as error-monitoring events. Logs deliberately exclude
credentials, session tokens, request bodies, and school dataset content.

## Backup and recovery

Create a verified backup from the Security screen or `POST /api/admin/backup` before every upgrade.
Copy the resulting database file and the `published` directory to storage outside the application
volume. Periodically test recovery on an isolated volume:

1. stop the application;
2. retain the failed volume without modifying it;
3. place the selected database backup at the configured `SG_DATABASE` path;
4. restore the matching `published` directory;
5. start the same application revision that created the backup;
6. require a successful readiness check, login, dataset read, and published-artifact download;
7. record recovery time and the newest restored audit-event timestamp.

## Upgrade and rollback

For an upgrade, record the current image digest, create an off-volume backup, build and test the new
revision, stop traffic, stop the old process, and start the new image against the existing volume.
SQLite migrations run transactionally when the database opens. Verify readiness, authentication,
one read operation, and the latest audit events before restoring traffic.

Rollback is data-aware: stop the new process, preserve its volume for diagnosis, restore the
pre-upgrade database and artifacts into a clean volume, then start the previous image digest.
Never run an older binary against a database that has already received newer migrations.

## Incident checklist

Capture the image digest, environment name, request ID, UTC time window, health responses, relevant
structured events, and a copy of the database before repair. Revoke exposed sessions or credentials,
restore service using the rollback procedure, and preserve evidence. After recovery, document impact,
root cause, corrective actions, and a regression test or monitor that detects recurrence.
