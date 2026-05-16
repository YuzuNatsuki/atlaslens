#!/usr/bin/env bash
# Bootstrap the Azure Storage Account that holds the Terraform remote state.
# Runs ONCE per subscription.
#
# Outputs the storage account name to stdout; pipe into terraform init:
#   az login
#   STORAGE=$(./infra/scripts/bootstrap_tfstate.sh)
#   cd infra/terraform
#   terraform init -backend-config="storage_account_name=$STORAGE"

set -euo pipefail

PREFIX="${PREFIX:-atlaslens}"
REGION="${REGION:-japaneast}"
RG="${RG:-${PREFIX}-tfstate-rg}"
SUFFIX="${SUFFIX:-$(az account show --query id -o tsv | tr -d '-' | cut -c1-6)}"
STORAGE="${STORAGE:-${PREFIX}tfstate${SUFFIX}}"
CONTAINER="${CONTAINER:-tfstate}"

echo "==> Resource group: ${RG}" >&2
az group create --name "${RG}" --location "${REGION}" -o none

echo "==> Storage account: ${STORAGE}" >&2
az storage account create \
  --name "${STORAGE}" \
  --resource-group "${RG}" \
  --location "${REGION}" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --allow-blob-public-access false \
  --min-tls-version TLS1_2 \
  -o none

echo "==> Enable AAD auth for blob (no shared keys in CI)" >&2
az storage account update \
  --name "${STORAGE}" --resource-group "${RG}" \
  --allow-shared-key-access false \
  -o none || true

echo "==> Grant current principal Storage Blob Data Contributor on the account" >&2
USER_ID=$(az ad signed-in-user show --query id -o tsv)
SUB=$(az account show --query id -o tsv)
SCOPE="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.Storage/storageAccounts/${STORAGE}"
az role assignment create \
  --assignee-object-id "${USER_ID}" --assignee-principal-type User \
  --role "Storage Blob Data Contributor" \
  --scope "${SCOPE}" -o none || true

# Wait briefly for RBAC propagation before creating the container with AAD auth.
sleep 30

echo "==> Container: ${CONTAINER}" >&2
az storage container create \
  --account-name "${STORAGE}" \
  --auth-mode login \
  --name "${CONTAINER}" \
  -o none

echo "${STORAGE}"
