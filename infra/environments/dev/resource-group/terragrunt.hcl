# Resource Group configuration for dev environment

include "root" {
  path = find_in_parent_folders("root.hcl")
}

include "env" {
  path   = find_in_parent_folders("env.hcl")
  expose = true
}

terraform {
  source = "../../../modules/resource-group"
}

inputs = {
  project     = "coffee-rt"
  environment = include.env.locals.environment
  location    = include.env.locals.location

  tags = {
    Project     = "coffee-rt"
    Environment = include.env.locals.environment
    ManagedBy   = "terragrunt"
  }
}
