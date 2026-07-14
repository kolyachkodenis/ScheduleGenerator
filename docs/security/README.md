# Users and security

The local workspace requires an account before school data, schedules, publications, or downloads can be accessed. The first browser session creates the initial administrator; bootstrap is permanently disabled after that account exists.

## Roles

| Role | Capabilities |
| --- | --- |
| Administrator | Full access, user administration, audit review, and database backups. |
| Scheduler | Read the workspace, edit school data, generate schedules, and edit drafts. |
| Reviewer | Read the workspace, approve conflict-free versions, and publish or unpublish artifacts. |
| Reader | Read configuration and schedules and download currently published artifacts. |

The final enabled administrator cannot be disabled or demoted. Disabling an account or resetting its password revokes all of its active sessions.

## Credential and session controls

- Passwords must contain at least 12 characters and must not contain the username.
- Passwords are stored as PBKDF2-HMAC-SHA256 hashes with a random salt and 600,000 iterations.
- Five consecutive failures lock an account for 15 minutes.
- Session tokens contain 256 bits of randomness, expire after 12 hours, and are stored only as SHA-256 hashes.
- Browser cookies are `HttpOnly` and `SameSite=Strict`.
- Responses deny framing, MIME sniffing, external referrers, object embedding, and unapproved content sources.

The built-in server is suitable for loopback use. Any non-loopback deployment must terminate TLS before traffic reaches the application, start it with `--secure-cookie`, and ensure credentials and session cookies never cross an unencrypted network.

## Audit trail and data minimization

The audit trail records authentication outcomes, user administration, dataset changes, generation control, draft changes, approvals, publication changes, downloads, and backups. Events contain stable user identifiers, action names, targets, outcomes, timestamps, and narrowly selected operational metadata. Passwords, session tokens, request bodies, network addresses, and unnecessary personal profile fields are not stored.

## Backup and recovery

An administrator can create an online SQLite backup from the security page. Backups are written beneath `backups/` beside the active database and the operation is audited.

Recovery is intentionally offline:

1. Stop the application and retain the damaged database for investigation.
2. Copy the selected backup to a new path; do not overwrite the only backup.
3. Start the application with `--database <restored-path>`.
4. Sign in, verify users, datasets, recent jobs, drafts, publications, and the audit trail.
5. Create a fresh backup after verification.

Backups must be copied to access-controlled storage outside the application directory and tested periodically. Restore is not exposed through HTTP to prevent an online account from replacing the complete security database.

## Baseline review

The implemented baseline covers authentication, server-side authorization, password hashing, session expiry and revocation, login throttling, security headers, auditability, protected downloads, least-data identity records, and recoverable database backups. Remaining deployment risks are TLS termination, host hardening, encrypted off-site backup storage, dependency scanning, and secret rotation; these belong to the operational deployment work.
