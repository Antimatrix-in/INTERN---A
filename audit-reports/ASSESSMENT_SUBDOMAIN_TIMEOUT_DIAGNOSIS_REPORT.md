# ASSESSMENT SUBDOMAIN CONNECTION TIMEOUT & ROUTING DIAGNOSIS REPORT

**Hostname:** `assesment.antimatrix.co.in` (and alias `assessment.antimatrix.co.in`)  
**VPS IP:** `145.223.23.169` (`srv2018952`, Ubuntu 24.04 LTS)  
**Report Timestamp:** 2026-11-21T12:06:00+05:30  
**Observed Error:** `ERR_CONNECTION_TIMED_OUT` (in browser)  

---

## 1. Complete Diagnostic Verification Matrix

| # | Inspection Category | Test Executed | Actual Finding | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **DNS Resolution** | Multi-resolver nslookup (`Default`, `1.1.1.1`, `8.8.8.8`, `Cloudflare Auth`) | **Default/ISP DNS:** Resolves to stale IPs `15.197.142.173` & `3.33.152.147`<br>**Cloudflare (1.1.1.1):** `145.223.23.169`<br>**Google (8.8.8.8):** `145.223.23.169`<br>**Auth (`maya.ns.cloudflare.com`):** `145.223.23.169` | ⚠️ **DNS CACHE SPLIT** |
| 2 | **Ports 80 & 443** | `ss -tulpn \| grep -E ':80\|:443'` | Nginx listening on `0.0.0.0:80`, `0.0.0.0:443`, `[::]:80`, `[::]:443` | 🟢 **OPEN & LISTENING** |
| 3 | **Firewall (UFW / Hostinger)** | Direct TCP probe to `145.223.23.169:80` and `443` | Responded in 50ms (HTTP 301 on port 80, HTTP 200 on port 443). **Not blocking.** | 🟢 **PASSING** |
| 4 | **Gunicorn Upstream** | `ps aux \| grep 8015` & `curl http://127.0.0.1:8015/login` | Active with 2 workers (PIDs `833705`, `833707`, `833708`). Returned **HTTP 200 OK** (`Content-Length: 5075`). | 🟢 **HEALTHY** |
| 5 | **Nginx Server Blocks** | `ls /etc/nginx/sites-enabled/` | Dedicated server block `anti-matrix-assessment` is **NOT yet enabled**. Staged at `/var/www/anti-matrix-assessment/nginx-assessment.conf`. | ⚠️ **NOT ENABLED** |
| 6 | **Nginx Routing Behavior** | `curl -sI -k -H "Host: assesment.antimatrix.co.in" https://145.223.23.169/` | Falls back to default block (`anti-matrix` on port 8017). Returns main website (`Content-Length: 64453`). | ⚠️ **FALLBACK ACTIVE** |
| 7 | **SSL Certificate** | `ls /etc/letsencrypt/renewal/` | Dedicated SSL certificate for `assesment.antimatrix.co.in` does not exist yet. Only `antimatrix.co.in` exists. | ⚠️ **PENDING CERTBOT** |
| 8 | **Existing Production Sites** | Probed ports `8017`, `8002`, `8010`, `8000` | All 5 production applications return **HTTP 200 / 302**. Zero disturbance. | 🟢 **UNTOUCHED** |

---

## 2. Root Cause Analysis

### A. Root Cause of `ERR_CONNECTION_TIMED_OUT`
When accessing `assesment.antimatrix.co.in` in the browser, the client's local DNS or ISP resolver returned the stale cached IP addresses **`15.197.142.173`** and **`3.33.152.147`** (AWS Global Accelerator / previous host), rather than `145.223.23.169`.

Testing TCP connections directly to `15.197.142.173:443`:
```
$ curl -I https://15.197.142.173
curl: (28) Connection timed out after 3004 milliseconds
```
This timed-out SYN packet is the exact source of `ERR_CONNECTION_TIMED_OUT`.

In contrast, testing TCP connections directly to the VPS origin **`145.223.23.169:443`**:
```
$ curl -I -k https://145.223.23.169/
HTTP/1.1 200 OK (responded in 0.05 seconds - NO TIMEOUT)
```

The authoritative Cloudflare nameservers (`maya.ns.cloudflare.com`) and major public DNS resolvers (`1.1.1.1`, `8.8.8.8`) already serve `145.223.23.169`. Flushing the local DNS cache or switching to `1.1.1.1` resolves the connection timeout immediately.

### B. Root Cause of Main Website Being Served
Once traffic reaches `145.223.23.169:443`:
Because no configuration matching `server_name assesment.antimatrix.co.in;` is currently enabled in `/etc/nginx/sites-enabled/`, Nginx selects the default virtual host for SSL, which is the first loaded block: `/etc/nginx/sites-enabled/anti-matrix`. It serves the certificate for `antimatrix.co.in` and proxies traffic to `http://127.0.0.1:8017`.

---

## 3. Fixes Staged and Ready on the VPS

1. **Gunicorn Assessment Daemon:** Started on `127.0.0.1:8015` with 2 workers.
2. **Corrected Nginx Virtual Host:** Created and validated at `/var/www/anti-matrix-assessment/nginx-assessment.conf`:
   - Configured with `server_name assesment.antimatrix.co.in assessment.antimatrix.co.in;`
   - Proxies strictly to `http://127.0.0.1:8015;`
   - Preserves all standard proxy headers (`$host`, `$remote_addr`, `$proxy_add_x_forwarded_for`, `$scheme`).
   - Dedicated access and error log paths.
3. **Automated Activation Script:** Prepared and made executable at:
   `/var/www/anti-matrix-assessment/activate-assessment-routing.sh`

---

## 4. Required Action to Activate Routing & SSL

Because enabling Nginx configurations, writing to `/etc/systemd/system/`, reloading Nginx, and issuing Let's Encrypt certificates require root (`sudo`) privileges, run the staged activation script on the VPS:

```bash
sudo /var/www/anti-matrix-assessment/activate-assessment-routing.sh
```

---

## 5. Post-Activation Verification Test

Once executed, verify from your terminal or browser:

```bash
# Verify the public HTTPS URL returns the Assessment login page
curl -sI https://assesment.antimatrix.co.in/login
```
Expected output: `HTTP/2 200` or `HTTP/1.1 200 OK` with `Content-Length: 5075` and session cookie.
