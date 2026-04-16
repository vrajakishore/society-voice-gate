#!/usr/bin/env bash
# preprovision.sh — Resolve the signed-in user's principal ID for RBAC assignment
set -euo pipefail

echo "==> Resolving signed-in user principal ID..."
AZURE_PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)

if [[ -z "$AZURE_PRINCIPAL_ID" ]]; then
    echo "ERROR: Could not determine signed-in user. Run 'az login' first."
    exit 1
fi

echo "    Principal ID: $AZURE_PRINCIPAL_ID"
azd env set AZURE_PRINCIPAL_ID "$AZURE_PRINCIPAL_ID"
echo "==> Done."
