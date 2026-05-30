variable "name_prefix" { type = string }
variable "sub_suffix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tenant_id" { type = string }
variable "tags" { type = map(string) }

# ---- Secrets to provision in the vault (all sensitive). ----
variable "jwt_secret" {
  type      = string
  sensitive = true
}
variable "demo_password" {
  type      = string
  sensitive = true
  default   = ""
}
variable "openai_api_key" {
  type      = string
  sensitive = true
}
variable "cosmos_key" {
  type      = string
  sensitive = true
}
variable "appi_connection_string" {
  type      = string
  sensitive = true
}
variable "registry_password" {
  type      = string
  sensitive = true
}

# ---- Optional: principal ids that should be granted Secrets User. ----
variable "secret_reader_principal_ids" {
  description = "Principal IDs (e.g. Container App MI) that need GET on secrets."
  type        = list(string)
  default     = []
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = "${var.name_prefix}-kv-${var.sub_suffix}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  tags                       = var.tags
}

# The principal running Terraform needs write access so the secrets below
# can be created. Without this, the apply fails with 403 on first run.
resource "azurerm_role_assignment" "tf_kv_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Container App (or any other workload MI) gets read-only access so it can
# pull secrets at runtime via key_vault_secret_id references.
resource "azurerm_role_assignment" "secret_readers" {
  for_each             = toset(var.secret_reader_principal_ids)
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = each.value
}

# ---- The secrets ----
# All secrets the backend consumes are stored centrally here. Container App
# references them via key_vault_secret_id so rotation = update KV value +
# bump the Container App revision (no code changes).

resource "azurerm_key_vault_secret" "jwt_secret" {
  name         = "jwt-secret"
  value        = var.jwt_secret
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.tf_kv_admin]
}

resource "azurerm_key_vault_secret" "demo_password" {
  count        = var.demo_password == "" ? 0 : 1
  name         = "demo-password"
  value        = var.demo_password
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.tf_kv_admin]
}

resource "azurerm_key_vault_secret" "openai_api_key" {
  name         = "openai-api-key"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.tf_kv_admin]
}

resource "azurerm_key_vault_secret" "cosmos_key" {
  name         = "cosmos-key"
  value        = var.cosmos_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.tf_kv_admin]
}

resource "azurerm_key_vault_secret" "appi_conn" {
  name         = "appi-connection-string"
  value        = var.appi_connection_string
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.tf_kv_admin]
}

resource "azurerm_key_vault_secret" "registry_password" {
  name         = "registry-password"
  value        = var.registry_password
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.tf_kv_admin]
}

output "key_vault_id" { value = azurerm_key_vault.main.id }
output "key_vault_uri" { value = azurerm_key_vault.main.vault_uri }

output "secret_ids" {
  value = {
    jwt_secret        = azurerm_key_vault_secret.jwt_secret.versionless_id
    demo_password     = length(azurerm_key_vault_secret.demo_password) > 0 ? azurerm_key_vault_secret.demo_password[0].versionless_id : ""
    openai_api_key    = azurerm_key_vault_secret.openai_api_key.versionless_id
    cosmos_key        = azurerm_key_vault_secret.cosmos_key.versionless_id
    appi_conn         = azurerm_key_vault_secret.appi_conn.versionless_id
    registry_password = azurerm_key_vault_secret.registry_password.versionless_id
  }
}
