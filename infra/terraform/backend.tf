# Remote state in an Azure Storage Account.
#
# The state backend itself is bootstrapped by `infra/scripts/bootstrap_tfstate.sh`
# (out-of-band, before the first `terraform init`).
#
#   resource group : atlaslens-tfstate-rg
#   storage account: atlaslenstfstate<sub-hash>
#   container       : tfstate
#
# Override the storage_account_name via -backend-config="storage_account_name=..."
# if you fork the project under a different subscription.

terraform {
  backend "azurerm" {
    resource_group_name = "atlaslens-tfstate-rg"
    container_name      = "tfstate"
    key                 = "atlaslens.tfstate"
    use_oidc            = true
    use_azuread_auth    = true
    # storage_account_name supplied via -backend-config or environment.
  }
}
