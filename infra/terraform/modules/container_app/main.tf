variable "name_prefix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "log_analytics_workspace_id" { type = string }
variable "application_insights_connection_string" {
  type      = string
  sensitive = true
}
variable "image_tag" { type = string }

variable "registry_login_server" { type = string }
variable "registry_username" { type = string }
variable "registry_password" {
  type      = string
  sensitive = true
}

variable "openai_endpoint" { type = string }
variable "openai_api_key" {
  type      = string
  sensitive = true
}
variable "foundry_project_endpoint" {
  type    = string
  default = ""
}
variable "cosmos_endpoint" { type = string }
variable "cosmos_key" {
  type      = string
  sensitive = true
}
variable "jwt_secret" {
  type      = string
  sensitive = true
}
variable "tags" { type = map(string) }

resource "azurerm_container_app_environment" "main" {
  name                       = "${var.name_prefix}-env"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = var.log_analytics_workspace_id
  tags                       = var.tags
}

resource "azurerm_container_app" "backend" {
  name                         = "${var.name_prefix}-backend"
  container_app_environment_id = azurerm_container_app_environment.main.id
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
  secret {
    name  = "openai-key"
    value = var.openai_api_key
  }
  secret {
    name  = "cosmos-key"
    value = var.cosmos_key
  }
  secret {
    name  = "appi-conn"
    value = var.application_insights_connection_string
  }
  secret {
    name  = "jwt-secret"
    value = var.jwt_secret
  }

  ingress {
    external_enabled = true
    target_port      = 8000
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
      name   = "backend"
      image  = "${var.registry_login_server}/atlaslens-backend:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.openai_endpoint
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "openai-key"
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = "2024-10-21"
      }
      env {
        name  = "AZURE_OPENAI_CHAT_DEPLOYMENT"
        value = "gpt-4o"
      }
      env {
        name  = "AZURE_OPENAI_CHAT_DEPLOYMENT_FAST"
        value = "gpt-4o"
      }
      env {
        name  = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        value = "text-embedding-3-large"
      }
      env {
        name  = "COSMOS_ENDPOINT"
        value = var.cosmos_endpoint
      }
      env {
        name        = "COSMOS_KEY"
        secret_name = "cosmos-key"
      }
      env {
        name  = "COSMOS_DATABASE"
        value = "atlaslens"
      }
      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appi-conn"
      }
      env {
        name        = "JWT_SECRET"
        secret_name = "jwt-secret"
      }
      env {
        name  = "APP_ENV"
        value = "container"
      }
      env {
        name  = "AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"
        value = var.foundry_project_endpoint
      }
    }
  }

  tags = var.tags
}

output "fqdn" { value = azurerm_container_app.backend.ingress[0].fqdn }
output "backend_url" { value = "https://${azurerm_container_app.backend.ingress[0].fqdn}" }
output "principal_id" { value = azurerm_container_app.backend.identity[0].principal_id }
output "environment_id" { value = azurerm_container_app_environment.main.id }
