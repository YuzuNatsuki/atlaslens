variable "name_prefix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tags" { type = map(string) }

resource "azurerm_static_web_app" "main" {
  name                = "${var.name_prefix}-web"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku_tier            = "Free"
  sku_size            = "Free"
  tags                = var.tags
}

output "default_hostname" { value = azurerm_static_web_app.main.default_host_name }
output "url" { value = "https://${azurerm_static_web_app.main.default_host_name}" }
output "api_key" {
  value     = azurerm_static_web_app.main.api_key
  sensitive = true
}
