# ANTI-MATRIX — Online Assessment Platform
## Phase 1: Flask Application Foundation, Authentication & Admin Dashboard

A professional, production-ready web application for Anti-Matrix's internal internship recruitment and online assessment process.

---

## 1. Technology Stack

- **Backend:** Python 3.12+, Flask 3.0.3 (Modular Architecture with Blueprints)
- **Database Engine (Dual-Dialect Compatible):**
  - **Local Development:** SQLite3 (stored at `instance/anti_matrix.db` with enforced foreign key constraints via `PRAGMA foreign_keys=ON;`)
  - **VPS Production:** PostgreSQL (via `DATABASE_URL` with connection pooling)
- **ORM & Migrations:** Flask-SQLAlchemy 3.1.1, Flask-Migrate 4.1.0, Alembic
- **Authentication & Security:** Flask-Login 0.6.3, Werkzeug password hashing (scrypt / pbkdf2), Flask-WTF CSRF protection
- **Frontend & UI:** HTML5, CSS3, JavaScript (ES6), Bootstrap 5.3, Bootstrap Icons 1.11, Custom Anti-Matrix Corporate Design System (White & Dark Navy/Black `#070b14`, `#0b0f19`, `#111827`, `#1e293b` with Orange Accent `#f97316`)
- **JSON Processing:** Python `json` standard module
- **Testing:** Pytest 9.1+

---

## 2. Implemented Features (Phase 1)

### A. Login & Authentication System
- **Anti-Matrix Branding:** Custom corporate navy/black theme with orange accents, dedicated responsive login card.
- **Show/Hide Password:** Interactive eye toggle with client-side visibility control.
- **Remember Me & Session Security:** Configured with `HttpOnly` and `SameSite='Lax'` cookies.
- **Role-Based Routing:**
  - `ADMIN` role &rarr; Redirects strictly to `/admin/dashboard`.
  - `CANDIDATE` role &rarr; Redirects strictly to `/candidate/dashboard`.
- **Role-Based Access Control (RBAC):** Decorators `@admin_required` and `@candidate_required`. Candidates attempting to access administrative routes receive `403 Forbidden`.
- **No Public Registration:** Candidate accounts are exclusively provisioned by administrators via the Credential Manager.
- **Secure Initial Admin Setup:** Created via CLI (`python -m flask create-admin`) or environment variables without hardcoded production credentials.

### B. Admin Dashboard
- **Sidebar Navigation (9 Sections):**
  1. Overview (`/admin/dashboard`)
  2. Assessment Manager (`/admin/assessments`)
  3. Question Bank (`/admin/questions`)
  4. Credential Manager (`/admin/credentials`)
  5. Candidate Manager (`/admin/candidates`)
  6. Examination Results (`/admin/results`)
  7. Proctoring Logs (`/admin/proctoring`)
  8. Settings (`/admin/settings`)
  9. Logout (`/logout`)
- **Database-Driven Statistics (No Hardcoded Numbers):**
  - **Total Candidates:** Live count of registered candidates.
  - **Active Credentials:** Live count of unexpired, active credentials within the 48-hour window.
  - **Pending Assessments:** Sum of active credentials and active in-progress attempts.
  - **Completed Assessments:** Count of submitted attempts.
  - **Passed Candidates:** Count of candidates meeting or exceeding assessment pass percentage.
  - **Failed Candidates:** Count of candidates below the pass percentage.
- **Live Feeds:** Recent credential issuances with remaining time and recent examination results.

### C. Credential Manager (Core Feature)
- **Candidate Account Provisioning:**
  - Candidate Full Name
  - Candidate Email
  - Auto-generated unique User ID (e.g. `AM-2026-X8K9M2`)
  - Auto-generated secure 12-character high-entropy password
  - Assigned Assessment
  - Creation Date (UTC)
  - Expiry Date (strictly 48 hours from creation)
  - Real-time Status: `ACTIVE`, `USED`, `EXPIRED`, `DISABLED`
- **Strict 48-Hour Expiry:**
  - Enforced strictly on the server. If `now >= expires_at`, the candidate cannot start a test.
- **Single-Attempt Enforcement:**
  - Database unique constraint on `Attempt.credential_id` guarantees only one attempt per credential.
- **Interruption Recovery:**
  - If a candidate experiences network failure or closes their browser, clicking "Resume Assessment" recovers their existing active attempt and saved answers.
- **Confirmation Voucher Screen:**
  - Displays generated User ID, one-time reveal of generated password, assessment duration, and full invitation template with single-click "Copy Invitation Message" and "Print Voucher" buttons.
- **Explicit Password Regeneration:**
  - Candidate credentials can only be reset through an explicit administrator action with confirmation, restarting the 48-hour window.

### D. Candidate Dashboard & Examination Interface
- **Dashboard Displays:**
  - Candidate Name & User ID
  - Assigned Assessment (Title, Code, Duration, Pass mark, MCQ count, Coding count, Instructions)
  - Live JavaScript 48-Hour Credential Countdown Timer
  - Examination Status (`NOT STARTED`, `IN PROGRESS`, `COMPLETED`, `EXPIRED`, `DISABLED`)
- **Conditional Actions:**
  - Shows **"Start Assessment"** only when the assessment is active and credential is valid.
  - Shows **"Resume Assessment"** when an attempt is in-progress.
  - Displays a warning banner when the 48-hour window has expired.
- **Examination Session:**
  - Server-side examination countdown timer.
  - Live AJAX autosave of candidate answers.
  - Question navigation palette.
  - Submit confirmation modal.
  - Automatic transition of credential to `USED` upon submission.

### E. Assessment Manager
- Create, edit, and toggle active/inactive status of assessments.
- Configurable duration (minutes).
- Configurable pass percentage (0 - 100%).
- Configurable MCQ count.
- Configurable coding problem count strictly constrained from **1 to 5** (with server-side validation).

### F. Question Bank Interface
- Upload structured JSON question files.
- Documented and validated JSON schema.
- Preview screen for staged questions before persisting to database.
- Question listing with search and filter by assessment, category, and difficulty.
- Question editing and deletion.
- Downloadable valid JSON schema template (`antimatrix_question_template.json`).

---

## 3. Project Structure

```
anti_matrix_assessment/
├── app.py                     # Flask application factory, routes registration, CLI commands
├── config.py                  # Environment-driven database config (SQLite / PostgreSQL)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .env                       # Local environment configuration (git ignored)
├── .gitignore                 # Excludes local databases, caches, and secrets
├── instance/                  # Local instance directory
│   ├── .gitkeep               # Preserves folder in git
│   └── anti_matrix.db         # Local SQLite3 database (git ignored)
├── models/                    # Modular SQLAlchemy models (Dual-dialect compatible)
│   ├── __init__.py            # Model discovery and exports
│   ├── database.py            # db instance & SQLite foreign key event listener
│   ├── user.py                # User model (Admin & Candidate)
│   ├── assessment.py          # Assessment model
│   ├── question.py            # Question model (MCQs)
│   ├── credential.py          # Credential model (48h strict expiry)
│   ├── attempt.py             # Attempt and AttemptAnswer models
│   ├── result.py              # Scored Result model
│   └── proctoring.py          # ProctoringEvent model
├── routes/                    # Modular Flask Blueprints
│   ├── __init__.py            # Blueprint registry
│   ├── auth.py                # Login, logout, role redirection
│   ├── admin.py               # 8 Admin sections (Dashboard, Assessments, Questions, etc.)
│   └── candidate.py           # Candidate dashboard, start/resume, autosave, submit
├── services/                  # Business logic services
│   ├── __init__.py            # Service exports
│   ├── auth_service.py        # Authentication & RBAC decorators
│   ├── credential_service.py  # User ID, password generation, 48h expiry, status sync
│   ├── assessment_service.py  # Assessment CRUD & coding validation (1-5)
│   ├── question_service.py    # JSON validation, template generation, batch import
│   ├── stats_service.py       # Live database-driven dashboard metrics
│   └── exam_service.py        # Single attempt rule, server timer, autosave, grading
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Base layout (Bootstrap 5, Icons, Custom CSS)
│   ├── auth/
│   │   └── login.html         # Anti-Matrix branded login page
│   ├── admin/                 # 12 Admin section templates
│   ├── candidate/             # 4 Candidate portal templates
│   └── errors/                # 403, 404, 500 error pages
├── static/                    # Static assets
│   ├── css/custom.css         # Anti-Matrix custom design system
│   ├── js/                    # auth.js, admin.js, candidate.js
│   └── images/logo.svg        # Anti-Matrix vector brand logo
├── migrations/                # Alembic database migrations
├── tests/                     # Comprehensive automated test suite
│   ├── conftest.py            # Pytest fixtures and testing app context
│   ├── test_auth_and_roles.py # Admin/Candidate login, RBAC, 403 tests
│   ├── test_credential_and_exam.py # 48h expiry, 1-attempt rule, resumption
│   └── test_assessment_and_questions.py # Assessment validation (1-5), JSON parser, stats
└── README.md                  # Project documentation
```

---

## 4. Local Development Setup (SQLite3)

### Prerequisites
- Python 3.12+ (Virtual environment recommended)
- Git

### Step 1: Clone / Navigate to Workspace
```bash
git clone https://github.com/Antimatrix-in/INTERN---A.git
cd INTERN---A
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
By default, the application runs on **SQLite3** stored locally at `instance/anti_matrix.db`. No PostgreSQL installation or setup is needed for local development.

### Step 4: Initialize the Database & Seed Admin
```bash
python -m flask init-db
```
This command creates the tables in `instance/anti_matrix.db` with SQLite foreign keys enabled, and seeds the initial administrator account.

*(Optional)* Seed a custom administrator directly:
```bash
python -m flask create-admin --username admin --email admin@antimatrix.local --password AntiMatrix@2026! --fullname "System Administrator"
```

### Step 5: Start the Local Development Server
```bash
python app.py
```
Or via the Flask CLI:
```bash
python -m flask run --host=0.0.0.0 --port=5000
```
Open [http://localhost:5000](http://localhost:5000) in your browser:
- **Admin Username:** `admin` (or `admin@antimatrix.local`)
- **Admin Password:** `AntiMatrix@2026!`

---

## 5. Hostinger VPS Production Migration (PostgreSQL)

When deploying this application to a Hostinger VPS with PostgreSQL, follow this standardized procedure:

### Step 1: Provision PostgreSQL on Hostinger VPS
1. In the VPS control panel or via SSH, install and start PostgreSQL:
   ```bash
   sudo apt update
   sudo apt install -y postgresql postgresql-contrib libpq-dev
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```
2. Create the production database and user:
   ```bash
   sudo -u postgres psql -c "CREATE USER antimatrix_user WITH PASSWORD 'StrongProductionPasswordHere!';"
   sudo -u postgres psql -c "CREATE DATABASE anti_matrix_db OWNER antimatrix_user;"
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE anti_matrix_db TO antimatrix_user;"
   ```

### Step 2: Configure Environment on Hostinger VPS
On the VPS, create the `.env` file and set the `DATABASE_URL` environment variable:
```ini
FLASK_ENV=production
FLASK_DEBUG=0
SECRET_KEY=generate-a-strong-random-hex-string-for-production
DATABASE_URL=postgresql://antimatrix_user:StrongProductionPasswordHere!@localhost:5432/anti_matrix_db
CREDENTIAL_EXPIRY_HOURS=48
MAX_CONTENT_LENGTH=5242880
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@antimatrix.local
ADMIN_PASSWORD=AntiMatrix@Production2026!
ADMIN_FULL_NAME="Platform Administrator"
```
The application dynamically detects the `postgresql://` prefix and switches to PostgreSQL with connection pooling (`pool_size=10`, `max_overflow=20`, `pool_recycle=300`).

### Step 3: Run Database Migrations on PostgreSQL
Run Alembic migrations to apply the schema to the production PostgreSQL database:
```bash
python -m flask db upgrade
```

### Step 4: Create the Production Administrator
```bash
python -m flask create-admin
```

### Step 5: (Optional) Migrate Existing Local Data
To copy local data from `instance/anti_matrix.db` into PostgreSQL without resetting records, you can use `pgloader`:
```bash
pgloader ./instance/anti_matrix.db postgresql://antimatrix_user:StrongProductionPasswordHere!@localhost:5432/anti_matrix_db
```

### Step 6: Run with a Production WSGI Server (Gunicorn)
```bash
gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
```

---

## 6. Question Bank JSON Schema

To import questions via JSON in the Admin Question Bank, upload an array of objects matching the documented schema below:

```json
[
  {
    "question_text": "What is the average time complexity of searching in a Python dictionary?",
    "options": [
      {"id": "A", "text": "O(1)"},
      {"id": "B", "text": "O(n)"},
      {"id": "C", "text": "O(log n)"},
      {"id": "D", "text": "O(n log n)"}
    ],
    "correct_option": "A",
    "explanation": "Python dictionaries use hash tables, offering O(1) average lookup time.",
    "points": 1.0,
    "difficulty": "EASY",
    "category": "Data Structures"
  }
]
```

You can download a template directly from the Question Bank interface via the **"JSON Template"** button.

---

## 7. Running the Automated Test Suite

Run the full pytest suite with verbose output:
```bash
python -m pytest tests/ -v
```

All 11 tests verify:
- Role-based login redirection (`/admin/dashboard` vs `/candidate/dashboard`)
- Candidate restriction from administrative endpoints (`403 Forbidden`)
- Unauthenticated redirection to login
- Strict 48-hour credential expiration enforcement
- Password hashing (plain text never stored in database)
- Single-attempt constraint enforcement
- Examination interruption recovery & resumption
- Answer autosave persistence
- Assessment coding count validation (1 to 5)
- Documented JSON schema question parsing & validation
- Real-time database-driven statistics calculation
