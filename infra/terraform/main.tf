locals {
  sub_suffix = lower(substr(replace(var.subscription_id, "-", ""), 0, 6))
  acr_name   = "${var.name_prefix}acr${local.sub_suffix}"
}

# Generated JWT secret — never falls back to the dev value in apply runs.
# The override via `var.jwt_secret` (TF_VAR_jwt_secret) wins when supplied,
# otherwise this 48-char random string is used and persisted in state.
resource "random_password" "jwt_secret" {
  length      = 48
  special     = false
  min_lower   = 8
  min_upper   = 8
  min_numeric = 8
}

locals {
  effective_jwt_secret = (
    var.jwt_secret == "atlaslens-dev-secret-change-me" ?
    random_password.jwt_secret.result :
    var.jwt_secret
  )
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "main" {
  name     = "${var.name_prefix}-rg"
  location = var.location
  tags     = var.tags
}

module "observability" {
  source              = "./modules/observability"
  name_prefix         = var.name_prefix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

module "cosmos" {
  source              = "./modules/cosmos"
  name_prefix         = var.name_prefix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

module "storage" {
  source              = "./modules/storage"
  name_prefix         = var.name_prefix
  sub_suffix          = local.sub_suffix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

module "keyvault" {
  source              = "./modules/keyvault"
  name_prefix         = var.name_prefix
  sub_suffix          = local.sub_suffix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  tags                = var.tags
}

module "foundry" {
  source                 = "./modules/foundry"
  name_prefix            = var.name_prefix
  location               = azurerm_resource_group.main.location
  resource_group_name    = azurerm_resource_group.main.name
  gpt4o_capacity_tpm     = var.gpt4o_capacity_tpm
  embedding_capacity_tpm = var.embedding_capacity_tpm
  tags                   = var.tags
}

module "foundry_hub" {
  source                  = "./modules/foundry_hub"
  name_prefix             = var.name_prefix
  location                = azurerm_resource_group.main.location
  resource_group_name     = azurerm_resource_group.main.name
  storage_account_id      = module.storage.foundry_storage_id
  key_vault_id            = module.keyvault.key_vault_id
  application_insights_id = module.observability.application_insights_id
  aoai_connection_name    = "atlaslens_aoai"
  aoai_endpoint           = module.foundry.openai_endpoint
  aoai_api_key            = module.foundry.primary_key
  aoai_resource_id        = module.foundry.account_id
  tags                    = var.tags
}

module "acr" {
  source              = "./modules/acr"
  name                = local.acr_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

module "container_app" {
  source                                 = "./modules/container_app"
  name_prefix                            = var.name_prefix
  location                               = azurerm_resource_group.main.location
  resource_group_name                    = azurerm_resource_group.main.name
  log_analytics_workspace_id             = module.observability.log_analytics_id
  application_insights_connection_string = module.observability.application_insights_connection_string
  image_tag                              = var.backend_image_tag

  registry_login_server = module.acr.login_server
  registry_username     = module.acr.admin_username
  registry_password     = module.acr.admin_password

  openai_endpoint          = module.foundry.openai_endpoint
  openai_api_key           = module.foundry.primary_key
  foundry_project_endpoint = module.foundry.foundry_project_endpoint
  cosmos_endpoint          = module.cosmos.endpoint
  cosmos_key               = module.cosmos.primary_key
  jwt_secret               = local.effective_jwt_secret
  extra_cors_origins       = "https://${var.name_prefix}-web.${module.container_app.environment_default_domain}"
  tags                     = var.tags
}

# NOTE: the Container App MI also needs "Azure AI User" on the Foundry account
# so the Analyzer can talk to Agent Service via AAD. We grant it via
# `infra/scripts/grant_container_app_foundry_role.sh` instead of Terraform
# because the principal_id is (known after apply) on first run, which the
# azurerm_role_assignment resource cannot resolve.

module "frontend_container_app" {
  source                       = "./modules/frontend_container_app"
  name_prefix                  = var.name_prefix
  location                     = azurerm_resource_group.main.location
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = module.container_app.environment_id
  image_tag                    = var.frontend_image_tag
  backend_url                  = module.container_app.backend_url

  registry_login_server = module.acr.login_server
  registry_username     = module.acr.admin_username
  registry_password     = module.acr.admin_password

  tags = var.tags
}

# The pre-existing Static Web App is retained in Terraform for state continuity
# but is no longer the primary frontend. New traffic goes to
# `module.frontend_container_app`. Remove the SWA only after the Container App
# is verified in production (see docs/RUNBOOK.md).
module "static_web_app" {
  source              = "./modules/static_web_app"
  name_prefix         = var.name_prefix
  location            = var.swa_location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}
