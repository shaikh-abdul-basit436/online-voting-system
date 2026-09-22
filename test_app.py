"""Functional tests for the main voter and admin workflows."""
import os
import sqlite3
import tempfile
import unittest

from app import create_app


class VotingSystemTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": self.db_path})
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def csrf(self):
        self.client.get("/")
        with self.client.session_transaction() as current_session:
            return current_session["csrf_token"]

    def post(self, url, data=None, follow=True):
        form = dict(data or {})
        form["csrf_token"] = self.csrf()
        return self.client.post(url, data=form, follow_redirects=follow)

    def voter_login(self, username="voter1", password="Voter@123"):
        return self.post("/login", {"username": username, "password": password})

    def admin_login(self, username="admin", password="Admin@123"):
        return self.post("/admin/login", {"username": username, "password": password})

    def test_home_and_custom_404_load(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.client.get("/missing-page")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Page not found", response.data)

    def test_custom_500_page(self):
        self.app.config["PROPAGATE_EXCEPTIONS"] = False

        @self.app.route("/test-internal-error")
        def test_internal_error():
            raise RuntimeError("test error")

        response = self.client.get("/test-internal-error")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Something went wrong", response.data)

    def test_registration_and_duplicate_username(self):
        data = {"full_name": "Maya Patel", "username": "maya_01", "password": "Password9", "confirm_password": "Password9"}
        response = self.post("/register", data)
        self.assertIn(b"Registration successful", response.data)
        duplicate = self.post("/register", data)
        self.assertIn(b"already registered", duplicate.data)
        database = sqlite3.connect(self.db_path)
        password = database.execute("SELECT password FROM voters WHERE username='maya_01'").fetchone()[0]
        self.assertNotEqual(password, "Password9")
        database.close()

    def test_login_wrong_password_and_logout(self):
        wrong = self.voter_login(password="wrong-password")
        self.assertIn(b"Invalid voter", wrong.data)
        correct = self.voter_login()
        self.assertIn(b"Welcome, Neha Verma", correct.data)
        logged_out = self.post("/logout")
        self.assertIn(b"logged out", logged_out.data)
        self.assertIn(b"Online Voting System", self.client.get("/").data)

    def test_candidate_list_and_empty_vote_rejected(self):
        self.voter_login()
        self.assertIn(b"Aarav Sharma", self.client.get("/candidates").data)
        response = self.post("/vote", {})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Select a valid candidate", response.data)

    def test_successful_vote_is_atomic_and_cannot_repeat(self):
        self.voter_login()
        first = self.post("/vote", {"candidate_id": "1"})
        self.assertIn(b"Vote Submitted Successfully", first.data)
        database = sqlite3.connect(self.db_path)
        self.assertEqual(database.execute("SELECT has_voted FROM voters WHERE username='voter1'").fetchone()[0], 1)
        self.assertEqual(database.execute("SELECT COUNT(*) FROM votes WHERE voter_id=1").fetchone()[0], 1)
        second = self.post("/vote", {"candidate_id": "2"})
        self.assertIn(b"Vote Already Submitted", second.data)
        self.client.get("/vote/success")
        self.assertEqual(database.execute("SELECT COUNT(*) FROM votes WHERE voter_id=1").fetchone()[0], 1)
        database.close()

    def test_modified_candidate_id_is_rejected(self):
        self.voter_login()
        response = self.post("/vote", {"candidate_id": "9999"})
        self.assertEqual(response.status_code, 400)
        database = sqlite3.connect(self.db_path)
        self.assertEqual(database.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 0)
        database.close()

    def test_login_protection_and_role_separation(self):
        self.assertEqual(self.client.get("/voter/dashboard").status_code, 302)
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 302)
        self.admin_login()
        self.assertEqual(self.client.get("/vote").status_code, 302)
        self.post("/logout")
        self.voter_login()
        self.assertEqual(self.client.get("/admin/results").status_code, 302)

    def test_admin_login_dashboard_and_voter_privacy(self):
        wrong = self.admin_login(password="wrong-password")
        self.assertIn(b"Invalid administrator", wrong.data)
        dashboard = self.admin_login()
        self.assertIn(b"Election overview", dashboard.data)
        voters = self.client.get("/admin/voters")
        self.assertIn(b"Neha Verma", voters.data)
        self.assertNotIn(b"Voter@123", voters.data)

    def test_admin_candidate_add_edit_delete(self):
        self.admin_login()
        added = self.post("/admin/candidates", {"name": "Ishaan Rao", "party": "Campus Forum", "symbol": "Pen", "description": "Improves student feedback."})
        self.assertIn(b"Candidate added successfully", added.data)
        database = sqlite3.connect(self.db_path)
        candidate_id = database.execute("SELECT id FROM candidates WHERE name='Ishaan Rao'").fetchone()[0]
        edited = self.post(f"/admin/candidates/{candidate_id}/edit", {"name": "Ishaan Rao", "party": "Campus Forum", "symbol": "Pencil", "description": "Improves feedback channels."})
        self.assertIn(b"Candidate updated successfully", edited.data)
        deleted = self.post(f"/admin/candidates/{candidate_id}/delete")
        self.assertIn(b"Candidate deleted successfully", deleted.data)
        self.assertIsNone(database.execute("SELECT id FROM candidates WHERE id=?", (candidate_id,)).fetchone())
        database.close()

    def test_dynamic_results_and_restart_persistence(self):
        self.voter_login()
        self.post("/vote", {"candidate_id": "1"})
        self.post("/logout")
        self.admin_login()
        results = self.client.get("/admin/results")
        self.assertIn(b"1", results.data)
        self.assertIn(b"100.0%", results.data)
        restarted = create_app({"TESTING": True, "SECRET_KEY": "new-key", "DATABASE": self.db_path})
        with restarted.app_context():
            database = sqlite3.connect(self.db_path)
            self.assertEqual(database.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 1)
            database.close()

    def test_csrf_rejects_missing_token(self):
        response = self.client.post("/login", data={"username": "voter1", "password": "Voter@123"})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
