#!/usr/bin/env bash
# Provision an Azure AI Foundry Hub + Project in the AtlasLens resource group.
#
# Layout:
#   atlaslens-rg
#     ├─ atlaslens-aoai         (existing CognitiveServices/OpenAI — kept)
#     ├─ atlaslens-foundry-hub  (NEW: AML workspace, kind=hub)
#     └─ atlaslens-foundry-proj (NEW: AML workspace, kind=project — child of the hub)
#
# Also creates the support resources the Hub needs (Storage + Key Vault) and
# wires an "Azure OpenAI" connection in the Project so agents can call the
# existing gpt-4o + embedding deployments without re-deployment.
#
# Usage:  ./infra/provision_foundry.sh

set -euo pipefail

PREFIX="${PREFIX:-atlaslens}"
REGION="${REGION:-japaneast}"
RG="${RG:-${PREFIX}-rg}"

HUB="${HUB:-${PREFIX}-foundry-hub}"
PROJECT="${PROJECT:-${PREFIX}-foundry-proj}"
AOAI_NAME="${AOAI_NAME:-${PREFIX}-aoai}"

# Names for Hub-required resources — pick globally unique by suffixing sub id hash.
SUFFIX="${SUFFIX:-$(az account show --query id -o tsv | tr -d '-' | cut -c1-6)}"
STORAGE_NAME="${STORAGE_NAME:-${PREFIX}fdy${SUFFIX}}"  # storage: lowercase, 3-24 chars, no dashes
KV_NAME="${KV_NAME:-${PREFIX}-kv-${SUFFIX}}"
APPI_NAME="${APPI_NAME:-${PREFIX}-appi}"

cyan() { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

cyan "==> Subscription"
az account show --query "{name:name, id:id}" -o table

cyan "==> Ensuring required providers"
for p in Microsoft.MachineLearningServices Microsoft.KeyVault Microsoft.Storage; do
  state=$(az provider show -n "$p" --query registrationState -o tsv 2>/dev/null || echo NotRegistered)
  if [[ "$state" != "Registered" ]]; then
    yellow "  registering $p"
    az provider register --namespace "$p" --wait
  fi
done

cyan "==> Storage account: ${STORAGE_NAME}"
az storage account show -g "${RG}" -n "${STORAGE_NAME}" -o tsv --query name 2>/dev/null \
  || az storage account create \
      -g "${RG}" -n "${STORAGE_NAME}" -l "${REGION}" \
      --sku Standard_LRS --kind StorageV2 --allow-blob-public-access false \
      -o tsv --query name

cyan "==> Key Vault: ${KV_NAME}"
az keyvault show -g "${RG}" -n "${KV_NAME}" -o tsv --query name 2>/dev/null \
  || az keyvault create \
      -g "${RG}" -n "${KV_NAME}" -l "${REGION}" \
      --enable-rbac-authorization true \
      -o tsv --query name

cyan "==> Application Insights (re-use existing if present): ${APPI_NAME}"
az monitor app-insights component show -g "${RG}" --app "${APPI_NAME}" -o tsv --query name 2>/dev/null \
  || az monitor app-insights component create \
      -g "${RG}" --app "${APPI_NAME}" --location "${REGION}" --kind web \
      -o tsv --query name

cyan "==> Resource IDs"
SUB=$(az account show --query id -o tsv)
STORAGE_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.Storage/storageAccounts/${STORAGE_NAME}"
KV_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.KeyVault/vaults/${KV_NAME}"
APPI_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/microsoft.insights/components/${APPI_NAME}"

cyan "==> Foundry Hub: ${HUB}"
EXISTING_HUB=$(az ml workspace show -g "${RG}" -n "${HUB}" --query name -o tsv 2>/dev/null || true)
if [[ -z "${EXISTING_HUB}" ]]; then
  cat >/tmp/hub.yaml <<EOF
\$schema: https://azuremlschemas.azureedge.net/latest/hub.schema.json
name: ${HUB}
display_name: AtlasLens Foundry Hub
location: ${REGION}
storage_account: ${STORAGE_ID}
key_vault: ${KV_ID}
application_insights: ${APPI_ID}
public_network_access: enabled
EOF
  az ml workspace create --kind hub -g "${RG}" --file /tmp/hub.yaml -o tsv --query name
else
  echo "  hub exists, reusing."
fi
HUB_ID=$(az ml workspace show -g "${RG}" -n "${HUB}" --query id -o tsv)
echo "  hub id: ${HUB_ID}"

cyan "==> Foundry Project: ${PROJECT}"
EXISTING_PROJECT=$(az ml workspace show -g "${RG}" -n "${PROJECT}" --query name -o tsv 2>/dev/null || true)
if [[ -z "${EXISTING_PROJECT}" ]]; then
  cat >/tmp/project.yaml <<EOF
\$schema: https://azuremlschemas.azureedge.net/latest/project.schema.json
name: ${PROJECT}
display_name: AtlasLens
location: ${REGION}
hub_id: ${HUB_ID}
EOF
  az ml workspace create --kind project -g "${RG}" --file /tmp/project.yaml -o tsv --query name
else
  echo "  project exists, reusing."
fi
PROJECT_ID=$(az ml workspace show -g "${RG}" -n "${PROJECT}" --query id -o tsv)
echo "  project id: ${PROJECT_ID}"

cyan "==> Linking existing Azure OpenAI as a Project connection"
AOAI_ENDPOINT=$(az cognitiveservices account show -g "${RG}" -n "${AOAI_NAME}" --query properties.endpoint -o tsv)
AOAI_KEY=$(az cognitiveservices account keys list -g "${RG}" -n "${AOAI_NAME}" --query key1 -o tsv)
AOAI_RES_ID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${AOAI_NAME}"

cat >/tmp/aoai_conn.yaml <<EOF
\$schema: https://azuremlschemas.azureedge.net/latest/azureOpenAIConnection.schema.json
name: atlaslens_aoai
type: azure_open_ai
azure_endpoint: ${AOAI_ENDPOINT}
api_version: "2024-10-21"
api_key: ${AOAI_KEY}
target: ${AOAI_RES_ID}
EOF

EXISTING_CONN=$(az ml connection show -g "${RG}" --workspace-name "${PROJECT}" -n atlaslens_aoai --query name -o tsv 2>/dev/null || true)
if [[ -z "${EXISTING_CONN}" ]]; then
  az ml connection create -g "${RG}" --workspace-name "${PROJECT}" --file /tmp/aoai_conn.yaml -o tsv --query name
else
  az ml connection update -g "${RG}" --workspace-name "${PROJECT}" --file /tmp/aoai_conn.yaml -o tsv --query name 2>&1 | tail -2
fi

cyan "==> Discovery endpoint for the Project (used by azure-ai-projects SDK)"
DISCOVERY=$(az ml workspace show -g "${RG}" -n "${PROJECT}" --query discovery_url -o tsv)
echo "  discovery_url: ${DISCOVERY}"

cyan "==> Patching ${ENV_FILE}"
python3 - <<PY
from pathlib import Path
p = Path("${ENV_FILE}")
lines = p.read_text().splitlines() if p.exists() else []
updates = {
    "FOUNDRY_PROJECT_NAME": "${PROJECT}",
    "FOUNDRY_HUB_NAME": "${HUB}",
    "FOUNDRY_RESOURCE_GROUP": "${RG}",
    "FOUNDRY_SUBSCRIPTION_ID": "${SUB}",
    "FOUNDRY_DISCOVERY_URL": "${DISCOVERY}",
    "FOUNDRY_AOAI_CONNECTION": "atlaslens_aoai",
}
seen = set()
out = []
for line in lines:
    k = line.split("=",1)[0] if "=" in line else ""
    if k in updates:
        out.append(f"{k}={updates[k]}")
        seen.add(k)
    else:
        out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
p.write_text("\n".join(out) + "\n")
print("patched")
PY

green "==> Foundry Hub + Project ready"
echo "  hub:     ${HUB}"
echo "  project: ${PROJECT}"
echo "  connection: atlaslens_aoai → ${AOAI_NAME}"
