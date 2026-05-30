variable "name_prefix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "container_app_environment_id" { type = string }
variable "image_tag" { type = string }
variable "backend_url" { type = string }

variable "registry_login_server" { type = string }
variable "registry_username" { type = string }
variable "registry_password" {
  type      = string
  sensitive = true
}

variable "tags" { type = map(string) }

# Frontend (nginx + Vite SPA) on Container Apps.
# nginx proxies /api/* to the backend Container App via BACKEND_URL.
resource "azurerm_container_app" "frontend" {
  name                         = "${var.name_prefix}-web"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  registry {
    server               = var.registry_login_server
    username             = var.registry_username
    password_secret_name = "registry-password"
  }

  secret {
    name  = "registry-password"
    value = var.registry_password
  }

  ingress {
    external_enabled = true
    target_port      = 8080
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 2

    container {
      name   = "web"
      image  = "${var.registry_login_server}/atlaslens-frontend:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "BACKEND_URL"
        value = var.backend_url
      }
      env {
        name  = "PORT"
        value = "8080"
      }
    }
  }

  tags = var.tags
}

output "fqdn" { value = azurerm_container_app.frontend.ingress[0].fqdn }
output "url" { value = "https://${azurerm_container_app.frontend.ingress[0].fqdn}" }
output "principal_id" { value = azurerm_container_app.frontend.identity[0].principal_id }
