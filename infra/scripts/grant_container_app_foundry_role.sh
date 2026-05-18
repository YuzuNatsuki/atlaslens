#!/usr/bin/env bash
# Grant the Container App's system-assigned managed identity the "Azure AI User"
# role on the Foundry account, so the Analyzer can call Foundry Agent Service
# via DefaultAzureCredential (no API keys for Agent threads).
#
# Idempotent: skips when the assignment already exists.
#
# Usage: ./grant_container_app_foundry_role.sh

set -euo pipefail

RG="${RG:-atlaslens-rg}"
APP="${APP:-atlaslens-backend}"
FOUNDRY="${FOUNDRY:-atlaslens-foundry}"
ROLE="${ROLE:-Azure AI Developer}"

SUB=$(az account show --query id -o tsv)
SCOPE="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${FOUNDRY}"

echo "==> Reading Container App identity"
PID=$(az containerapp show -g "${RG}" -n "${APP}" --query "identity.principalId" -o tsv 2>/dev/null || true)
if [[ -z "${PID}" || "${PID}" == "null" ]]; then
  echo "Container App ${APP} has no managed identity. Enabling SystemAssigned..."
  az containerapp identity assign -g "${RG}" -n "${APP}" --system-assigned -o none
  PID=$(az containerapp show -g "${RG}" -n "${APP}" --query "identity.principalId" -o tsv)
fi
echo "principal_id=${PID}"

echo "==> Ensuring role assignment (${ROLE})"
az role assignment create \
  --role "${ROLE}" \
  --assignee-object-id "${PID}" \
  --assignee-principal-type ServicePrincipal \
  --scope "${SCOPE}" \
  -o tsv --query roleDefinitionId 2>&1 | tail -1 || true

echo "Done."
