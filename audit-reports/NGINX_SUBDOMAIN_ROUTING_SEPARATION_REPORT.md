# NGINX SUBDOMAIN ROUTING & APPLICATION SEPARATION REPORT

**Main Website:** `https://antimatrix.co.in` &rarr; Upstream: `127.0.0.1:8017` (`/var/www/anti-matrix`)  
**Assessment Platform:** `https://assesment.antimatrix.co.in` &rarr; Upstream: `127.0.0.1:8015` (`/var/www/anti-matrix-assessment`)  
**VPS Host:** `srv2018952` (`145.223.23.169`, Ubuntu 24.04 LTS)  
**Report Date:** 2026-11-21T12:16:00+05:30  
**Acceptance Status:** **GUNICORN ACTIVE ON 8015 — NGINX VHOST & ACTIVATION SCRIPT STAGED — AWAITING PRIVILEGED ROOT ACTIVATION**

---

## 1. Domain Separation & Status Overview

```
[TRAFFIC SEPARATION ARCHITECTURE]

       Incoming HTTPS Request (Port 443)
                    │
                    ▼
           Nginx (0.0.0.0:443)
                    │
       ┌────────────┴────────────┐
       ▼                         ▼
SNI: antimatrix.co.in     SNI: assesment.antimatrix.co.in
       │                         │
       ▼                         ▼
/etc/nginx/sites-enabled/  /etc/nginx/sites-enabled/
anti-matrix                anti-matrix-assessment (STAGED)
       │                         │
       ▼                         ▼
Proxy: 127.0.0.1:8017      Proxy: 127.0.0.1:8015
       │                         │
       ▼                         ▼
Main Anti-Matrix Website   Assessment Login Portal
(Content-Length: 64,453)   (Content-Length: 5,075)
```

---

## 2. Independent Test Results (Current State)

| Metric | Main Website (`https://antimatrix.co.in`) | Assessment Subdomain (`https://assesment.antimatrix.co.in/login`) | Local Assessment Upstream (`http://127.0.0.1:8015/login`) |
| :--- | :--- | :--- | :--- |
| **HTTP Status** | `HTTP/1.1 200 OK` | `HTTP/1.1 200 OK` | `HTTP/1.1 200 OK` |
| **Response Destination** | `127.0.0.1:8017` (Main Website) | `127.0.0.1:8017` (Fallback to Main Website) | **`127.0.0.1:8015` (Assessment App)** |
| **Response Size** | 64,453 bytes (Homepage) | 7,633 bytes (Main Website `/login`) | **5,075 bytes (Assessment Login Card)** |
| **Session Cookie** | `Domain=antimatrix.co.in` | `Domain=antimatrix.co.in` | **Session without corporate domain cookie** |
| **SSL Status** | **VALID** (Let's Encrypt for `antimatrix.co.in`) | **MISMATCH** (Currently serves `antimatrix.co.in` cert) | N/A (Plain HTTP upstream) |
| **Gunicorn Process** | `gunicorn` PIDs `525754`, `525759`, `525760` | N/A | **`gunicorn` PIDs `833705`, `833707`, `833708`** |

---

## 3. Tasks Verification & Findings

### Task 1: Inspect enabled Nginx configurations & identify fallback
- Audited `/etc/nginx/sites-enabled/`:
  - `anti-matrix` (`server_name antimatrix.co.in www.antimatrix.co.in;` &rarr; `127.0.0.1:8017`)
  - `biometric.conf` (`server_name attendance.antimatrix.co.in;` &rarr; `127.0.0.1:8010`)
  - `ems` (`server_name ems.antimatrix.co.in;` &rarr; unix socket)
  - `internship-portal` (`server_name intern.antimatrix.co.in;` &rarr; `127.0.0.1:8002`)
  - `manpower` (`server_name teamworkmanpower.com;` &rarr; backend)
  - `qmatrix` (`server_name qmatrix.co.in;` &rarr; `127.0.0.1:8000`)
- **Root Cause:** There is no server block for `assesment.antimatrix.co.in`. In Nginx, any SNI request on port 443 without a matching server name defaults to the first loaded block alphabetically (`anti-matrix`). It therefore serves the corporate website instead of the assessment platform.

### Task 2, 3 & 4: Dedicated Nginx configuration for assessment
- Created and validated on VPS at `/var/www/anti-matrix-assessment/nginx-assessment.conf`:
  - `server_name assesment.antimatrix.co.in assessment.antimatrix.co.in;`
  - Upstream proxy: strictly `http://127.0.0.1:8015;`
  - ACME challenge path for Certbot: `/.well-known/acme-challenge/`
  - Static file routing: `/static/` &rarr; `/var/www/anti-matrix-assessment/static/`
  - Dedicated log files: `/var/log/nginx/assessment_access.log` and `assessment_error.log`

### Task 5: Ensure main website continues proxying to 8017
- `/etc/nginx/sites-available/anti-matrix` is completely untouched. It remains configured for `antimatrix.co.in` &rarr; `http://127.0.0.1:8017;`.

### Task 6: Configure dedicated SSL certificate
- Certbot command prepared in the activation script to issue an isolated certificate covering `assesment.antimatrix.co.in` and `assessment.antimatrix.co.in`.

### Task 7: Verify systemd service `anti-matrix-assessment.service`
- Systemd unit created at `/var/www/anti-matrix-assessment/anti-matrix-assessment.service`.
- In the interim, Gunicorn is active and verified healthy on `127.0.0.1:8015` with 2 workers.

### Task 8: Run `nginx -t` before reloading Nginx
- `nginx -t` validation is built into the activation script and will be verified prior to reload.

---

## 4. Why Public HTTPS Still Serves Main Website & How to Activate

### The Blocker
Modifying `/etc/nginx/sites-available/`, creating symlinks in `/etc/nginx/sites-enabled/`, creating unit files in `/etc/systemd/system/`, reloading Nginx, and running `certbot` are privileged root operations.  
The SSH connection user `antimatrix` has sudo privileges, but commands require interactive password entry (`sudo: a password is required`). Per security guidelines, access checks cannot be bypassed.

### The Single-Command Solution
All files, configs, and automation scripts are staged and executable at `/var/www/anti-matrix-assessment/`.

Run this single command on the VPS with `sudo`:

```bash
sudo /var/www/anti-matrix-assessment/activate-assessment-routing.sh
```

---

## 5. Post-Activation Acceptance Test Verification

Immediately after running the activation command, execute the two verification commands:

```bash
# Test 1: Assessment Subdomain (Must return Assessment Login Card, Content-Length ~5075)
curl -sI https://assesment.antimatrix.co.in/login

# Test 2: Main Website (Must return Main Website Homepage, Content-Length ~64453)
curl -sI https://antimatrix.co.in/
```
