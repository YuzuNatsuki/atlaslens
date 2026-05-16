# `import` blocks (Terraform >= 1.5) bind existing Azure resources to the
# Terraform state on the first `terraform apply`. Re-running apply after the
# first import is a no-op as long as the resource configuration matches reality.
#
# The subscription id is interpolated from var.subscription_id at plan time.

locals {
  sub_id    = var.subscription_id
  rg_scope  = "/subscriptions/${local.sub_id}/resourceGroups/${var.name_prefix}-rg"
  acc_scope = "${local.rg_scope}/providers/Microsoft.CognitiveServices/accounts"
}

import {
  to = azurerm_resource_group.main
  id = local.rg_scope
}

# ---------- observability ----------

import {
  to = module.observability.azurerm_log_analytics_workspace.main
  id = "${local.rg_scope}/providers/Microsoft.OperationalInsights/workspaces/${var.name_prefix}-logs"
}

import {
  to = module.observability.azurerm_application_insights.main
  id = "${local.rg_scope}/providers/Microsoft.Insights/components/${var.name_prefix}-appi"
}

# ---------- cosmos ----------

import {
  to = module.cosmos.azurerm_cosmosdb_account.main
  id = "${local.rg_scope}/providers/Microsoft.DocumentDB/databaseAccounts/${var.name_prefix}-cosmos"
}

import {
  to = module.cosmos.azurerm_cosmosdb_sql_database.main
  id = "${local.rg_scope}/providers/Microsoft.DocumentDB/databaseAccounts/${var.name_prefix}-cosmos/sqlDatabases/atlaslens"
}

import {
  for_each = toset(["members", "goals", "daily_reports", "one_on_ones", "meetings", "prep_notes"])
  to       = module.cosmos.azurerm_cosmosdb_sql_container.containers[each.value]
  id       = "${local.rg_scope}/providers/Microsoft.DocumentDB/databaseAccounts/${var.name_prefix}-cosmos/sqlDatabases/atlaslens/containers/${each.value}"
}

# ---------- storage / kv ----------

import {
  to = module.storage.azurerm_storage_account.foundry
  id = "${local.rg_scope}/providers/Microsoft.Storage/storageAccounts/${var.name_prefix}fdy${local.sub_suffix}"
}

import {
  to = module.keyvault.azurerm_key_vault.main
  id = "${local.rg_scope}/providers/Microsoft.KeyVault/vaults/${var.name_prefix}-kv-${local.sub_suffix}"
}

# ---------- foundry (AIServices) ----------

import {
  to = module.foundry.azurerm_cognitive_account.foundry
  id = "${local.acc_scope}/${var.name_prefix}-foundry"
}

import {
  to = module.foundry.azurerm_cognitive_deployment.gpt4o
  id = "${local.acc_scope}/${var.name_prefix}-foundry/deployments/gpt-4o"
}

import {
  to = module.foundry.azurerm_cognitive_deployment.embedding
  id = "${local.acc_scope}/${var.name_prefix}-foundry/deployments/text-embedding-3-large"
}

import {
  to = module.foundry.azapi_resource.default_project
  id = "${local.acc_scope}/${var.name_prefix}-foundry/projects/atlaslens"
}

# ---------- foundry hub + project (AML) ----------

import {
  to = module.foundry_hub.azurerm_ai_foundry.hub
  id = "${local.rg_scope}/providers/Microsoft.MachineLearningServices/workspaces/${var.name_prefix}-foundry-hub"
}

import {
  to = module.foundry_hub.azurerm_ai_foundry_project.project
  id = "${local.rg_scope}/providers/Microsoft.MachineLearningServices/workspaces/${var.name_prefix}-foundry-proj"
}

import {
  to = module.foundry_hub.azapi_resource.aoai_connection
  id = "${local.rg_scope}/providers/Microsoft.MachineLearningServices/workspaces/${var.name_prefix}-foundry-proj/connections/atlaslens_aoai"
}

# ---------- acr / container apps ----------

import {
  to = module.acr.azurerm_container_registry.main
  id = "${local.rg_scope}/providers/Microsoft.ContainerRegistry/registries/${local.acr_name}"
}

import {
  to = module.container_app.azurerm_container_app_environment.main
  id = "${local.rg_scope}/providers/Microsoft.App/managedEnvironments/${var.name_prefix}-env"
}

import {
  to = module.container_app.azurerm_container_app.backend
  id = "${local.rg_scope}/providers/Microsoft.App/containerApps/${var.name_prefix}-backend"
}

# ---------- static web app ----------

import {
  to = module.static_web_app.azurerm_static_web_app.main
  id = "${local.rg_scope}/providers/Microsoft.Web/staticSites/${var.name_prefix}-web"
}
