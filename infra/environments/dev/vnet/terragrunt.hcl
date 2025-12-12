# VNet configuration for dev environment

include "root" {
  path = find_in_parent_folders("root.hcl")
}

include "env" {
  path   = find_in_parent_folders("env.hcl")
  expose = true
}

terraform {
  source = "../../../modules/vnet"
}

dependency "rg" {
  config_path = "../resource-group"

  mock_outputs = {
    name     = "coffee-rt-dev-rg"
    location = "ukwest"
  }
}

inputs = {
  project             = "coffee-rt"
  environment         = include.env.locals.environment
  resource_group_name = dependency.rg.outputs.name
  location            = dependency.rg.outputs.location
  vnet_cidr           = "10.10.0.0/16"
  aks_subnet_cidr     = "10.10.0.0/20"

  # Bastion subnet for jump box
  enable_bastion_subnet = true
  bastion_subnet_cidr   = "10.10.255.0/24"
}
