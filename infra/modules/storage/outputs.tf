output "storage_account_name" {
  description = "Name of the storage account"
  value       = data.azurerm_storage_account.tfstate.name
}

output "container_name" {
  description = "Name of the load-tests container"
  value       = azurerm_storage_container.load_tests.name
}

output "load_tester_identity_client_id" {
  description = "Client ID of the load-tester managed identity (for workload identity)"
  value       = azurerm_user_assigned_identity.load_tester.client_id
}

output "load_tester_identity_principal_id" {
  description = "Principal ID of the load-tester managed identity"
  value       = azurerm_user_assigned_identity.load_tester.principal_id
}

output "blob_endpoint" {
  description = "Blob endpoint URL"
  value       = data.azurerm_storage_account.tfstate.primary_blob_endpoint
}
