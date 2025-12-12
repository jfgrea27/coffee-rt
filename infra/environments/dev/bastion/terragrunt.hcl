# Bastion configuration for dev environment

include "root" {
  path = find_in_parent_folders("root.hcl")
}

include "env" {
  path   = find_in_parent_folders("env.hcl")
  expose = true
}

terraform {
  source = "../../../modules/bastion"
}

dependency "rg" {
  config_path = "../resource-group"

  mock_outputs = {
    name     = "coffee-rt-dev-rg"
    location = "ukwest"
  }
}

dependency "vnet" {
  config_path = "../vnet"

  mock_outputs = {
    bastion_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/mock-rg/providers/Microsoft.Network/virtualNetworks/mock-vnet/subnets/mock-bastion-subnet"
  }
}

dependency "aks" {
  config_path = "../aks"

  mock_outputs = {
    cluster_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/mock-rg/providers/Microsoft.ContainerService/managedClusters/mock-aks"
  }
}

dependency "acr" {
  config_path = "../acr"

  mock_outputs = {
    id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/mock-rg/providers/Microsoft.ContainerRegistry/registries/mockacr"
  }
}

inputs = {
  project             = "coffee-rt"
  environment         = include.env.locals.environment
  resource_group_name = dependency.rg.outputs.name
  location            = dependency.rg.outputs.location
  subnet_id           = dependency.vnet.outputs.bastion_subnet_id
  aks_cluster_id      = dependency.aks.outputs.cluster_id
  acr_id              = dependency.acr.outputs.id

  # VM settings
  vm_size        = "Standard_B1s"
  admin_username = "azureuser"

  # SSH public key from environment variable
  ssh_public_key = get_env("BASTION_SSH_PUBLIC_KEY")

  # IPs allowed to SSH from environment variable
  allowed_ssh_ips = [get_env("BASTION_ALLOWED_IP")]

  tags = {
    Project     = "coffee-rt"
    Environment = include.env.locals.environment
    ManagedBy   = "terragrunt"
  }
}
