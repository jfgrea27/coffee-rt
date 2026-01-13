# Storage configuration for dev environment
# Adds load-tests container and workload identity for load-tester

include "root" {
  path = find_in_parent_folders("root.hcl")
}

include "env" {
  path   = find_in_parent_folders("env.hcl")
  expose = true
}

terraform {
  source = "../../../modules/storage"
}

dependency "rg" {
  config_path = "../resource-group"

  mock_outputs = {
    name     = "coffee-rt-dev-rg"
    location = "ukwest"
  }
}

dependency "aks" {
  config_path = "../aks"

  mock_outputs = {
    oidc_issuer_url = "https://mock-oidc-issuer.example.com"
  }
}

inputs = {
  project             = "coffee-rt"
  environment         = include.env.locals.environment
  resource_group_name = dependency.rg.outputs.name
  location            = dependency.rg.outputs.location

  # Reference existing tfstate storage account
  storage_account_name        = "coffeertstate${include.env.locals.environment}"
  tfstate_resource_group_name = "coffee-rt-tfstate-rg"

  # AKS OIDC issuer for workload identity
  aks_oidc_issuer_url = dependency.aks.outputs.oidc_issuer_url

  # Kubernetes service account details
  kubernetes_namespace            = "coffee-ns"
  kubernetes_service_account_name = "load-tester"
}
