#!/usr/bin/env bash
# postprovision.sh — Write provisioned resource values into .env files
set -euo pipefail

echo "==> Fetching ACS connection string..."
ACS_CONNECTION_STRING=$(az communication list-key \
    --name "$ACS_NAME" \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --query primaryConnectionString -o tsv)

echo "==> Writing .env files..."

ENV_CONTENT="# ── Azure Communication Services ─────────────────────────────────────────────
ACS_CONNECTION_STRING=${ACS_CONNECTION_STRING}
ACS_PHONE_NUMBER=\${ACS_PHONE_NUMBER:-REPLACE_AFTER_PURCHASING_NUMBER}

# ── Azure AI Services (Cognitive Services endpoint for Voice Live API) ───────
COGNITIVE_SERVICES_ENDPOINT=${COGNITIVE_SERVICES_ENDPOINT}
VOICE_LIVE_MODEL=gpt-4o-mini

# ── Foundry Agent — fetches instructions & voice config from Foundry ─────────
FOUNDRY_AGENT_NAME=\${FOUNDRY_AGENT_NAME:-REPLACE_WITH_YOUR_AGENT_NAME}
FOUNDRY_PROJECT_ENDPOINT=\${FOUNDRY_PROJECT_ENDPOINT:-REPLACE_WITH_YOUR_PROJECT_ENDPOINT}

# ── Azure OpenAI — ticket classification after call ends ─────────────────────
AZURE_OPENAI_ENDPOINT=${COGNITIVE_SERVICES_ENDPOINT}
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini

# ── App ───────────────────────────────────────────────────────────────────────
CALLBACK_HOST=\${CALLBACK_HOST:-https://REPLACE_WITH_YOUR_DEVTUNNEL_URL}
LOG_LEVEL=INFO"

# Root .env (used by compose)
echo "$ENV_CONTENT" > .env
echo "    Written .env"

# Backend .env (used when running without compose)
echo "$ENV_CONTENT" > backend/.env
echo "    Written backend/.env"

echo ""
echo "==> Provisioning complete!"
echo ""
echo "    Cognitive Services: ${COGNITIVE_SERVICES_ENDPOINT}"
echo "    ACS resource:       ${ACS_NAME}"
echo ""
echo "    ⚠️  MANUAL STEPS STILL NEEDED:"
echo "    1. Purchase a phone number:       Azure Portal → ${ACS_NAME} → Phone Numbers"
echo "    2. Set ACS_PHONE_NUMBER in .env:  The E.164 number you purchased (e.g. +18331234567)"
echo "    3. Create a Foundry agent:        ai.azure.com → Agents → Create → enable Voice mode"
echo "    4. Set FOUNDRY_AGENT_NAME and FOUNDRY_PROJECT_ENDPOINT in .env"
echo "    5. Create EventGrid subscription: ACS → Events → IncomingCall → Webhook"
echo "    6. Set CALLBACK_HOST in .env:     Your Dev Tunnel URL (no trailing slash)"
