variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_container_registry" "main" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Basic"
  admin_enabled       = true
  tags                = var.tags
}

output "login_server" { value = azurerm_container_registry.main.login_server }
output "admin_username" { value = azurerm_container_registry.main.admin_username }
output "admin_password" {
  value     = azurerm_container_registry.main.admin_password
  sensitive = true
}
output "id" { value = azurerm_container_registry.main.id }
