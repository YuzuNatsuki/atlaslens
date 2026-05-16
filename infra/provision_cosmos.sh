#!/usr/bin/env bash
# Provision an Azure Cosmos DB (NoSQL, serverless) account for AtlasLens.
#
# Creates:
#   - Cosmos account (Serverless)
#   - Database "atlaslens"
#   - Containers: members, goals, daily_reports, one_on_ones, meetings, prep_notes
#
# Updates the Container App backend's env vars with the new endpoint/key,
# and patches ../.env so local dev picks them up too.
#
# Usage:  ./infra/provision_cosmos.sh

set -euo pipefail

PREFIX="${PREFIX:-atlaslens}"
REGION="${REGION:-japaneast}"
RG="${RG:-${PREFIX}-rg}"
ACCOUNT="${ACCOUNT:-${PREFIX}-cosmos}"
DB="${DB:-atlaslens}"
BACKEND_APP="${BACKEND_APP:-${PREFIX}-backend}"

cyan() { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

cyan "==> Ensuring Microsoft.DocumentDB provider is registered"
state=$(az provider show -n Microsoft.DocumentDB --query registrationState -o tsv 2>/dev/null || echo NotRegistered)
if [[ "$state" != "Registered" ]]; then
  az provider register --namespace Microsoft.DocumentDB --wait
fi

cyan "==> Cosmos DB account: ${ACCOUNT} (serverless, ${REGION})"
EXISTING="$(az cosmosdb show -g "${RG}" -n "${ACCOUNT}" --query name -o tsv 2>/dev/null || true)"
if [[ -z "${EXISTING}" ]]; then
  az cosmosdb create \
    -g "${RG}" -n "${ACCOUNT}" \
    --kind GlobalDocumentDB \
    --capabilities EnableServerless \
    --locations "regionName=${REGION}" \
    --default-consistency-level Session \
    -o table
else
  echo "  Cosmos account already exists."
fi

cyan "==> Database: ${DB}"
az cosmosdb sql database show -g "${RG}" -a "${ACCOUNT}" -n "${DB}" -o table 2>/dev/null \
  || az cosmosdb sql database create -g "${RG}" -a "${ACCOUNT}" -n "${DB}" -o table

cyan "==> Containers"
declare -A CONTAINERS=(
  [members]="/id"
  [goals]="/member_id"
  [daily_reports]="/member_id"
  [one_on_ones]="/member_id"
  [meetings]="/id"
  [prep_notes]="/member_id"
)

for name in "${!CONTAINERS[@]}"; do
  pk="${CONTAINERS[$name]}"
  az cosmosdb sql container show -g "${RG}" -a "${ACCOUNT}" -d "${DB}" -n "${name}" -o tsv --query name 2>/dev/null \
    || az cosmosdb sql container create -g "${RG}" -a "${ACCOUNT}" -d "${DB}" \
        -n "${name}" --partition-key-path "${pk}" -o table
done

cyan "==> Fetching connection info"
ENDPOINT="$(az cosmosdb show -g "${RG}" -n "${ACCOUNT}" --query documentEndpoint -o tsv)"
KEY="$(az cosmosdb keys list -g "${RG}" -n "${ACCOUNT}" --query primaryMasterKey -o tsv)"

green "Endpoint: ${ENDPOINT}"

cyan "==> Patching ${ENV_FILE}"
python3 - <<PY
from pathlib import Path
path = Path("${ENV_FILE}")
existing = path.read_text(encoding="utf-8") if path.exists() else ""
updates = {
    "COSMOS_ENDPOINT": "${ENDPOINT}",
    "COSMOS_KEY": "${KEY}",
    "COSMOS_DATABASE": "${DB}",
}
lines = existing.splitlines()
keys_present = set()
new_lines = []
for line in lines:
    key = line.split("=", 1)[0] if "=" in line else ""
    if key in updates:
        new_lines.append(f"{key}={updates[key]}")
        keys_present.add(key)
    else:
        new_lines.append(line)
for k, v in updates.items():
    if k not in keys_present:
        new_lines.append(f"{k}={v}")
path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
print(f"wrote {path}")
PY

cyan "==> Pushing env vars + secrets onto Container App ${BACKEND_APP}"
az containerapp secret set \
  -g "${RG}" -n "${BACKEND_APP}" \
  --secrets "cosmos-key=${KEY}" \
  -o table >/dev/null

az containerapp update \
  -g "${RG}" -n "${BACKEND_APP}" \
  --set-env-vars \
      "COSMOS_ENDPOINT=${ENDPOINT}" \
      "COSMOS_KEY=secretref:cosmos-key" \
      "COSMOS_DATABASE=${DB}" \
  -o table

green "==> Cosmos provisioned and Backend env updated. Redeploy backend image to pick up code changes."
