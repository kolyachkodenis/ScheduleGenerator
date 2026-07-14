"""Local user accounts, sessions, authorization, and security audit events."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from schedule_generator.storage import DatasetStore


ROLES = ("administrator", "scheduler", "reviewer", "reader")
ROLE_PERMISSIONS = {
    "administrator": frozenset({"*"}),
    "scheduler": frozenset(
        {"workspace:read", "data:write", "generation:write", "draft:write"}
    ),
    "reviewer": frozenset({"workspace:read", "publication:write"}),
    "reader": frozenset({"workspace:read"}),
}
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,64}$")
PBKDF2_ITERATIONS = 600_000
SESSION_HOURS = 12
MAX_LOGIN_FAILURES = 5
LOCK_MINUTES = 15


@dataclass(frozen=True)
class User:
    user_id: str
    username: str
    role: str
    enabled: bool
    created_at: str
    last_login_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Session:
    token: str
    expires_at: str
    user: User


@dataclass(frozen=True)
class AuditEvent:
    event_id: int
    actor_user_id: str | None
    actor_username: str | None
    action: str
    target_type: str
    target_id: str | None
    outcome: str
    details: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AuthenticationError(ValueError):
    """Raised when credentials or a session cannot be accepted."""


class AuthorizationError(PermissionError):
    """Raised when an authenticated role lacks a required permission."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def _password_matches(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.urlsafe_b64decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(
            base64.urlsafe_b64encode(digest).decode("ascii"), expected
        )
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


class SecurityService:
    """Persist the minimum identity data needed for a local protected workspace."""

    def __init__(self, store: DatasetStore) -> None:
        self.store = store

    @staticmethod
    def _validate_account(username: str, password: str, role: str) -> None:
        if not USERNAME_PATTERN.fullmatch(username):
            raise ValueError(
                "username must contain 3-64 letters, numbers, dots, dashes, or underscores"
            )
        if role not in ROLES:
            raise ValueError(f"unknown role {role!r}")
        if len(password) < 12:
            raise ValueError("password must contain at least 12 characters")
        if username.casefold() in password.casefold():
            raise ValueError("password must not contain the username")

    @staticmethod
    def _user(row: Any) -> User:
        return User(
            user_id=row["user_id"],
            username=row["username"],
            role=row["role"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            last_login_at=row["last_login_at"],
        )

    def has_users(self) -> bool:
        return bool(self.store.connection.execute("SELECT 1 FROM app_users LIMIT 1").fetchone())

    def bootstrap(self, username: str, password: str) -> User:
        username = username.strip()
        self._validate_account(username, password, "administrator")
        user_id = uuid.uuid4().hex
        with self.store.connection:
            cursor = self.store.connection.execute(
                "INSERT INTO app_users(user_id, username, password_hash, role) "
                "SELECT ?, ?, ?, 'administrator' WHERE NOT EXISTS (SELECT 1 FROM app_users)",
                (user_id, username, _password_hash(password)),
            )
        if cursor.rowcount != 1:
            raise ValueError("workspace has already been initialized")
        user = self.get_user(user_id)
        self.audit(user.user_id, "security.bootstrap", "user", user.user_id)
        return user

    def create_user(self, username: str, password: str, role: str) -> User:
        user = self._create_user(username, password, role)
        return user

    def _create_user(self, username: str, password: str, role: str) -> User:
        username = username.strip()
        self._validate_account(username, password, role)
        user_id = uuid.uuid4().hex
        try:
            with self.store.connection:
                self.store.connection.execute(
                    "INSERT INTO app_users(user_id, username, password_hash, role) "
                    "VALUES (?, ?, ?, ?)",
                    (user_id, username, _password_hash(password), role),
                )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ValueError("username already exists") from error
            raise
        return self.get_user(user_id)

    def get_user(self, user_id: str) -> User:
        row = self.store.connection.execute(
            "SELECT * FROM app_users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            raise KeyError(user_id)
        return self._user(row)

    def list_users(self) -> list[User]:
        rows = self.store.connection.execute(
            "SELECT * FROM app_users ORDER BY username COLLATE NOCASE"
        ).fetchall()
        return [self._user(row) for row in rows]

    def update_user(
        self, user_id: str, *, role: str | None = None, enabled: bool | None = None
    ) -> User:
        current = self.get_user(user_id)
        new_role = role or current.role
        if new_role not in ROLES:
            raise ValueError(f"unknown role {new_role!r}")
        new_enabled = current.enabled if enabled is None else enabled
        if current.role == "administrator" and (not new_enabled or new_role != "administrator"):
            administrators = self.store.connection.execute(
                "SELECT COUNT(*) FROM app_users WHERE role = 'administrator' AND enabled = 1"
            ).fetchone()[0]
            if administrators <= 1:
                raise ValueError("the last enabled administrator cannot be changed")
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE app_users SET role = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE user_id = ?",
                (new_role, int(new_enabled), user_id),
            )
            if not new_enabled:
                self.store.connection.execute(
                    "UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP "
                    "WHERE user_id = ? AND revoked_at IS NULL",
                    (user_id,),
                )
        return self.get_user(user_id)

    def reset_password(self, user_id: str, password: str) -> None:
        user = self.get_user(user_id)
        self._validate_account(user.username, password, user.role)
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE app_users SET password_hash = ?, failed_login_count = 0, "
                "locked_until = NULL, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (_password_hash(password), user_id),
            )
            self.store.connection.execute(
                "UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP "
                "WHERE user_id = ? AND revoked_at IS NULL",
                (user_id,),
            )

    def login(self, username: str, password: str) -> Session:
        row = self.store.connection.execute(
            "SELECT * FROM app_users WHERE username = ? COLLATE NOCASE", (username.strip(),)
        ).fetchone()
        if row is None:
            self.audit(None, "security.login", "session", outcome="denied")
            raise AuthenticationError("invalid username or password")
        user = self._user(row)
        locked = self.store.connection.execute(
            "SELECT locked_until > CURRENT_TIMESTAMP FROM app_users WHERE user_id = ?",
            (user.user_id,),
        ).fetchone()[0]
        if not user.enabled or locked:
            self.audit(user.user_id, "security.login", "session", outcome="denied")
            raise AuthenticationError("account is unavailable")
        if not _password_matches(password, row["password_hash"]):
            failures = int(row["failed_login_count"]) + 1
            with self.store.connection:
                self.store.connection.execute(
                    "UPDATE app_users SET failed_login_count = ?, locked_until = "
                    "CASE WHEN ? >= ? THEN datetime('now', ?) ELSE locked_until END "
                    "WHERE user_id = ?",
                    (
                        failures,
                        failures,
                        MAX_LOGIN_FAILURES,
                        f"+{LOCK_MINUTES} minutes",
                        user.user_id,
                    ),
                )
            self.audit(user.user_id, "security.login", "session", outcome="denied")
            raise AuthenticationError("invalid username or password")
        token = secrets.token_urlsafe(32)
        expires_at = _timestamp(_utc_now() + timedelta(hours=SESSION_HOURS))
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE app_users SET failed_login_count = 0, locked_until = NULL, "
                "last_login_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user.user_id,),
            )
            self.store.connection.execute(
                "DELETE FROM user_sessions WHERE expires_at <= CURRENT_TIMESTAMP OR revoked_at IS NOT NULL"
            )
            self.store.connection.execute(
                "INSERT INTO user_sessions(session_id, user_id, token_hash, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (uuid.uuid4().hex, user.user_id, _token_hash(token), expires_at),
            )
        refreshed = self.get_user(user.user_id)
        self.audit(user.user_id, "security.login", "session")
        return Session(token, expires_at, refreshed)

    def authenticate(self, token: str | None) -> User:
        if not token:
            raise AuthenticationError("authentication required")
        row = self.store.connection.execute(
            "SELECT u.* FROM user_sessions s JOIN app_users u ON u.user_id = s.user_id "
            "WHERE s.token_hash = ? AND s.revoked_at IS NULL "
            "AND s.expires_at > CURRENT_TIMESTAMP AND u.enabled = 1",
            (_token_hash(token),),
        ).fetchone()
        if row is None:
            raise AuthenticationError("session is invalid or expired")
        return self._user(row)

    def logout(self, token: str, actor: User) -> None:
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP "
                "WHERE token_hash = ? AND revoked_at IS NULL",
                (_token_hash(token),),
            )
        self.audit(actor.user_id, "security.logout", "session")

    @staticmethod
    def require(user: User, permission: str) -> None:
        permissions = ROLE_PERMISSIONS[user.role]
        if "*" not in permissions and permission not in permissions:
            raise AuthorizationError(f"role {user.role!r} cannot perform this action")

    def audit(
        self,
        actor_user_id: str | None,
        action: str,
        target_type: str,
        target_id: str | None = None,
        *,
        outcome: str = "success",
        details: dict[str, Any] | None = None,
    ) -> None:
        safe_details = details or {}
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO audit_events(actor_user_id, action, target_type, target_id, "
                "outcome, details_json) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    actor_user_id,
                    action,
                    target_type,
                    target_id,
                    outcome,
                    json.dumps(safe_details, sort_keys=True, separators=(",", ":")),
                ),
            )

    def list_audit_events(self, limit: int = 200) -> list[AuditEvent]:
        if not 1 <= limit <= 1000:
            raise ValueError("audit limit must be between 1 and 1000")
        rows = self.store.connection.execute(
            "SELECT e.*, u.username AS actor_username FROM audit_events e "
            "LEFT JOIN app_users u ON u.user_id = e.actor_user_id "
            "ORDER BY e.event_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            AuditEvent(
                event_id=int(row["event_id"]),
                actor_user_id=row["actor_user_id"],
                actor_username=row["actor_username"],
                action=row["action"],
                target_type=row["target_type"],
                target_id=row["target_id"],
                outcome=row["outcome"],
                details=json.loads(row["details_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
