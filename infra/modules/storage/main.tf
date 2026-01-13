# Storage Module - Load Test Results Container with Workload Identity
#
# This module adds a load-tests container to the existing tfstate storage account
# and sets up workload identity for the load-tester pod to upload results.

# Data source to reference existing storage account
data "azurerm_storage_account" "tfstate" {
  name                = var.storage_account_name
  resource_group_name = var.tfstate_resource_group_name
}

# Create container for load test results
resource "azurerm_storage_container" "load_tests" {
  name                  = "load-tests"
  storage_account_id    = data.azurerm_storage_account.tfstate.id
  container_access_type = "private"
}

# User-assigned managed identity for the load-tester workload
resource "azurerm_user_assigned_identity" "load_tester" {
  name                = "${var.project}-${var.environment}-load-tester-identity"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# Role assignment: Storage Blob Data Contributor on the storage account
resource "azurerm_role_assignment" "load_tester_blob_contributor" {
  scope                            = data.azurerm_storage_account.tfstate.id
  role_definition_name             = "Storage Blob Data Contributor"
  principal_id                     = azurerm_user_assigned_identity.load_tester.principal_id
  skip_service_principal_aad_check = true
}

# Federated credential for workload identity
# This allows the Kubernetes service account to assume the managed identity
resource "azurerm_federated_identity_credential" "load_tester" {
  name                = "load-tester-federated-credential"
  resource_group_name = var.resource_group_name
  parent_id           = azurerm_user_assigned_identity.load_tester.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = var.aks_oidc_issuer_url
  subject             = "system:serviceaccount:${var.kubernetes_namespace}:${var.kubernetes_service_account_name}"
}
