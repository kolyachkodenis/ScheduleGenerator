# ADR 0008: Use local role-based access control

- Status: Accepted
- Date: 2026-07-14

## Context

School configuration, draft timetables, and published artifacts must not be available to every process that can reach the HTTP listener. The MVP needs clear separation between configuration, scheduling, review, publication, and read-only access without depending on an external identity provider.

## Decision

Store local accounts, password hashes, revocable sessions, and audit events in the existing SQLite database. Enforce administrator, scheduler, reviewer, and reader permissions in the transport layer before invoking application services. Use a one-time first-user bootstrap, PBKDF2 password hashing, short-lived random sessions, temporary login lockout, and protected artifact downloads.

Keep identity records minimal and store no email address, profile, network address, raw password, or raw session token. Make recovery an offline database operation rather than a privileged HTTP endpoint.

## Consequences

- A new workspace requires explicit administrator creation before use.
- Every protected route has a server-side permission boundary independent of the browser UI.
- User accounts and audit history are included in consistent SQLite backups.
- External single sign-on, multi-factor authentication, and organization-wide identity lifecycle integration are deferred.
- Non-loopback deployments still require TLS and operating-system hardening.
