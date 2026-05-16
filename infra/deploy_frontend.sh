#!/usr/bin/env bash
# Build the AtlasLens frontend and deploy it to Azure Static Web Apps.
#
# Provisions (creating only if missing):
#   - Azure Static Web App (Free tier, no GitHub backing)
#
# Steps:
#   1. Discover the backend URL from the Container App fqdn
#   2. Write frontend/.env.production with VITE_API_BASE
#   3. pnpm install + pnpm build (requires nvm Node already active)
#   4. Install @azure/static-web-apps-cli locally and deploy ./dist
#
# Pre-requisites:
#   - `az login` done
#   - deploy_backend.sh has been run (we resolve the Container App)
#   - pnpm + node available (nvm)
#
# Usage:
#   ./infra/deploy_frontend.sh

set -euo pipefail

PREFIX="${PREFIX:-atlaslens}"
REGION="${REGION:-eastasia}"          # Static Web Apps Free is not in japaneast — eastasia is closest
RG="${RG:-${PREFIX}-rg}"
SWA_NAME="${SWA_NAME:-${PREFIX}-web}"
BACKEND_APP="${BACKEND_APP:-${PREFIX}-backend}"

cyan() { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONT_DIR="${ROOT_DIR}/frontend"

cyan "==> Ensuring required resource provider is registered"
state=$(az provider show -n Microsoft.Web --query registrationState -o tsv 2>/dev/null || echo NotRegistered)
if [[ "$state" != "Registered" ]]; then
  yellow "  registering Microsoft.Web (currently $state)…"
  az provider register --namespace Microsoft.Web --wait
fi

cyan "==> Discovering backend URL"
BACKEND_FQDN="$(az containerapp show -g "${RG}" -n "${BACKEND_APP}" --query "properties.configuration.ingress.fqdn" -o tsv)"
BACKEND_URL="https://${BACKEND_FQDN}"
green "    ${BACKEND_URL}"

cyan "==> Writing ${FRONT_DIR}/.env.production"
echo "VITE_API_BASE=${BACKEND_URL}" > "${FRONT_DIR}/.env.production"

cyan "==> Static Web App: ${SWA_NAME}"
EXISTING="$(az staticwebapp show -g "${RG}" -n "${SWA_NAME}" --query name -o tsv 2>/dev/null || true)"
if [[ -z "${EXISTING}" ]]; then
  az staticwebapp create \
    -g "${RG}" -n "${SWA_NAME}" \
    --location "${REGION}" \
    --sku Free \
    -o table
else
  yellow "Static Web App exists — re-using it"
fi

DEPLOY_TOKEN="$(az staticwebapp secrets list -g "${RG}" -n "${SWA_NAME}" --query "properties.apiKey" -o tsv)"

cyan "==> Building frontend"
# nvm refuses to load when PREFIX is set (script uses PREFIX for resource naming).
# Unset it for the build subshell only.
(
  unset PREFIX
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  # shellcheck disable=SC1091
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  cd "${FRONT_DIR}"
  pnpm install --frozen-lockfile=false
  pnpm build
)

cyan "==> Deploying ./dist via swa CLI"
(
  unset PREFIX
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  # shellcheck disable=SC1091
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  cd "${FRONT_DIR}"
  npx --yes @azure/static-web-apps-cli@latest deploy ./dist \
    --deployment-token "${DEPLOY_TOKEN}" \
    --env production \
    --no-use-keychain
)

FRONT_URL="https://$(az staticwebapp show -g "${RG}" -n "${SWA_NAME}" --query defaultHostname -o tsv)"
green "==> Frontend deployed:"
green "    ${FRONT_URL}"
echo
cyan "Open in browser:"
echo "  open ${FRONT_URL}"
