# Dev environment configuration

locals {
  environment = "dev"
  location    = "ukwest"
}

inputs = {
  environment = local.environment
  location    = local.location

  # Dev-specific sizing (smaller instances)
  system_node_count   = 1
  system_node_size    = "Standard_D2s_v3"
  workload_node_count = 2
  workload_node_size  = "Standard_D2s_v3"
  enable_autoscaling  = false

  # Dev networking
  vnet_cidr       = "10.10.0.0/16"
  aks_subnet_cidr = "10.10.0.0/20"

  tags = {
    Project     = "coffee-rt"
    Environment = local.environment
    ManagedBy   = "terragrunt"
  }
}
