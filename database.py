"""SQLite helpers and sample data for the Online Voting System."""

import os
import sqlite3
from flask import current_app, g
from werkzeug.security import generate_password_hash


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS voters (
 id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL,
 username TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
 has_voted INTEGER NOT NULL DEFAULT 0 CHECK (has_voted IN (0,1)),
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS candidates (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
 party TEXT NOT NULL, symbol TEXT, description TEXT,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS votes (
 id INTEGER PRIMARY KEY AUTOINCREMENT, voter_id INTEGER UNIQUE NOT NULL,
 candidate_id INTEGER NOT NULL, voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(voter_id) REFERENCES voters(id),
 FOREIGN KEY(candidate_id) REFERENCES candidates(id)
);
CREATE TABLE IF NOT EXISTS admins (
 id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
 password TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DEMO_CANDIDATES = [
 ("Aarav Sharma", "Student Unity", "Book", "Focuses on academic coordination and student activities."),
 ("Zoya Khan", "Campus Progress", "Star", "Focuses on student participation and campus initiatives."),
 ("Rohan Mehta", "Student Voice", "Lamp", "Focuses on communication between students and coordinators."),
]


def get_db():
    """Return one SQLite connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def initialize_database(database_path=None, reset=False):
    """Create tables and insert demo records when they do not exist."""
    if database_path is None:
        database_path = os.path.join(os.path.dirname(__file__), "database", "voting.db")
    os.makedirs(os.path.dirname(database_path), exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    if reset:
        connection.executescript("DROP TABLE IF EXISTS votes; DROP TABLE IF EXISTS candidates; DROP TABLE IF EXISTS voters; DROP TABLE IF EXISTS admins;")
    connection.executescript(SCHEMA)
    if connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0] == 0:
        connection.executemany("INSERT INTO candidates (name,party,symbol,description) VALUES (?,?,?,?)", DEMO_CANDIDATES)
    for full_name, username in [("Neha Verma", "voter1"), ("Kabir Singh", "voter2")]:
        connection.execute("INSERT OR IGNORE INTO voters (full_name,username,password) VALUES (?,?,?)", (full_name, username, generate_password_hash("Voter@123")))
    connection.execute("INSERT OR IGNORE INTO admins (username,password) VALUES (?,?)", ("admin", generate_password_hash("Admin@123")))
    connection.commit()
    connection.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    initialize_database(app.config["DATABASE"])
