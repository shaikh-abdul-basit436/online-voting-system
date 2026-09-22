"""Create or reset the local demo database."""
import argparse
import os
from database import initialize_database

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the voting database")
    parser.add_argument("--reset", action="store_true", help="Delete all current demo data first")
    args = parser.parse_args()
    path = os.path.join(os.path.dirname(__file__), "database", "voting.db")
    initialize_database(path, reset=args.reset)
    print("Database initialized successfully.")
