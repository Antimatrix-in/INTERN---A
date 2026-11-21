# ANTI-MATRIX ONLINE ASSESSMENT — PRE-DEPLOYMENT VERIFICATION & DNS GATE REPORT

**Timestamp:** 2026-11-21T11:04:00+05:30  
**Target Domain:** `https://assesment.antimatrix.co.in` (and alias `https://assessment.antimatrix.co.in`)  
**Server IP:** `145.223.23.169` (`srv2018952`, Ubuntu 24.04 LTS)  
**Deployment Status:** **STAGED & VERIFIED — BLOCKED AT DNS GATE**

---

## 1. Pre-Deployment Verification Summary

| # | Inspection Item | Required State | Actual State | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Application Directory | `/var/www/anti-matrix-assessment` | Present, owned by `antimatrix:antimatrix` | **PASSED** |
| 2 | Git Status & Commit | Up-to-date with `origin/main` | Commit `cbd950e` (Cross-DB integration) | **PASSED** |
| 3 | Virtual Environment | Isolated Python 3.12 venv | `/var/www/anti-matrix-assessment/venv` | **PASSED** |
| 4 | Automated Test Suite | All tests passing on VPS | **43 passed, 0 failed** (in 26.27s) | **PASSED** |
| 5 | Gunicorn Upstream Port | Port `8015` free | `127.0.0.1:8015` free and unbound | **PASSED** |
| 6 | Source Database (`antimatrix_db`) | Strict read-only integration | `candidate_lookup_view` active, writes blocked | **PASSED** |
| 7 | Production `.env` | Configured with 0600 permissions | Created at `/var/www/anti-matrix-assessment/.env` | **PASSED** |
| 8 | Systemd Service Template | Production service unit | Staged at `/var/www/anti-matrix-assessment/anti-matrix-assessment.service` | **PASSED** |
| 9 | Nginx Site Template | Configured for domain & proxy | Staged at `/var/www/anti-matrix-assessment/nginx-assessment.conf` | **PASSED** |
| 10 | Existing Production Sites | Zero regression, untouched | All 5 production sites return **HTTP 200 OK** | **PASSED** |
| 11 | **DNS Resolution** | **Resolves to `145.223.23.169`** | **NXDOMAIN (DNS name does not exist)** | ⛔ **BLOCKED** |

---

## 2. DNS Gate Status (Action Required)

Per pre-deployment requirement:
> *"DNS must resolve to the VPS IP `145.223.23.169`. If DNS is not ready, stop the public deployment and report the issue. Do not modify DNS records automatically."*

### DNS Diagnostic Output:
- **Query `assesment.antimatrix.co.in`:** `DNS_ERROR_RCODE_NAME_ERROR` (NXDOMAIN)
- **Query `assessment.antimatrix.co.in`:** `DNS_ERROR_RCODE_NAME_ERROR` (NXDOMAIN)
- **Authoritative Nameservers:** `leif.ns.cloudflare.com`, `diva.ns.cloudflare.com`

### Required User Action in Cloudflare DNS Console:
Add the following DNS record(s) in your Cloudflare dashboard for domain `antimatrix.co.in`:

| Type | Name | Content (IPv4) | Proxy Status | TTL |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `assesment` | `145.223.23.169` | DNS only (or Proxied) | Auto |
| **A** (Recommended alias) | `assessment` | `145.223.23.169` | DNS only (or Proxied) | Auto |

---

## 3. Privileged Setup Steps (Database & Services)

Once the DNS record resolves to `145.223.23.169`, execute the following commands on the VPS with `sudo` (or provide the `antimatrix` sudo password to automate):

### Step 1: Create PostgreSQL Database & Role
```bash
# Read generated database password from protected staging file
DB_PASS=$(cat /var/www/anti-matrix-assessment/instance/.db_user_password)

# Create user and database
sudo -u postgres psql -c "CREATE USER anti_matrix_assessment_user WITH ENCRYPTED PASSWORD '$DB_PASS';"
sudo -u postgres psql -c "CREATE DATABASE anti_matrix_assessment_db OWNER anti_matrix_assessment_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE anti_matrix_assessment_db TO anti_matrix_assessment_user;"
```

### Step 2: Migrate Assessment Data
```bash
cd /var/www/anti-matrix-assessment
source .env
./venv/bin/python scripts/migrate_sqlite_to_pg.py instance/anti_matrix.db "$ASSESSMENT_DATABASE_URL"
```

### Step 3: Install & Start Systemd Service
```bash
sudo cp /var/www/anti-matrix-assessment/anti-matrix-assessment.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now anti-matrix-assessment.service
sudo systemctl is-active anti-matrix-assessment.service
```

### Step 4: Enable Nginx & Issue Let's Encrypt SSL
```bash
# Link Nginx site configuration
sudo cp /var/www/anti-matrix-assessment/nginx-assessment.conf /etc/nginx/sites-available/anti-matrix-assessment
sudo ln -sf /etc/nginx/sites-available/anti-matrix-assessment /etc/nginx/sites-enabled/

# Test Nginx syntax safely before reloading
sudo nginx -t && sudo systemctl reload nginx

# Issue SSL certificate via Certbot (after DNS propagation)
sudo certbot --nginx -d assesment.antimatrix.co.in -d assessment.antimatrix.co.in
```

---

## 4. Production Safety Audit

All existing production sites on VPS `145.223.23.169` have been inspected and confirmed operational with zero regressions:
- `antimatrix.co.in` (`127.0.0.1:8017`): **HTTP 200 OK**
- `intern.antimatrix.co.in` (`127.0.0.1:8002`): **HTTP 200 OK**
- `attendance.antimatrix.co.in` (`127.0.0.1:8010`): **HTTP 200 OK**
- `qmatrix.co.in` (`127.0.0.1:8000`): **HTTP 200 OK**
- Manpower Payroll (`127.0.0.1:10000`): **HTTP 200 OK**
