variable "name_prefix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "storage_account_id" { type = string }
variable "key_vault_id" { type = string }
variable "application_insights_id" { type = string }
variable "aoai_connection_name" { type = string }
variable "aoai_endpoint" { type = string }
variable "aoai_api_key" {
  type      = string
  sensitive = true
}
variable "aoai_resource_id" { type = string }
variable "tags" { type = map(string) }

# Azure Machine Learning workspaces — Foundry Hub + Project.
# azurerm exposes Hub/Project as kind values on `azurerm_ai_foundry`*.

resource "azurerm_ai_foundry" "hub" {
  name                = "${var.name_prefix}-foundry-hub"
  location            = var.location
  resource_group_name = var.resource_group_name

  storage_account_id      = var.storage_account_id
  key_vault_id            = var.key_vault_id
  application_insights_id = var.application_insights_id

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_ai_foundry_project" "project" {
  name               = "${var.name_prefix}-foundry-proj"
  location           = var.location
  ai_services_hub_id = azurerm_ai_foundry.hub.id

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Connection to the AIServices-deployed OpenAI from inside the Foundry Project.
resource "azapi_resource" "aoai_connection" {
  type      = "Microsoft.MachineLearningServices/workspaces/connections@2024-10-01-preview"
  parent_id = azurerm_ai_foundry_project.project.id
  name      = var.aoai_connection_name

  body = {
    properties = {
      category      = "AzureOpenAI"
      authType      = "ApiKey"
      target        = var.aoai_endpoint
      isSharedToAll = true
      credentials = {
        key = var.aoai_api_key
      }
      metadata = {
        ApiVersion = "2024-10-21"
        ApiType    = "Azure"
        ResourceId = var.aoai_resource_id
      }
    }
  }
}

output "hub_id" { value = azurerm_ai_foundry.hub.id }
output "project_id" { value = azurerm_ai_foundry_project.project.id }
output "project_discovery_url" { value = azurerm_ai_foundry_project.project.discovery_url }
