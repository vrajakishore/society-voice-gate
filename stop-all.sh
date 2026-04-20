#!/bin/bash
# stop-all.sh — Gracefully stop all society-voice-gate services (keeps resources intact)
set -e

PROJECT=~/society-voice-gate

echo "=== 1/3  Stop Dev Tunnel ==="
pkill -f "devtunnel host" 2>/dev/null && echo "    Stopped" || echo "    Not running"

echo "=== 2/3  Stop containers ==="
cd "$PROJECT"
podman-compose stop 2>/dev/null && echo "    Containers stopped" || echo "    No containers running"

echo "=== 3/3  Verify ==="
echo -n "    Containers: " && podman ps -q --filter "name=society-voice-gate" | wc -l | xargs -I{} echo "{} running"
echo -n "    Dev Tunnel:  " && (pgrep -f "devtunnel host" > /dev/null && echo "still running" || echo "stopped")
echo ""
echo "Done! To restart: ./restart-all.sh"
