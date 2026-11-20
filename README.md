# ANTI-MATRIX — Online Assessment Platform
## Phase 1: Flask Application Foundation, Authentication & Admin Dashboard

A professional, production-ready web application for Anti-Matrix's internal internship recruitment and online assessment process.

---

## 1. Technology Stack

- **Backend:** Python 3.12+, Flask 3.0.3
- **Database:** PostgreSQL (with `psycopg2-binary` and connection pooling)
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
- **Sidebar Navigation:**
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
  - Stored as PostgreSQL `TIMESTAMPTZ`.
  - Expiry is strictly enforced on the server. If `now >= expires_at`, the candidate cannot start a test.
- **Single-Attempt Enforcement:**
  - Strict PostgreSQL unique constraint (`uq_attempt_credential`) guarantees only one attempt per credential.
- **Interruption Recovery:**
  - If a candidate experiences network failure or closes their browser, clicking "Resume Assessment" recovers their existing active attempt and saved answers.
- **Confirmation Voucher Screen:**
  - Displays generated User ID, one-time reveal of generated password, assessment duration, and full invitation template with single-click "Copy Credentials" and "Print Voucher" buttons.
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
  - Transition of credential to `USED` upon submission.

### E. Assessment Manager
- Create, edit, and toggle active/inactive status of assessments.
- Configurable duration (minutes).
- Configurable pass percentage (0 - 100%).
- Configurable MCQ count.
- Configurable coding problem count strictly constrained from **1 to 5** (with server-side validation).

### F. Question Bank Interface
- Upload structured JSON question files.
- Documented and validated JSON schema.
- Preview screen for staged questions before persisting to PostgreSQL.
- Question listing with search and filter by assessment, category, and difficulty.
- Question editing and deletion.
- Downloadable valid JSON schema template (`antimatrix_question_template.json`).

---

## 3. Project Structure

```
anti_matrix_assessment/
├── app.py                     # Flask application factory, routes registration, CLI commands
├── config.py                  # Environment configuration, database pooling, session settings
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .env                       # Local environment configuration
├── models/                    # Modular SQLAlchemy models
│   ├── __init__.py            # Model discovery and exports
│   ├── database.py            # SQLAlchemy instance
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
│   ├── admin/
│   │   ├── base_admin.html    # 9-section sidebar layout
│   │   ├── dashboard.html     # Live metrics & recent activity feeds
│   │   ├── assessment_manager.html
│   │   ├── assessment_form.html
│   │   ├── question_bank.html
│   │   ├── question_preview.html
│   │   ├── question_form.html
│   │   ├── credential_manager.html
│   │   ├── credential_create.html
│   │   ├── credential_confirm.html # Confirmation voucher with copy buttons
│   │   ├── candidate_manager.html
│   │   ├── results.html
│   │   ├── proctoring_logs.html
│   │   └── settings.html
│   ├── candidate/
│   │   ├── base_candidate.html
│   │   ├── dashboard.html     # Candidate portal & 48h countdown
│   │   ├── exam_session.html  # Exam timer, autosave, question palette
│   │   └── exam_result.html   # Scored submission summary
│   └── errors/
│       ├── 403.html           # Forbidden error page
│       ├── 404.html           # Not found error page
│       └── 500.html           # Server error page
├── static/                    # Static assets
│   ├── css/
│   │   └── custom.css         # Anti-Matrix custom design system
│   ├── js/
│   │   ├── auth.js            # Password show/hide, form submission feedback
│   │   ├── admin.js           # Clipboard copying, sidebar toggle
│   │   └── candidate.js       # Live 48h countdown, server exam timer, autosave fetch
│   └── images/
│       └── logo.svg           # Anti-Matrix vector brand logo
├── migrations/                # Alembic database migrations (PostgreSQL)
├── instance/                  # Local runtime directory
├── tests/                     # Comprehensive automated test suite
│   ├── conftest.py            # Pytest fixtures and app context
│   ├── test_auth_and_roles.py # Admin/Candidate login, RBAC, 403 tests
│   ├── test_credential_and_exam.py # 48h expiry, 1-attempt rule, resumption
│   └── test_assessment_and_questions.py # Assessment validation (1-5), JSON parser, stats
└── README.md                  # Project documentation
```

---

## 4. Installation & Setup Instructions

### Prerequisites
- Python 3.12+
- PostgreSQL 14+ (PostgreSQL 18 tested and verified)

### Step 1: Clone / Navigate to Workspace
```bash
cd c:\Users\Prave\Desktop\Assesment\INTERN---A
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Ensure your PostgreSQL database URL is configured in `.env`:
```ini
DATABASE_URL=postgresql://postgres:root@localhost:5432/anti_matrix_db
SECRET_KEY=your-production-secret-key-here
CREDENTIAL_EXPIRY_HOURS=48
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@antimatrix.local
ADMIN_PASSWORD=AntiMatrix@2026!
ADMIN_FULL_NAME="System Administrator"
```

### Step 4: Database Initialization & Migrations
Initialize database tables and run Alembic migrations:
```bash
python -m flask db upgrade
```

### Step 5: Create Initial Administrator Account
Seed the initial admin account securely:
```bash
python -m flask create-admin
```
*(Or specify custom credentials via CLI flags)*:
```bash
python -m flask create-admin --username admin --email admin@example.com --password YourSecurePassword123! --fullname "Lead Admin"
```

---

## 5. Running the Application

Start the Flask server:
```bash
python app.py
```
Or using the Flask CLI:
```bash
python -m flask run --host=0.0.0.0 --port=5000
```

Access the platform:
- **URL:** [http://localhost:5000](http://localhost:5000)
- **Initial Admin Credentials:**
  - **Username:** `admin` (or `admin@antimatrix.local`)
  - **Password:** `AntiMatrix@2026!`

---

## 6. Question Bank JSON Schema

To import questions via JSON, upload an array of objects matching the documented schema below:

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
    "explanation": "Python dictionaries are implemented using hash tables, offering O(1) average lookup time.",
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
