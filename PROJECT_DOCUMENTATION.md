# Online Voting System — Mini Project Documentation

## 1. Introduction

The Online Voting System is a web-based B.Sc. IT mini project. It demonstrates how a small election can be managed using Python, Flask, and SQLite. Registered voters can study candidate information and submit one vote. An administrator can maintain candidate records, check participation, and view results.

The election and every candidate in this project are fictional. The project is intended only for classroom demonstration.

## 2. Problem Statement

Paper-based voting takes manual effort to register participants, count votes, and prepare results. A basic digital system can make these steps easier to demonstrate. The main programming problem is to ensure that one authenticated voter cannot vote more than once while keeping the design understandable.

## 3. Proposed Solution

The proposed application uses a Flask web server and a local SQLite database. It has separate voter and administrator sessions. The database stores voter accounts, candidate details, vote records, and a simple administrator account. During voting, the vote insert and voter status update happen inside one database transaction.

## 4. Objectives

- Build a working web application with frontend, backend, and database layers.
- Authenticate voters and an administrator.
- Allow registration with validation and hashed passwords.
- Display fictional candidates in a clear format.
- Store only one vote for each voter.
- Calculate vote counts and turnout directly from the database.
- Present a simple interface suitable for a college viva.

## 5. Scope

The project covers one active student council demo election. It supports local voter registration, voting, candidate management, a voter register, and result viewing. It does not provide real identity verification or the controls needed for public elections.

## 6. Hardware Requirements

- Computer with at least 2 GB RAM
- About 100 MB free disk space
- Standard keyboard, mouse, and display

## 7. Software Requirements

- Windows, macOS, or Linux
- Python 3.9 or newer
- Flask 3.x
- Modern web browser
- SQLite support included with Python
- Text editor or IDE for source code study

## 8. Functional Requirements

### Voter functions

1. Register with full name, unique username, and password.
2. Log in using valid credentials.
3. View the voter dashboard and current status.
4. View candidate information.
5. Select and confirm exactly one candidate.
6. Receive a success message after submission.
7. Log out safely.

### Administrator functions

1. Log in through a separate admin page.
2. View voter, vote, participation, and candidate totals.
3. Add, edit, and delete valid candidate records.
4. View registered voters without passwords or vote choices.
5. View calculated candidate totals and percentages.

## 9. Non-Functional Requirements

- **Usability:** Pages use consistent navigation and simple wording.
- **Reliability:** Database constraints and transactions protect the voting rule.
- **Security:** Passwords are hashed, SQL is parameterized, protected routes check roles, and forms contain CSRF tokens.
- **Responsiveness:** The layout adapts to desktop, tablet, and mobile screens.
- **Maintainability:** The project uses direct Flask routes and short database helpers.
- **Privacy:** The admin voter list never reveals a voter's selected candidate.

## 10. System Modules

### Registration module
Checks required fields, name format, username format, password length, confirmation, and username uniqueness. It stores a Werkzeug password hash.

### Authentication module
Checks submitted credentials and creates a Flask session with one role. Decorators prevent voters and administrators from entering each other's protected pages.

### Candidate module
Shows candidates to voters. It also provides add, edit, and delete operations to the administrator. Candidates with recorded votes cannot be deleted.

### Voting module
Accepts one candidate selection, validates that the candidate exists, and records the vote inside a transaction. Both `voters.has_voted` and `votes.voter_id UNIQUE` prevent duplicates.

### Results module
Uses `COUNT` and `LEFT JOIN` queries to include candidates with zero votes. It calculates each percentage and overall turnout safely, including when no votes exist.

## 11. Database Design

### voters

| Field | Type | Purpose |
|---|---|---|
| id | INTEGER | Primary key |
| full_name | TEXT | Voter name |
| username | TEXT UNIQUE | Login name |
| password | TEXT | Password hash |
| has_voted | INTEGER | 0 before voting, 1 after voting |
| created_at | TIMESTAMP | Registration time |

### candidates

| Field | Type | Purpose |
|---|---|---|
| id | INTEGER | Primary key |
| name | TEXT | Candidate name |
| party | TEXT | Student group |
| symbol | TEXT | Simple ballot symbol |
| description | TEXT | Short profile |
| created_at | TIMESTAMP | Creation time |

### votes

| Field | Type | Purpose |
|---|---|---|
| id | INTEGER | Primary key |
| voter_id | INTEGER UNIQUE | Links the voter and prevents duplicates |
| candidate_id | INTEGER | Links the candidate |
| voted_at | TIMESTAMP | Submission time |

### admins

Stores the seeded administrator username and hashed password. This supporting table keeps the admin password out of application pages and source code comparisons.

## 12. System Workflow

```text
Home → Register/Login → Voter Dashboard → Candidate List
                                      └→ Ballot → Confirm → Success

Home → Admin Login → Admin Dashboard → Candidates / Voters / Results
```

## 13. Voting Algorithm

```text
1. Verify that the current session belongs to a voter.
2. Read the voter record.
3. If has_voted is 1, show the already-voted page.
4. Read and validate the selected candidate ID.
5. Begin an immediate SQLite transaction.
6. Check has_voted again inside the transaction.
7. Insert the vote using the voter ID and candidate ID.
8. Update has_voted to 1.
9. Commit both changes together.
10. Redirect to the success page.
```

If the insert fails, the transaction is rolled back. The database also rejects a second vote because `voter_id` is unique.

## 14. Admin Workflow

The administrator logs in with the seeded local account. The dashboard queries current counts. Candidate forms are checked on the server before data is inserted or updated. The voter page shows only account and status information. The result page groups votes by candidate and calculates percentages from the total number of stored vote rows.

## 15. Testing

The included `test_app.py` suite uses Flask's test client and a temporary SQLite database. It checks:

- Home page and custom 404 response
- Registration, password hashing, and duplicate usernames
- Correct and incorrect voter login
- Candidate list loading
- Empty and manipulated ballot submissions
- Successful voting and the `has_voted` update
- Duplicate vote and refresh protection
- Admin login and dashboard
- Candidate add, edit, and delete operations
- Dynamic results and persistence after creating a new app instance
- Voter/admin role separation
- Logout and missing CSRF rejection

Run it with `python -m unittest -v test_app.py`.

## 16. Limitations

- Supports one locally configured election.
- Uses a seeded admin account and Flask's development server.
- Does not verify a person's real identity.
- Does not provide anonymous cryptographic ballots or independent audits.
- Does not include email, OTP, or remote deployment features.
- It is not suitable for a real public election.

## 17. Future Scope

- Add start and closing time settings.
- Support multiple college elections.
- Add downloadable summary reports.
- Add controlled voter import from a college register.
- Improve keyboard and screen-reader testing.
- Add an administrator password update feature.

## 18. Conclusion

This project demonstrates a complete small web application with registration, sessions, database operations, validation, administration, and result calculation. Its central one-voter-one-vote rule is protected both in Flask logic and in SQLite. The design remains simple enough to explain and modify as a second-year B.Sc. IT mini project.
