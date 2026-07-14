from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from schedule_generator.security import (
    AuthenticationError,
    AuthorizationError,
    SecurityService,
)
from schedule_generator.storage import DatasetStore


class SecurityServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = DatasetStore(Path(self.temporary.name) / "school.db")
        self.security = SecurityService(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_bootstrap_login_logout_and_hashed_storage(self) -> None:
        user = self.security.bootstrap("admin", "Long-Initial-Password!42")
        stored = self.store.connection.execute(
            "SELECT password_hash FROM app_users WHERE user_id = ?", (user.user_id,)
        ).fetchone()[0]
        self.assertTrue(stored.startswith("pbkdf2_sha256$600000$"))
        self.assertNotIn("Long-Initial-Password", stored)

        session = self.security.login("ADMIN", "Long-Initial-Password!42")
        self.assertEqual(self.security.authenticate(session.token).user_id, user.user_id)
        self.assertNotIn(
            session.token,
            self.store.connection.execute("SELECT token_hash FROM user_sessions").fetchone()[0],
        )
        self.security.logout(session.token, user)
        with self.assertRaises(AuthenticationError):
            self.security.authenticate(session.token)

    def test_roles_enforce_permissions(self) -> None:
        self.security.bootstrap("admin", "Long-Initial-Password!42")
        scheduler = self.security.create_user(
            "scheduler", "Distinct-Planning-Key!42", "scheduler"
        )
        reviewer = self.security.create_user(
            "reviewer", "Distinct-Review-Key!42", "reviewer"
        )
        reader = self.security.create_user("reader", "Distinct-Viewing-Key!42", "reader")
        self.security.require(scheduler, "draft:write")
        self.security.require(reviewer, "publication:write")
        self.security.require(reader, "workspace:read")
        with self.assertRaises(AuthorizationError):
            self.security.require(reader, "data:write")

    def test_repeated_failures_lock_account(self) -> None:
        self.security.bootstrap("admin", "Long-Initial-Password!42")
        for _attempt in range(5):
            with self.assertRaises(AuthenticationError):
                self.security.login("admin", "incorrect-password")
        with self.assertRaisesRegex(AuthenticationError, "unavailable"):
            self.security.login("admin", "Long-Initial-Password!42")

    def test_last_enabled_administrator_is_preserved(self) -> None:
        administrator = self.security.bootstrap("admin", "Long-Initial-Password!42")
        with self.assertRaisesRegex(ValueError, "last enabled administrator"):
            self.security.update_user(administrator.user_id, enabled=False)

    def test_audit_events_exclude_credentials(self) -> None:
        administrator = self.security.bootstrap("admin", "Long-Initial-Password!42")
        self.security.audit(
            administrator.user_id,
            "dataset.updated",
            "dataset",
            "school",
            details={"revision": 2},
        )
        event = self.security.list_audit_events()[0]
        self.assertEqual(event.details, {"revision": 2})
        payload = str(event.to_dict()).casefold()
        self.assertNotIn("password", payload)


if __name__ == "__main__":
    unittest.main()
