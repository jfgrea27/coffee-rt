# GitHub OIDC Module - Federated identity for GitHub Actions

data "azurerm_client_config" "current" {}

# Azure AD Application
resource "azuread_application" "github_actions" {
  display_name = "${var.project}-github-actions"
  owners       = [data.azurerm_client_config.current.object_id]
}

# Service Principal
resource "azuread_service_principal" "github_actions" {
  client_id                    = azuread_application.github_actions.client_id
  app_role_assignment_required = false
  owners                       = [data.azurerm_client_config.current.object_id]
}

# Federated credential for main branch
resource "azuread_application_federated_identity_credential" "main_branch" {
  application_id = azuread_application.github_actions.id
  display_name   = "github-main"
  description    = "GitHub Actions deployment from main branch"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main"
}

# Optional: Federated credential for pull requests
resource "azuread_application_federated_identity_credential" "pull_request" {
  count = var.enable_pr_deployments ? 1 : 0

  application_id = azuread_application.github_actions.id
  display_name   = "github-pr"
  description    = "GitHub Actions for pull requests"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_org}/${var.github_repo}:pull_request"
}

# Grant AcrPush role on ACR
resource "azurerm_role_assignment" "acr_push" {
  scope                = var.acr_id
  role_definition_name = "AcrPush"
  principal_id         = azuread_service_principal.github_actions.object_id
}

# Optional: Grant AcrPull role (for reading images)
resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azuread_service_principal.github_actions.object_id
}
