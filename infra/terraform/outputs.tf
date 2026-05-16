output "backend_url" {
  value       = module.container_app.backend_url
  description = "Public URL of the FastAPI backend"
}

output "frontend_url" {
  value       = module.static_web_app.url
  description = "Public URL of the Static Web App"
}

output "foundry_account" {
  value       = module.foundry.account_name
  description = "AIServices account name (Foundry resource)"
}

output "foundry_openai_endpoint" {
  value       = module.foundry.openai_endpoint
  description = "OpenAI inference endpoint under the Foundry resource"
}

output "foundry_project_endpoint" {
  value       = module.foundry.foundry_project_endpoint
  description = "Foundry default project endpoint (AI Foundry API)"
}

output "cosmos_endpoint" {
  value       = module.cosmos.endpoint
  description = "Cosmos DB account endpoint"
}

output "container_app_principal_id" {
  value       = module.container_app.principal_id
  description = "System-assigned managed identity of the backend Container App"
}

output "registry_login_server" {
  value       = module.acr.login_server
  description = "ACR login server (used by GitHub Actions to push images)"
}
