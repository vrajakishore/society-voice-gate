#!/bin/bash
# restart-all.sh — Restart society-voice-gate dev environment after WSL crash
set -e

PROJECT=~/society-voice-gate
TUNNEL_ID="fun-ant-shvprm7"
TENANT="e6e6c3b7-14a4-4b8a-940e-37cf5d6507c7"
DEVTUNNEL=~/bin/devtunnel

echo "=== 1/5  Fix .azure permissions ==="
sudo chown -R $(whoami):$(whoami) ~/.azure 2>/dev/null || true

echo "=== 2/5  Azure login ==="
az account show -o none 2>/dev/null || az login --use-device-code --tenant "$TENANT"

echo "=== 3/5  Start Dev Tunnel (background) ==="
nohup "$DEVTUNNEL" host "$TUNNEL_ID" --allow-anonymous > /tmp/devtunnel.log 2>&1 &
sleep 3
echo "    Tunnel PID: $!"
grep -oP 'https://\S+' /tmp/devtunnel.log | head -1 || echo "    (check /tmp/devtunnel.log for URL)"

echo "=== 4/5  Start containers ==="
cd "$PROJECT"
podman-compose down 2>/dev/null || true
podman-compose up --build -d

echo "=== 5/5  Verify ==="
sleep 5
echo -n "Backend:  " && curl -sf http://localhost:8000/health && echo ""
echo -n "Health:   " && curl -sf http://localhost:8000/api/health/services | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['overall'])" 2>/dev/null && echo ""
echo "Frontend: http://localhost:5173"
echo ""
echo "Done! All services started."