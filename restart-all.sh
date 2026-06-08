#!/bin/bash
# restart-all.sh — Restart society-voice-gate dev environment after WSL crash
set -e

PROJECT=~/society-voice-gate
TENANT="e6e6c3b7-14a4-4b8a-940e-37cf5d6507c7"
DEVTUNNEL=~/bin/devtunnel
ACS_RESOURCE_ID="/subscriptions/ea29cfe1-fa2f-4f97-b953-c5fc0da75219/resourceGroups/society-demo-rg/providers/Microsoft.Communication/communicationServices/societyacs"
EVENT_SUBSCRIPTION_NAME="incoming-call-sub"

update_callback_host() {
	local env_file="$1"
	local tunnel_url="$2"

	if grep -q '^CALLBACK_HOST=' "$env_file"; then
		sed -i "s|^CALLBACK_HOST=.*$|CALLBACK_HOST=$tunnel_url|" "$env_file"
	else
		printf '\nCALLBACK_HOST=%s\n' "$tunnel_url" >> "$env_file"
	fi
}

update_event_subscription() {
	local tunnel_url="$1"

	az eventgrid event-subscription update \
		--name "$EVENT_SUBSCRIPTION_NAME" \
		--source-resource-id "$ACS_RESOURCE_ID" \
		--endpoint "$tunnel_url/api/incoming-call" \
		-o none
}

echo "=== 1/5  Fix .azure permissions ==="
sudo chown -R $(whoami):$(whoami) ~/.azure 2>/dev/null || true

echo "=== 2/5  Azure login ==="
az account show -o none 2>/dev/null || az login --use-device-code --tenant "$TENANT"

echo "=== 3/5  Start Dev Tunnel (background) ==="
pkill -f "devtunnel host" 2>/dev/null || true
nohup "$DEVTUNNEL" host -p 8000 --protocol http --allow-anonymous > /tmp/devtunnel.log 2>&1 &
sleep 3
echo "    Tunnel PID: $!"
TUNNEL_URL=$(grep -oP 'https://[^, ]+-8000\.[^, ]+\.devtunnels\.ms' /tmp/devtunnel.log | head -1)
if [[ -z "$TUNNEL_URL" ]]; then
	echo "    Failed to detect tunnel URL"
	cat /tmp/devtunnel.log
	exit 1
fi
echo "    Tunnel URL: $TUNNEL_URL"

update_callback_host "$PROJECT/.env" "$TUNNEL_URL"
update_callback_host "$PROJECT/backend/.env" "$TUNNEL_URL"

echo "=== 3.5/5  Update Azure Event Subscription ==="
update_event_subscription "$TUNNEL_URL"

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