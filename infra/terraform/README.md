# AtlasLens — Terraform IaC

## Layout

```
infra/terraform/
├── providers.tf       azurerm / azuread / azapi
├── variables.tf       inputs (subscription_id, location, ...)
├── backend.tf         remote state in Azure Storage
├── main.tf            module wiring
├── imports.tf         `import` blocks for the existing live resources
├── outputs.tf         backend_url / frontend_url / endpoints
└── modules/
    ├── observability/     Log Analytics + Application Insights
    ├── cosmos/            Cosmos DB account + DB + 6 containers
    ├── storage/           Storage account used by the AML Hub
    ├── keyvault/          Key Vault used by the AML Hub
    ├── foundry/           AIServices account + gpt-4o + embedding + Foundry project
    ├── foundry_hub/       AML Hub + Project + AOAI connection
    ├── acr/               Azure Container Registry
    ├── container_app/     Container App env + backend app
    └── static_web_app/    Static Web App (frontend)
```

## First-time setup (run once per subscription)

```bash
# 0. Login
az login
gh auth login

# 1. Bootstrap remote state storage
STORAGE=$(./infra/scripts/bootstrap_tfstate.sh)
echo "tfstate storage account: $STORAGE"

# 2. Create the GitHub repo if it doesn't exist
gh repo create atlaslens --public --source=. --remote=origin --push

# 3. Set up OIDC federation between GitHub Actions and Azure
./infra/scripts/setup_oidc.sh

# 4. Initialise Terraform locally
cd infra/terraform
terraform init -backend-config="storage_account_name=$STORAGE"

# 5. Pull existing resources into state (one-shot)
terraform plan \
  -var "subscription_id=$(az account show --query id -o tsv)" \
  -var "tenant_id=$(az account show --query tenantId -o tsv)" \
  -var "jwt_secret=$(cat ../../.env | grep '^JWT_SECRET' | cut -d= -f2)"

# Review the plan. The `imports.tf` blocks should pull every existing
# resource into state with `+/-` (no destroy) — adjust drift if any.

terraform apply \
  -var "subscription_id=$(az account show --query id -o tsv)" \
  -var "tenant_id=$(az account show --query tenantId -o tsv)" \
  -var "jwt_secret=$(cat ../../.env | grep '^JWT_SECRET' | cut -d= -f2)"
```

After that, every push to `main` runs `cd-infra.yml` and applies any drift.
PRs run `ci.yml` which executes `terraform fmt -check && validate && plan`.

## What imports.tf covers

| Module               | Resource type                                         |
|----------------------|-------------------------------------------------------|
| `main`               | `azurerm_resource_group.main`                          |
| `observability`      | Log Analytics + App Insights                          |
| `cosmos`             | account + DB + 6 containers                           |
| `storage`            | Storage account used by the Hub                       |
| `keyvault`           | Key Vault used by the Hub                             |
| `foundry`            | AIServices + gpt-4o + embedding + default project     |
| `foundry_hub`        | AML Hub + Project + AOAI connection                   |
| `acr`                | Container Registry                                     |
| `container_app`      | Container Apps env + backend app                      |
| `static_web_app`     | Static Web App                                         |

The old `atlaslens-aoai` (legacy CognitiveServices/OpenAI account) is NOT
imported; it can be deleted manually once you've confirmed nothing relies on
it.

## CI/CD overview

| Workflow            | Trigger                                          | Does                                   |
|---------------------|--------------------------------------------------|----------------------------------------|
| `ci.yml`            | PR (any path)                                    | backend lint + tests, frontend build, `terraform plan` |
| `cd-infra.yml`      | push to main, paths `infra/terraform/**`         | `terraform apply` to `production` env  |
| `cd-backend.yml`    | push to main, paths `backend/**` `data/**` `infra/prompt_flow/**` | `az acr build` + `containerapp update` |
| `cd-frontend.yml`   | push to main, paths `frontend/**`                | `pnpm build` + Static Web Apps deploy   |

All workflows authenticate to Azure via Workload Identity Federation — no
service-principal secrets in GitHub.
