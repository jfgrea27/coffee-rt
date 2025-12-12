# GitHub OIDC configuration for dev environment

include "root" {
  path = find_in_parent_folders("root.hcl")
}

include "env" {
  path   = find_in_parent_folders("env.hcl")
  expose = true
}

terraform {
  source = "../../../modules/github-oidc"
}

dependency "acr" {
  config_path = "../acr"

  mock_outputs = {
    id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/mock-rg/providers/Microsoft.ContainerRegistry/registries/mockacr"
  }
}

inputs = {
  project     = "coffee-rt"
  github_org  =  "jfgrea27"
  github_repo = "coffee-rt"
  acr_id      = dependency.acr.outputs.id

  enable_pr_deployments = false
}
