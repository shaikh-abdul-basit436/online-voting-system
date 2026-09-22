"""Online Voting System - academic Flask mini project."""
import os
import re
import secrets
import sqlite3
from functools import wraps

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db, init_app


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "development-key-change-before-deployment"),
        DATABASE=os.path.join(app.root_path, "database", "voting.db"),
        ELECTION_NAME="Student Council Demo Election",
        ELECTION_STATUS="Active",
    )
    if test_config:
        app.config.update(test_config)
    init_app(app)

    @app.before_request
    def create_csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(24)

    @app.context_processor
    def shared_template_values():
        return {
            "csrf_token": session.get("csrf_token"),
            "election_name": app.config["ELECTION_NAME"],
            "election_status": app.config["ELECTION_STATUS"],
        }

    def valid_csrf():
        token = request.form.get("csrf_token", "")
        return secrets.compare_digest(token, session.get("csrf_token", ""))

    def require_csrf():
        if not valid_csrf():
            abort(400, description="The form expired. Please return and try again.")

    def voter_required(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if not session.get("voter_id") or session.get("role") != "voter":
                flash("Please log in as a voter to continue.", "warning")
                return redirect(url_for("voter_login"))
            return view(**kwargs)
        return wrapped_view

    def admin_required(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if not session.get("admin_id") or session.get("role") != "admin":
                flash("Administrator login is required.", "warning")
                return redirect(url_for("admin_login"))
            return view(**kwargs)
        return wrapped_view

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if session.get("role") == "voter":
            return redirect(url_for("voter_dashboard"))
        if request.method == "POST":
            require_csrf()
            full_name = " ".join(request.form.get("full_name", "").split())
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            error = None
            if not all([full_name, username, password, confirm_password]):
                error = "All fields are required."
            elif not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{2,59}", full_name):
                error = "Enter a valid full name using 3 to 60 letters."
            elif not re.fullmatch(r"[a-z0-9_]{4,20}", username):
                error = "Username must be 4 to 20 letters, numbers, or underscores."
            elif len(password) < 8:
                error = "Password must contain at least 8 characters."
            elif password != confirm_password:
                error = "Passwords do not match."
            if error is None:
                try:
                    database = get_db()
                    database.execute(
                        "INSERT INTO voters (full_name,username,password) VALUES (?,?,?)",
                        (full_name, username, generate_password_hash(password)),
                    )
                    database.commit()
                    flash("Registration successful. You can now log in.", "success")
                    return redirect(url_for("voter_login"))
                except sqlite3.IntegrityError:
                    error = "That username is already registered."
            flash(error, "danger")
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def voter_login():
        if session.get("role") == "voter":
            return redirect(url_for("voter_dashboard"))
        if request.method == "POST":
            require_csrf()
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            voter = get_db().execute("SELECT * FROM voters WHERE username = ?", (username,)).fetchone()
            if voter and check_password_hash(voter["password"], password):
                token = session.get("csrf_token")
                session.clear()
                session.update(voter_id=voter["id"], role="voter", csrf_token=token)
                return redirect(url_for("voter_dashboard"))
            flash("Invalid voter username or password.", "danger")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        require_csrf()
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("index"))

    @app.route("/voter/dashboard")
    @voter_required
    def voter_dashboard():
        database = get_db()
        voter = database.execute("SELECT * FROM voters WHERE id = ?", (session["voter_id"],)).fetchone()
        count = database.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        return render_template("voter_dashboard.html", voter=voter, candidate_count=count)

    @app.route("/candidates")
    @voter_required
    def candidates():
        rows = get_db().execute("SELECT * FROM candidates ORDER BY id").fetchall()
        return render_template("candidates.html", candidates=rows)

    @app.route("/vote", methods=["GET", "POST"])
    @voter_required
    def vote():
        database = get_db()
        voter = database.execute("SELECT * FROM voters WHERE id = ?", (session["voter_id"],)).fetchone()
        if voter["has_voted"]:
            return render_template("already_voted.html")
        candidates_list = database.execute("SELECT * FROM candidates ORDER BY id").fetchall()
        if request.method == "POST":
            require_csrf()
            candidate_id = request.form.get("candidate_id", type=int)
            candidate = database.execute("SELECT id FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
            if not candidate:
                flash("Select a valid candidate before submitting your vote.", "danger")
                return render_template("vote_confirmation.html", candidates=candidates_list), 400
            try:
                database.execute("BEGIN IMMEDIATE")
                current = database.execute("SELECT has_voted FROM voters WHERE id = ?", (session["voter_id"],)).fetchone()
                if not current or current["has_voted"]:
                    database.rollback()
                    return render_template("already_voted.html")
                cursor = database.execute(
                    "INSERT INTO votes (voter_id,candidate_id) VALUES (?,?)",
                    (session["voter_id"], candidate_id),
                )
                database.execute("UPDATE voters SET has_voted = 1 WHERE id = ?", (session["voter_id"],))
                voted_at = database.execute("SELECT voted_at FROM votes WHERE id = ?", (cursor.lastrowid,)).fetchone()[0]
                database.commit()
                session["last_vote_time"] = voted_at
                return redirect(url_for("vote_success"))
            except sqlite3.IntegrityError:
                database.rollback()
                return render_template("already_voted.html")
        return render_template("vote_confirmation.html", candidates=candidates_list)

    @app.route("/vote/success")
    @voter_required
    def vote_success():
        voter = get_db().execute("SELECT has_voted FROM voters WHERE id = ?", (session["voter_id"],)).fetchone()
        if not voter or not voter["has_voted"]:
            return redirect(url_for("vote"))
        voted_at = get_db().execute("SELECT voted_at FROM votes WHERE voter_id = ?", (session["voter_id"],)).fetchone()
        return render_template("vote_success.html", voted_at=voted_at[0] if voted_at else session.get("last_vote_time"))

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        if request.method == "POST":
            require_csrf()
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            admin = get_db().execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
            if admin and check_password_hash(admin["password"], password):
                token = session.get("csrf_token")
                session.clear()
                session.update(admin_id=admin["id"], role="admin", csrf_token=token)
                return redirect(url_for("admin_dashboard"))
            flash("Invalid administrator username or password.", "danger")
        return render_template("admin_login.html")

    @app.route("/admin/dashboard")
    @admin_required
    def admin_dashboard():
        database = get_db()
        total_voters = database.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
        total_votes = database.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
        total_candidates = database.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        recent_votes = database.execute("SELECT voted_at FROM votes ORDER BY voted_at DESC LIMIT 5").fetchall()
        summary = {
            "total_voters": total_voters,
            "total_votes": total_votes,
            "remaining": total_voters - total_votes,
            "total_candidates": total_candidates,
            "participation": round((total_votes / total_voters * 100), 1) if total_voters else 0,
        }
        return render_template("admin_dashboard.html", summary=summary, recent_votes=recent_votes)

    def validate_candidate_form():
        values = {
            "name": " ".join(request.form.get("name", "").split()),
            "party": " ".join(request.form.get("party", "").split()),
            "symbol": " ".join(request.form.get("symbol", "").split()),
            "description": " ".join(request.form.get("description", "").split()),
        }
        error = None
        if not values["name"] or not values["party"]:
            error = "Candidate name and party/group are required."
        elif len(values["name"]) > 60 or len(values["party"]) > 60:
            error = "Name and party/group must be 60 characters or fewer."
        elif len(values["symbol"]) > 30 or len(values["description"]) > 250:
            error = "Symbol or description is too long."
        return values, error

    @app.route("/admin/candidates", methods=["GET", "POST"])
    @admin_required
    def manage_candidates():
        database = get_db()
        if request.method == "POST":
            require_csrf()
            values, error = validate_candidate_form()
            if error:
                flash(error, "danger")
            else:
                database.execute(
                    "INSERT INTO candidates (name,party,symbol,description) VALUES (?,?,?,?)",
                    (values["name"], values["party"], values["symbol"], values["description"]),
                )
                database.commit()
                flash("Candidate added successfully.", "success")
                return redirect(url_for("manage_candidates"))
        rows = database.execute(
            "SELECT c.*, COUNT(v.id) AS vote_count FROM candidates c LEFT JOIN votes v ON v.candidate_id=c.id GROUP BY c.id ORDER BY c.id"
        ).fetchall()
        return render_template("manage_candidates.html", candidates=rows, edit_candidate=None)

    @app.route("/admin/candidates/<int:candidate_id>/edit", methods=["GET", "POST"])
    @admin_required
    def edit_candidate(candidate_id):
        database = get_db()
        candidate = database.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not candidate:
            abort(404)
        if request.method == "POST":
            require_csrf()
            values, error = validate_candidate_form()
            if error:
                flash(error, "danger")
            else:
                database.execute(
                    "UPDATE candidates SET name=?,party=?,symbol=?,description=? WHERE id=?",
                    (values["name"], values["party"], values["symbol"], values["description"], candidate_id),
                )
                database.commit()
                flash("Candidate updated successfully.", "success")
                return redirect(url_for("manage_candidates"))
        rows = database.execute(
            "SELECT c.*, COUNT(v.id) AS vote_count FROM candidates c LEFT JOIN votes v ON v.candidate_id=c.id GROUP BY c.id ORDER BY c.id"
        ).fetchall()
        return render_template("manage_candidates.html", candidates=rows, edit_candidate=candidate)

    @app.post("/admin/candidates/<int:candidate_id>/delete")
    @admin_required
    def delete_candidate(candidate_id):
        require_csrf()
        database = get_db()
        candidate = database.execute(
            "SELECT c.name, COUNT(v.id) vote_count FROM candidates c LEFT JOIN votes v ON v.candidate_id=c.id WHERE c.id=? GROUP BY c.id",
            (candidate_id,),
        ).fetchone()
        if not candidate:
            abort(404)
        if candidate["vote_count"]:
            flash("This candidate cannot be deleted because votes are already recorded.", "danger")
        else:
            database.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
            database.commit()
            flash("Candidate deleted successfully.", "success")
        return redirect(url_for("manage_candidates"))

    @app.route("/admin/voters")
    @admin_required
    def voters():
        rows = get_db().execute(
            "SELECT id,full_name,username,has_voted,created_at FROM voters ORDER BY id"
        ).fetchall()
        return render_template("voters.html", voters=rows)

    @app.route("/admin/results")
    @admin_required
    def results():
        database = get_db()
        rows = database.execute(
            "SELECT c.id,c.name,c.party,c.symbol,COUNT(v.id) AS vote_count "
            "FROM candidates c LEFT JOIN votes v ON v.candidate_id=c.id "
            "GROUP BY c.id ORDER BY vote_count DESC,c.id"
        ).fetchall()
        total_votes = database.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
        total_voters = database.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
        result_rows = [dict(row) | {"percentage": round(row["vote_count"] / total_votes * 100, 1) if total_votes else 0} for row in rows]
        turnout = round(total_votes / total_voters * 100, 1) if total_voters else 0
        return render_template("results.html", results=result_rows, total_votes=total_votes, total_voters=total_voters, turnout=turnout)

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("404.html", code=400, title="Request could not be completed", message=str(error.description)), 400

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html", code=404, title="Page not found", message="The page you requested does not exist."), 404

    @app.errorhandler(500)
    def internal_error(error):
        try:
            get_db().rollback()
        except Exception:
            pass
        return render_template("500.html"), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)
