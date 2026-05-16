#!/usr/bin/env bash
# Set up Workload Identity Federation between GitHub Actions and Azure.
#
# Creates:
#   - Entra app registration `${APP_NAME}` + service principal
#   - Contributor role on the subscription (broad scope for the demo)
#   - User Access Administrator on the RG (needed to manage role assignments
#     for the Container App managed identity)
#   - Federated credentials for: main branch, pull_request, and tags
#   - GitHub Actions repository secrets: AZURE_CLIENT_ID / TENANT_ID / SUBSCRIPTION_ID
#
# Pre-requisites:
#   - az login
#   - gh auth login
#   - the GitHub repo already exists (we read owner/name from `gh repo view`)
#
# Usage:  ./infra/scripts/setup_oidc.sh

set -euo pipefail

APP_NAME="${APP_NAME:-atlaslens-github-actions}"
REPO_FULLNAME="${REPO_FULLNAME:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
SUB=$(az account show --query id -o tsv)
TENANT=$(az account show --query tenantId -o tsv)
RG="${RG:-atlaslens-rg}"

cyan() { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }

cyan "==> Subscription: ${SUB}  Tenant: ${TENANT}  Repo: ${REPO_FULLNAME}"

cyan "==> App registration"
APP_ID=$(az ad app list --display-name "${APP_NAME}" --query "[0].appId" -o tsv)
if [[ -z "${APP_ID}" ]]; then
  APP_ID=$(az ad app create --display-name "${APP_NAME}" --query appId -o tsv)
  echo "  created appId=${APP_ID}"
else
  echo "  reusing existing appId=${APP_ID}"
fi

cyan "==> Service principal"
az ad sp show --id "${APP_ID}" --query id -o tsv 2>/dev/null \
  || az ad sp create --id "${APP_ID}" --query id -o tsv

SP_OBJECT_ID=$(az ad sp show --id "${APP_ID}" --query id -o tsv)

cyan "==> Subscription roles"
for role in "Contributor" "User Access Administrator"; do
  az role assignment create \
    --role "${role}" \
    --assignee-object-id "${SP_OBJECT_ID}" \
    --assignee-principal-type ServicePrincipal \
    --scope "/subscriptions/${SUB}" \
    -o tsv --query roleDefinitionId 2>&1 | tail -1 || true
done

cyan "==> Foundry data-plane roles on atlaslens-foundry"
FOUNDRY_SCOPE="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/atlaslens-foundry"
az role assignment create \
  --role "Azure AI Administrator" \
  --assignee-object-id "${SP_OBJECT_ID}" \
  --assignee-principal-type ServicePrincipal \
  --scope "${FOUNDRY_SCOPE}" \
  -o tsv --query roleDefinitionId 2>&1 | tail -1 || true

cyan "==> Federated credentials"
ensure_federated_credential() {
  local name="$1"; local subject="$2"
  # Drop and re-create to keep idempotency.
  az ad app federated-credential delete --id "${APP_ID}" --federated-credential-id "${name}" 2>/dev/null || true
  az ad app federated-credential create \
    --id "${APP_ID}" \
    --parameters "$(cat <<EOF
{
  "name": "${name}",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "${subject}",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF
)" -o tsv --query name
}
ensure_federated_credential "main-branch"  "repo:${REPO_FULLNAME}:ref:refs/heads/main"
ensure_federated_credential "pull-request" "repo:${REPO_FULLNAME}:pull_request"
ensure_federated_credential "infra-env"    "repo:${REPO_FULLNAME}:environment:production"

cyan "==> Push GitHub Actions secrets"
gh secret set AZURE_CLIENT_ID --body "${APP_ID}"
gh secret set AZURE_TENANT_ID --body "${TENANT}"
gh secret set AZURE_SUBSCRIPTION_ID --body "${SUB}"
gh secret set TF_STATE_STORAGE_ACCOUNT --body "atlaslenstfstate$(echo ${SUB} | tr -d '-' | cut -c1-6)"

green "==> OIDC ready. Secrets configured for ${REPO_FULLNAME}."
echo
echo "Workflow can authenticate with:"
cat <<'YAML'
  - uses: azure/login@v2
    with:
      client-id: ${{ secrets.AZURE_CLIENT_ID }}
      tenant-id: ${{ secrets.AZURE_TENANT_ID }}
      subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
YAML
