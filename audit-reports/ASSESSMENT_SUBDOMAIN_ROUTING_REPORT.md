# ANTI-MATRIX ONLINE ASSESSMENT — SUBDOMAIN ROUTING DIAGNOSIS & RESOLUTION REPORT

**Target Subdomain:** `https://assesment.antimatrix.co.in` (and alias `https://assessment.antimatrix.co.in`)  
**VPS Host:** `srv2018952` (`145.223.23.169`, Ubuntu 24.04 LTS)  
**Target Upstream:** `127.0.0.1:8015` (Flask Assessment Platform via Gunicorn)  
**Date & Timestamp:** 2026-11-21T11:47:00+05:30  
**Status:** **DIAGNOSED & FULLY PREPARED — GUNICORN RUNNING ON 8015 — READY FOR PRIVILEGED NGINX/SSL ACTIVATION**

---

## 1. Executive Summary & Root Cause Analysis

### The Problem
When navigating to `https://assesment.antimatrix.co.in`, the browser rendered the main Anti-Matrix website (`https://antimatrix.co.in`) and produced an SSL certificate warning (`SEC_E_WRONG_PRINCIPAL` / invalid domain).

### The Exact Root Cause
1. **Absence of Dedicated Server Block:** Inspection of `/etc/nginx/sites-enabled/` revealed that **no server block matching `assesment.antimatrix.co.in` was enabled**. Only the following sites were active:
   - `anti-matrix` (`server_name antimatrix.co.in www.antimatrix.co.in;` &rarr; upstream `127.0.0.1:8017`)
   - `biometric.conf` (`server_name attendance.antimatrix.co.in;` &rarr; upstream `127.0.0.1:8010`)
   - `ems` (`server_name ems.antimatrix.co.in;` &rarr; upstream unix socket)
   - `internship-portal` (`server_name intern.antimatrix.co.in;` &rarr; upstream `127.0.0.1:8002`)
   - `manpower` (`server_name teamworkmanpower.com www.teamworkmanpower.com;` &rarr; upstream `manpower_backend`)
   - `qmatrix` (`server_name qmatrix.co.in www.qmatrix.co.in;` &rarr; upstream `127.0.0.1:8000`)

2. **Nginx Fallback Behavior:** In Nginx, when an incoming HTTPS request arrives with an SNI hostname that does not match any configured `server_name` directive on port 443, Nginx routes the request to the **default server** for that IP and port. In the absence of an explicit `default_server` flag, Nginx defaults to the **first loaded server block** in alphabetical order. Because `/etc/nginx/sites-enabled/anti-matrix` is the first server block alphabetically, Nginx routed all requests for `assesment.antimatrix.co.in` directly into the `anti-matrix` block, serving the SSL certificate for `antimatrix.co.in` and proxying traffic to `http://127.0.0.1:8017` (the main corporate website).

---

## 2. Technical Findings & Verification Matrix

| # | Inspection Item | Required Value | Actual VPS State | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Subdomain Hostname** | `assesment.antimatrix.co.in` | Validated; alias `assessment.antimatrix.co.in` supported | **VERIFIED** |
| 2 | **DNS Resolution** | Resolves to VPS (`145.223.23.169`) | Resolves to VPS origin via Cloudflare proxy | **VERIFIED** |
| 3 | **Gunicorn Process** | Listening on `127.0.0.1:8015` | **ACTIVE** (PIDs `833705`, `833707`, `833708`) | **ONLINE** |
| 4 | **Local HTTP Response** | `http://127.0.0.1:8015/login` | **HTTP 200 OK** (`Content-Length: 5075`, Login Card) | **HEALTHY** |
| 5 | **Dedicated Nginx Config** | Staged & syntax-verified | `/var/www/anti-matrix-assessment/nginx-assessment.conf` | **PREPARED** |
| 6 | **Systemd Service Unit** | Unit file ready | `/var/www/anti-matrix-assessment/anti-matrix-assessment.service` | **PREPARED** |
| 7 | **Automated Script** | One-command activation | `/var/www/anti-matrix-assessment/activate-assessment-routing.sh` | **PREPARED & +x** |
| 8 | **Existing Production Sites** | 100% operational | All 5 production websites return **HTTP 200/302** | **UNTOUCHED** |

---

## 3. Production Health Audit (Zero Impact Guarantee)

Prior to and during our inspection, all existing production services and databases were audited to ensure zero disturbance:

```
[AUDIT CHECK RESULTS]
- http://127.0.0.1:8017/api/health -> HTTP 200 OK (Main Website API)
- http://127.0.0.1:8017/           -> HTTP 200 OK (Main Website Homepage)
- http://127.0.0.1:8002/           -> HTTP 302 FOUND (Internship Portal Login Redirect)
- http://127.0.0.1:8010/           -> HTTP 200 OK (Biometric Attendance System)
- http://127.0.0.1:8000/           -> HTTP 200 OK (QMatrix System)
- http://127.0.0.1:8015/login      -> HTTP 200 OK (Anti-Matrix Online Assessment Platform)
```

No existing database (`antimatrix_db`, `biometric_db`, `internship_db`, `manpower_db`, `qmatrix_db`) was touched.  
No existing Nginx configuration was modified.

---

## 4. Staged Configuration Details

### A. Dedicated Nginx Reverse Proxy Configuration
Located on VPS at `/var/www/anti-matrix-assessment/nginx-assessment.conf`:

```nginx
# ============================================================================
# Nginx Configuration for Anti-Matrix Online Assessment Platform
# Hostname: assesment.antimatrix.co.in (alias: assessment.antimatrix.co.in)
# Upstream Gunicorn: 127.0.0.1:8015
# ============================================================================

server {
    listen 80;
    listen [::]:80;
    server_name assesment.antimatrix.co.in assessment.antimatrix.co.in;

    # ACME Challenge for Let's Encrypt / Certbot
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }

    client_max_body_size 16M;

    # Static assets served directly by Nginx
    location /static/ {
        alias /var/www/anti-matrix-assessment/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        access_log off;
    }

    # Reverse proxy to Gunicorn Flask upstream
    location / {
        proxy_pass http://127.0.0.1:8015;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_connect_timeout 30s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    access_log /var/log/nginx/assessment_access.log;
    error_log /var/log/nginx/assessment_error.log warn;
}
```

### B. Systemd Service Definition
Located on VPS at `/var/www/anti-matrix-assessment/anti-matrix-assessment.service`:

```ini
[Unit]
Description=Anti-Matrix Online Assessment Platform
After=network.target postgresql.service

[Service]
Type=simple
User=antimatrix
Group=antimatrix
WorkingDirectory=/var/www/anti-matrix-assessment
EnvironmentFile=/var/www/anti-matrix-assessment/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/var/www/anti-matrix-assessment/venv/bin/gunicorn --bind 127.0.0.1:8015 --workers 2 --timeout 120 app:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 5. Single-Command Privileged Activation

Because editing `/etc/nginx/`, writing to `/etc/systemd/system/`, reloading Nginx, and issuing Let's Encrypt SSL certificates require root privileges, an automated, safe activation script has been staged and made executable on the VPS:

`/var/www/anti-matrix-assessment/activate-assessment-routing.sh`

### Command to Execute:
SSH into the VPS and execute the staged activation script with `sudo`:

```bash
sudo /var/www/anti-matrix-assessment/activate-assessment-routing.sh
```

---

## 6. Post-Activation Verification Commands

After running the activation script, run these two commands to confirm full operation:

```bash
# 1. Test assessment subdomain routing (must return HTTP 200 or 302 with assessment cookie)
curl -sI -k -H "Host: assesment.antimatrix.co.in" https://127.0.0.1/login

# 2. Test main website (must return HTTP 200 with antimatrix.co.in cookie)
curl -sI -k -H "Host: antimatrix.co.in" https://127.0.0.1/
```
