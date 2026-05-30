variable "name_prefix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "log_analytics_workspace_id" { type = string }
variable "image_tag" { type = string }

variable "registry_login_server" { type = string }
variable "registry_username" { type = string }

variable "openai_endpoint" { type = string }
variable "foundry_project_endpoint" {
  type    = string
  default = ""
}
variable "cosmos_endpoint" { type = string }

# ---- Key Vault references (resolved at runtime by the Container App MI). ----
# Each value is a Key Vault Secret URI (versionless) produced by the keyvault
# module. The Container App fetches the latest version on revision start.
variable "kv_secret_id_jwt_secret" {
  description = "Key Vault Secret URI for the JWT signing key."
  type        = string
}
variable "kv_secret_id_demo_password" {
  description = "Key Vault Secret URI for the demo account password. Empty disables demo login."
  type        = string
  default     = ""
}
variable "kv_secret_id_openai_api_key" {
  description = "Key Vault Secret URI for the Azure OpenAI API key."
  type        = string
}
variable "kv_secret_id_cosmos_key" {
  description = "Key Vault Secret URI for the Cosmos DB primary key."
  type        = string
}
variable "kv_secret_id_appi_conn" {
  description = "Key Vault Secret URI for the App Insights connection string."
  type        = string
}
variable "kv_secret_id_registry_password" {
  description = "Key Vault Secret URI for the ACR admin password."
  type        = string
}

variable "kv_uami_id" {
  description = "Resource ID of the User-Assigned Managed Identity used to pull secrets from Key Vault."
  type        = string
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

  # SystemAssigned is kept for the AI Foundry role grant (out-of-band script).
  # UserAssigned MI is what reads Key Vault, granted Secrets User at apply time
  # before this Container App boots.
  identity {
    type         = "SystemAssigned, UserAssigned"
    identity_ids = [var.kv_uami_id]
  }

  # All secrets below are sourced from Key Vault via the user-assigned MI.
  # Rotation is handled by updating the secret value in KV and bumping a new
  # revision; no plaintext leaves the vault.

  registry {
    server               = var.registry_login_server
    username             = var.registry_username
    password_secret_name = "registry-password"
  }

  secret {
    name                = "registry-password"
    key_vault_secret_id = var.kv_secret_id_registry_password
    identity            = var.kv_uami_id
  }
  secret {
    name                = "openai-key"
    key_vault_secret_id = var.kv_secret_id_openai_api_key
    identity            = var.kv_uami_id
  }
  secret {
    name                = "cosmos-key"
    key_vault_secret_id = var.kv_secret_id_cosmos_key
    identity            = var.kv_uami_id
  }
  secret {
    name                = "appi-conn"
    key_vault_secret_id = var.kv_secret_id_appi_conn
    identity            = var.kv_uami_id
  }
  secret {
    name                = "jwt-secret"
    key_vault_secret_id = var.kv_secret_id_jwt_secret
    identity            = var.kv_uami_id
  }
  dynamic "secret" {
    for_each = var.kv_secret_id_demo_password == "" ? [] : [var.kv_secret_id_demo_password]
    content {
      name                = "demo-password"
      key_vault_secret_id = secret.value
      identity            = var.kv_uami_id
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
        for_each = var.kv_secret_id_demo_password == "" ? [] : [1]
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
