variable "subscription_id" {
  description = "Azure subscription id"
  type        = string
}

variable "tenant_id" {
  description = "Azure tenant id (used for OIDC federation outputs)"
  type        = string
  default     = ""
}

variable "name_prefix" {
  description = "Prefix used for every resource name (lowercase, 3-12 chars)"
  type        = string
  default     = "atlaslens"
}

variable "location" {
  description = "Azure region — must support AIServices, Container Apps, Cosmos, AML, SWA"
  type        = string
  default     = "japaneast"
}

variable "swa_location" {
  description = "Static Web App location (SWA Free is not in japaneast — eastasia is closest)"
  type        = string
  default     = "eastasia"
}

variable "tags" {
  description = "Tags applied to every resource"
  type        = map(string)
  default = {
    project    = "atlaslens"
    hackathon  = "microsoft-agent-hackathon-2026"
    managed_by = "terraform"
  }
}

variable "jwt_secret" {
  description = "JWT signing secret for backend auth — override per environment"
  type        = string
  sensitive   = true
  default     = "atlaslens-dev-secret-change-me"
}

variable "gpt4o_capacity_tpm" {
  description = "gpt-4o capacity in thousands of TPM"
  type        = number
  default     = 30
}

variable "embedding_capacity_tpm" {
  description = "text-embedding-3-large capacity"
  type        = number
  default     = 30
}

variable "backend_image_tag" {
  description = "Backend image tag (CI overrides with the commit SHA)"
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "Frontend image tag (CI overrides with the commit SHA)"
  type        = string
  default     = "latest"
}
