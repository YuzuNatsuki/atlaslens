#!/usr/bin/env bash
# Deploy the AtlasLens backend to Azure Container Apps.
#
# Provisions (creating only if missing):
#   - Azure Container Registry (atlaslensacr<suffix>)
#   - Log Analytics workspace
#   - Container Apps managed environment
#   - The backend Container App, pulling its image from ACR
#
# Builds the image with `az acr build` (no local Docker required), reads the
# Azure OpenAI credentials from ../.env, and wires them as secrets into the app.
#
# Pre-requisites:
#   - `az login` done, subscription selected
#   - infra/provision_openai.sh already ran (we read its outputs from .env)
#
# Usage:
#   ./infra/deploy_backend.sh

set -euo pipefail

PREFIX="${PREFIX:-atlaslens}"
REGION="${REGION:-japaneast}"
RG="${RG:-${PREFIX}-rg}"
ACR_SUFFIX="${ACR_SUFFIX:-$(az account show --query id -o tsv | tr -d '-' | cut -c1-6)}"
ACR_NAME="${ACR_NAME:-${PREFIX}acr${ACR_SUFFIX}}"
LOGS_NAME="${LOGS_NAME:-${PREFIX}-logs}"
ENV_NAME="${ENV_NAME:-${PREFIX}-env}"
APP_NAME="${APP_NAME:-${PREFIX}-backend}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M%S)}"
IMAGE_NAME="${IMAGE_NAME:-atlaslens-backend}"

cyan() { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: ${ENV_FILE} not found — run infra/provision_openai.sh first." >&2
  exit 1
fi

# shellcheck disable=SC2046
export $(grep -E '^[A-Z_]+=' "${ENV_FILE}" | xargs -0 2>/dev/null) >/dev/null 2>&1 || true
# Re-load via python to handle special chars
eval "$(python3 - <<PY
from pathlib import Path
for line in Path("${ENV_FILE}").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        print(f"export {k.strip()}={v.strip()!r}")
PY
)"

: "${AZURE_OPENAI_ENDPOINT:?AZURE_OPENAI_ENDPOINT missing in .env}"
: "${AZURE_OPENAI_API_KEY:?AZURE_OPENAI_API_KEY missing in .env}"

cyan "==> Active subscription"
az account show --query "{name:name, id:id}" -o table

cyan "==> Ensuring required resource providers are registered"
for p in Microsoft.ContainerRegistry Microsoft.App Microsoft.OperationalInsights Microsoft.Insights; do
  state=$(az provider show -n "$p" --query registrationState -o tsv 2>/dev/null || echo NotRegistered)
  if [[ "$state" != "Registered" ]]; then
    yellow "  registering $p (currently $state)…"
    az provider register --namespace "$p" --wait
  fi
done

cyan "==> Resource group: ${RG}"
az group show -n "${RG}" -o table 2>/dev/null \
  || az group create --name "${RG}" --location "${REGION}" -o table

cyan "==> Container Registry: ${ACR_NAME}"
az acr show -n "${ACR_NAME}" -o table 2>/dev/null \
  || az acr create -n "${ACR_NAME}" -g "${RG}" --sku Basic --admin-enabled true -o table

cyan "==> Building image ${IMAGE_NAME}:${IMAGE_TAG} on ACR"
az acr build \
  --registry "${ACR_NAME}" \
  --image "${IMAGE_NAME}:${IMAGE_TAG}" \
  --image "${IMAGE_NAME}:latest" \
  --file backend/Dockerfile \
  "${ROOT_DIR}" \
  -o table

cyan "==> Log Analytics workspace: ${LOGS_NAME}"
az monitor log-analytics workspace show -g "${RG}" -n "${LOGS_NAME}" -o table 2>/dev/null \
  || az monitor log-analytics workspace create -g "${RG}" -n "${LOGS_NAME}" -o table

LOG_WS_ID="$(az monitor log-analytics workspace show -g "${RG}" -n "${LOGS_NAME}" --query customerId -o tsv)"
LOG_WS_KEY="$(az monitor log-analytics workspace get-shared-keys -g "${RG}" -n "${LOGS_NAME}" --query primarySharedKey -o tsv)"

cyan "==> Container Apps env: ${ENV_NAME}"
az containerapp env show -g "${RG}" -n "${ENV_NAME}" -o table 2>/dev/null \
  || az containerapp env create \
      -g "${RG}" -n "${ENV_NAME}" \
      --location "${REGION}" \
      --logs-workspace-id "${LOG_WS_ID}" \
      --logs-workspace-key "${LOG_WS_KEY}" \
      -o table

cyan "==> Granting Container Apps env pull access on ACR"
ACR_LOGIN_SERVER="$(az acr show -n "${ACR_NAME}" --query loginServer -o tsv)"
ACR_USERNAME="$(az acr credential show -n "${ACR_NAME}" --query username -o tsv)"
ACR_PASSWORD="$(az acr credential show -n "${ACR_NAME}" --query "passwords[0].value" -o tsv)"

cyan "==> Container App: ${APP_NAME}"
EXISTING="$(az containerapp show -g "${RG}" -n "${APP_NAME}" -o tsv --query name 2>/dev/null || true)"

if [[ -z "${EXISTING}" ]]; then
  az containerapp create \
    -g "${RG}" -n "${APP_NAME}" \
    --environment "${ENV_NAME}" \
    --image "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}" \
    --registry-server "${ACR_LOGIN_SERVER}" \
    --registry-username "${ACR_USERNAME}" \
    --registry-password "${ACR_PASSWORD}" \
    --target-port 8000 \
    --ingress external \
    --cpu 0.5 --memory 1.0Gi \
    --min-replicas 0 --max-replicas 2 \
    --secrets \
        "openai-key=${AZURE_OPENAI_API_KEY}" \
    --env-vars \
        "AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}" \
        "AZURE_OPENAI_API_KEY=secretref:openai-key" \
        "AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION:-2024-10-21}" \
        "AZURE_OPENAI_CHAT_DEPLOYMENT=${AZURE_OPENAI_CHAT_DEPLOYMENT:-gpt-4o}" \
        "AZURE_OPENAI_CHAT_DEPLOYMENT_FAST=${AZURE_OPENAI_CHAT_DEPLOYMENT_FAST:-gpt-4o}" \
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=${AZURE_OPENAI_EMBEDDING_DEPLOYMENT:-text-embedding-3-large}" \
        "APP_ENV=container" \
    -o table
else
  yellow "Container App exists — updating image and env vars"
  az containerapp secret set \
    -g "${RG}" -n "${APP_NAME}" \
    --secrets "openai-key=${AZURE_OPENAI_API_KEY}" \
    -o table
  az containerapp update \
    -g "${RG}" -n "${APP_NAME}" \
    --image "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}" \
    --set-env-vars \
        "AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}" \
        "AZURE_OPENAI_API_KEY=secretref:openai-key" \
        "AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION:-2024-10-21}" \
        "AZURE_OPENAI_CHAT_DEPLOYMENT=${AZURE_OPENAI_CHAT_DEPLOYMENT:-gpt-4o}" \
        "AZURE_OPENAI_CHAT_DEPLOYMENT_FAST=${AZURE_OPENAI_CHAT_DEPLOYMENT_FAST:-gpt-4o}" \
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=${AZURE_OPENAI_EMBEDDING_DEPLOYMENT:-text-embedding-3-large}" \
        "APP_ENV=container" \
    -o table
fi

BACKEND_FQDN="$(az containerapp show -g "${RG}" -n "${APP_NAME}" --query "properties.configuration.ingress.fqdn" -o tsv)"
BACKEND_URL="https://${BACKEND_FQDN}"

green "==> Backend deployed:"
green "    ${BACKEND_URL}"
echo
cyan "Health check:"
echo "  curl -s ${BACKEND_URL}/api/health/team | jq ."
echo
cyan "Save the URL into the frontend env (used by VITE_API_BASE):"
echo "  echo VITE_API_BASE=${BACKEND_URL} > frontend/.env.production"
