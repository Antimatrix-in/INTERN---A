#!/bin/bash
set -euo pipefail

echo "========================================================"
echo "Anti-Matrix Online Assessment - Nginx & SSL Activation"
echo "========================================================"

# 1. Install and start systemd service
echo "[1/5] Installing systemd service..."
cp /var/www/anti-matrix-assessment/anti-matrix-assessment.service /etc/systemd/system/anti-matrix-assessment.service
systemctl daemon-reload
systemctl enable --now anti-matrix-assessment.service

# 2. Verify Gunicorn responds on port 8015
echo "[2/5] Verifying Gunicorn upstream on 127.0.0.1:8015..."
for i in {1..10}; do
    if curl -sI http://127.0.0.1:8015/login | grep -q "200 OK"; then
        echo "Gunicorn is active and responding with HTTP 200 OK."
        break
    fi
    sleep 1
done

# 3. Enable Nginx site configuration
echo "[3/5] Configuring Nginx reverse proxy..."
cp /var/www/anti-matrix-assessment/nginx-assessment.conf /etc/nginx/sites-available/anti-matrix-assessment
ln -sf /etc/nginx/sites-available/anti-matrix-assessment /etc/nginx/sites-enabled/anti-matrix-assessment

# 4. Test Nginx configuration and reload
echo "[4/5] Testing Nginx configuration..."
nginx -t
systemctl reload nginx

# 5. Acquire SSL Certificate with Certbot
echo "[5/5] Requesting Let's Encrypt SSL certificate..."
certbot --nginx -d assesment.antimatrix.co.in -d assessment.antimatrix.co.in --non-interactive --agree-tos -m admin@antimatrix.co.in --redirect || {
    echo "Warning: Multi-domain cert failed, issuing certificate for primary domain assesment.antimatrix.co.in..."
    certbot --nginx -d assesment.antimatrix.co.in --non-interactive --agree-tos -m admin@antimatrix.co.in --redirect
}

echo "Testing final routing and reloading Nginx..."
nginx -t
systemctl reload nginx

echo "========================================================"
echo "Anti-Matrix Assessment Subdomain Routing Activated Successfully!"
echo "========================================================"
