variable "name_prefix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_cosmosdb_account" "main" {
  name                = "${var.name_prefix}-cosmos"
  location            = var.location
  resource_group_name = var.resource_group_name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  public_network_access_enabled = true

  tags = var.tags
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "atlaslens"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
}

locals {
  containers = {
    members        = "/id"
    goals          = "/member_id"
    daily_reports  = "/member_id"
    one_on_ones    = "/member_id"
    meetings       = "/id"
    prep_notes     = "/member_id"
  }
}

resource "azurerm_cosmosdb_sql_container" "containers" {
  for_each            = local.containers
  name                = each.key
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = [each.value]
}

output "endpoint" { value = azurerm_cosmosdb_account.main.endpoint }
output "primary_key" {
  value     = azurerm_cosmosdb_account.main.primary_key
  sensitive = true
}
output "database_name" { value = azurerm_cosmosdb_sql_database.main.name }
