output "client_id" {
  description = "Azure AD Application (client) ID - use as AZURE_CLIENT_ID secret"
  value       = azuread_application.github_actions.client_id
}

output "tenant_id" {
  description = "Azure AD Tenant ID - use as AZURE_TENANT_ID secret"
  value       = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  description = "Azure Subscription ID - use as AZURE_SUBSCRIPTION_ID secret"
  value       = data.azurerm_client_config.current.subscription_id
}

output "application_name" {
  description = "Azure AD Application display name"
  value       = azuread_application.github_actions.display_name
}

output "service_principal_id" {
  description = "Service Principal object ID"
  value       = azuread_service_principal.github_actions.object_id
}

output "github_secrets_summary" {
  description = "Summary of values to add as GitHub secrets"
  value = <<-EOT
    Add these secrets to GitHub (Settings → Secrets → Actions):

    AZURE_CLIENT_ID       = ${azuread_application.github_actions.client_id}
    AZURE_TENANT_ID       = ${data.azurerm_client_config.current.tenant_id}
    AZURE_SUBSCRIPTION_ID = ${data.azurerm_client_config.current.subscription_id}
  EOT
}
