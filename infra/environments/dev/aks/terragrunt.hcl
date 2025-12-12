# AKS configuration for dev environment

include "root" {
  path = find_in_parent_folders("root.hcl")
}

include "env" {
  path   = find_in_parent_folders("env.hcl")
  expose = true
}

terraform {
  source = "../../../modules/aks"
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
    aks_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/mock-rg/providers/Microsoft.Network/virtualNetworks/mock-vnet/subnets/mock-subnet"
    vnet_id       = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/mock-rg/providers/Microsoft.Network/virtualNetworks/mock-vnet"
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
  aks_subnet_id       = dependency.vnet.outputs.aks_subnet_id
  vnet_id             = dependency.vnet.outputs.vnet_id
  acr_id              = dependency.acr.outputs.id

  kubernetes_version = "1.33"

  # Dev sizing - burstable instances for cost savings
  system_node_count   = 1
  system_node_size    = "Standard_B2s"
  workload_node_count = 0  # Disabled due to vCPU quota - request increase or use different VM family
  workload_node_size  = "Standard_B2as_v2"   # 2 vCPU, 4GB - AMD, better spot availability
  enable_autoscaling  = false
  use_spot_instances  = true

  # Networking
  service_cidr   = "10.1.0.0/16"
  dns_service_ip = "10.1.0.10"

  # Disable monitoring for dev to save costs
  enable_monitoring = false

  # Private cluster - API server only accessible from VNet via bastion
  private_cluster_enabled = true
}
