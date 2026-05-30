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
variable "demo_password" {
  description = "Out-of-band demo account password, passed via secret env DEMO_PASSWORD."
  type        = string
  sensitive   = true
  default     = ""
}
variable "extra_cors_origins" {
  description = "Comma-separated list of extra allowed origins (e.g. the frontend Container App URL)."
  type        = string
  default     = ""
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
  dynamic "secret" {
    for_each = var.demo_password == "" ? [] : [var.demo_password]
    content {
      name  = "demo-password"
      value = secret.value
    }
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
      dynamic "env" {
        for_each = var.demo_password == "" ? [] : [1]
        content {
          name        = "DEMO_PASSWORD"
          secret_name = "demo-password"
        }
      }
      env {
        name  = "APP_ENV"
        value = "container"
      }
      env {
        name  = "CORS_ORIGINS"
        value = var.extra_cors_origins
      }
      env {
        name  = "AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"
        value = var.foundry_project_endpoint
      }
    }
  }

  tags = var.tags

  # The frontend Container App is created in a separate module that depends on
  # this one's environment_id. We don't need a Terraform link back, but the
  # CORS_ORIGINS env var should be updated whenever the frontend FQDN changes
  # (handled by `cd-infra` running a fresh apply after the frontend exists).
}

output "fqdn" { value = azurerm_container_app.backend.ingress[0].fqdn }
output "backend_url" { value = "https://${azurerm_container_app.backend.ingress[0].fqdn}" }
output "principal_id" { value = azurerm_container_app.backend.identity[0].principal_id }
output "environment_id" { value = azurerm_container_app_environment.main.id }
output "environment_default_domain" { value = azurerm_container_app_environment.main.default_domain }
