terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.10" }
    azapi   = { source = "Azure/azapi", version = "~> 2.0" }
  }
}

variable "name_prefix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "gpt4o_capacity_tpm" { type = number }
variable "embedding_capacity_tpm" { type = number }
variable "tags" { type = map(string) }

resource "azurerm_cognitive_account" "foundry" {
  name                          = "${var.name_prefix}-foundry"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  kind                          = "AIServices"
  sku_name                      = "S0"
  custom_subdomain_name         = "${var.name_prefix}-foundry"
  public_network_access_enabled = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-11-20"
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.gpt4o_capacity_tpm
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = "text-embedding-3-large"
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-large"
    version = "1"
  }

  sku {
    name     = "Standard"
    capacity = var.embedding_capacity_tpm
  }
}

# Foundry sub-project on top of the AIServices account (control-plane via azapi
# because azurerm doesn't yet expose Microsoft.CognitiveServices/accounts/projects).
resource "azapi_resource" "default_project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  parent_id = azurerm_cognitive_account.foundry.id
  name      = "atlaslens"
  location  = var.location

  body = {
    identity = {
      type = "SystemAssigned"
    }
    properties = {
      displayName = "AtlasLens"
    }
  }

  response_export_values = ["properties.endpoints"]
}

output "account_id" { value = azurerm_cognitive_account.foundry.id }
output "account_name" { value = azurerm_cognitive_account.foundry.name }
output "openai_endpoint" { value = azurerm_cognitive_account.foundry.endpoint }
output "primary_key" {
  value     = azurerm_cognitive_account.foundry.primary_access_key
  sensitive = true
}
output "foundry_project_endpoint" {
  value = try(azapi_resource.default_project.output.properties.endpoints["AI Foundry API"], null)
}
