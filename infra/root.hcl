# Root terragrunt.hcl - Common configuration for all environments

locals {
  # Parse the file path to extract environment
  path_components = split("/", path_relative_to_include())
  environment     = try(local.path_components[1], "dev")
}

# Generate provider configuration
generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.45"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

provider "azuread" {}
EOF
}

# Configure remote state in Azure Storage
remote_state {
  backend = "azurerm"
  config = {
    resource_group_name  = "coffee-rt-tfstate-rg"
    storage_account_name = "coffeertstate${local.environment}"
    container_name       = "tfstate"
    key                  = "${path_relative_to_include()}/terraform.tfstate"
  }
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
}

# Default inputs applied to all modules
inputs = {
  environment = local.environment
  project     = "coffee-rt"
  location    = "ukwest"

  tags = {
    Project     = "coffee-rt"
    Environment = local.environment
    ManagedBy   = "terragrunt"
  }
}
