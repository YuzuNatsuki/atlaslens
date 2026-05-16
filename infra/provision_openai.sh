#!/usr/bin/env bash
# Provision a minimal Azure OpenAI footprint for AtlasLens.
#
# Creates:
#   - Resource group (if not present)
#   - Azure OpenAI account (CognitiveServices, kind=OpenAI)
#   - Three model deployments: gpt-4o, gpt-4o-mini, text-embedding-3-large
#
# Outputs the endpoint and key, then patches ../.env so the backend can read them.
#
# Requires: `az login` already done, subscription selected.
#
# Usage:
#   ./infra/provision_openai.sh                   # defaults below
#   PREFIX=mylens REGION=japaneast ./infra/provision_openai.sh

set -euo pipefail

PREFIX="${PREFIX:-atlaslens}"
REGION="${REGION:-japaneast}"        # japaneast: low latency from JP. gpt-4o quota can be tight; fall back to eastus2 if it fails.
RG="${PREFIX}-rg"
ACCOUNT="${PREFIX}-aoai"
SKU="${SKU:-S0}"

# Model deployments. gpt-4o and gpt-4o-mini default capacity = 30K TPM each.
# Embedding has its own quota pool.
GPT4O_DEPLOY="${GPT4O_DEPLOY:-gpt-4o}"
GPT4O_MODEL_VERSION="${GPT4O_MODEL_VERSION:-2024-11-20}"
GPT4O_CAPACITY="${GPT4O_CAPACITY:-30}"

GPT4O_MINI_DEPLOY="${GPT4O_MINI_DEPLOY:-gpt-4o-mini}"
GPT4O_MINI_MODEL_VERSION="${GPT4O_MINI_MODEL_VERSION:-2024-07-18}"
GPT4O_MINI_CAPACITY="${GPT4O_MINI_CAPACITY:-30}"

EMBED_DEPLOY="${EMBED_DEPLOY:-text-embedding-3-large}"
EMBED_MODEL_VERSION="${EMBED_MODEL_VERSION:-1}"
EMBED_CAPACITY="${EMBED_CAPACITY:-30}"

cyan() { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

cyan "==> Active subscription"
az account show --query "{name:name, id:id, tenantId:tenantId}" -o table

cyan "==> Ensuring Microsoft.CognitiveServices provider is registered"
az provider register --namespace Microsoft.CognitiveServices --wait

cyan "==> Resource group: ${RG} (${REGION})"
az group create --name "${RG}" --location "${REGION}" -o table

cyan "==> Azure OpenAI account: ${ACCOUNT}"
az cognitiveservices account create \
  --name "${ACCOUNT}" \
  --resource-group "${RG}" \
  --kind OpenAI \
  --sku "${SKU}" \
  --location "${REGION}" \
  --custom-domain "${ACCOUNT}" \
  --yes \
  -o table

cyan "==> Deploying model: ${GPT4O_DEPLOY} (gpt-4o ${GPT4O_MODEL_VERSION})"
az cognitiveservices account deployment create \
  --name "${ACCOUNT}" \
  --resource-group "${RG}" \
  --deployment-name "${GPT4O_DEPLOY}" \
  --model-name gpt-4o \
  --model-version "${GPT4O_MODEL_VERSION}" \
  --model-format OpenAI \
  --sku-capacity "${GPT4O_CAPACITY}" \
  --sku-name "Standard" \
  -o table || yellow "gpt-4o deployment failed (possibly quota or version mismatch — continuing)"

cyan "==> Deploying model: ${GPT4O_MINI_DEPLOY} (gpt-4o-mini ${GPT4O_MINI_MODEL_VERSION})"
az cognitiveservices account deployment create \
  --name "${ACCOUNT}" \
  --resource-group "${RG}" \
  --deployment-name "${GPT4O_MINI_DEPLOY}" \
  --model-name gpt-4o-mini \
  --model-version "${GPT4O_MINI_MODEL_VERSION}" \
  --model-format OpenAI \
  --sku-capacity "${GPT4O_MINI_CAPACITY}" \
  --sku-name "Standard" \
  -o table || yellow "gpt-4o-mini deployment failed (possibly quota or version mismatch — continuing)"

cyan "==> Deploying model: ${EMBED_DEPLOY} (text-embedding-3-large ${EMBED_MODEL_VERSION})"
az cognitiveservices account deployment create \
  --name "${ACCOUNT}" \
  --resource-group "${RG}" \
  --deployment-name "${EMBED_DEPLOY}" \
  --model-name text-embedding-3-large \
  --model-version "${EMBED_MODEL_VERSION}" \
  --model-format OpenAI \
  --sku-capacity "${EMBED_CAPACITY}" \
  --sku-name "Standard" \
  -o table || yellow "text-embedding-3-large deployment failed (possibly quota — continuing)"

cyan "==> Fetching endpoint and key"
ENDPOINT="$(az cognitiveservices account show \
  --name "${ACCOUNT}" --resource-group "${RG}" \
  --query "properties.endpoint" -o tsv)"
KEY="$(az cognitiveservices account keys list \
  --name "${ACCOUNT}" --resource-group "${RG}" \
  --query "key1" -o tsv)"

green "Endpoint: ${ENDPOINT}"

cyan "==> Patching ${ENV_FILE}"
python3 - <<PY
from pathlib import Path
path = Path("${ENV_FILE}")
existing = path.read_text(encoding="utf-8") if path.exists() else ""
updates = {
    "AZURE_OPENAI_ENDPOINT": "${ENDPOINT}",
    "AZURE_OPENAI_API_KEY": "${KEY}",
    "AZURE_OPENAI_API_VERSION": "2024-10-21",
    "AZURE_OPENAI_CHAT_DEPLOYMENT": "${GPT4O_DEPLOY}",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_FAST": "${GPT4O_MINI_DEPLOY}",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "${EMBED_DEPLOY}",
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

green "==> Done. The backend will read the new values on next start."
echo
echo "Restart the backend:"
echo "  cd ${ROOT_DIR}"
echo "  lsof -ti:8000 | xargs kill -9 2>/dev/null || true"
echo "  source backend/.venv/bin/activate"
echo "  uvicorn app.main:app --port 8000 --host 127.0.0.1 --app-dir backend"
