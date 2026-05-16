variable "name_prefix" { type = string }
variable "sub_suffix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_storage_account" "foundry" {
  # 3-24 lowercase chars, no dashes
  name                            = "${var.name_prefix}fdy${var.sub_suffix}"
  location                        = var.location
  resource_group_name             = var.resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  allow_nested_items_to_be_public = false
  tags                            = var.tags
}

output "foundry_storage_id" { value = azurerm_storage_account.foundry.id }
output "foundry_storage_name" { value = azurerm_storage_account.foundry.name }
