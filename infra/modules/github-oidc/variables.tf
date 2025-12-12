variable "project" {
  description = "Project name"
  type        = string
}

variable "github_org" {
  description = "GitHub organization or username"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "acr_id" {
  description = "Azure Container Registry resource ID"
  type        = string
}

variable "enable_pr_deployments" {
  description = "Enable federated credential for pull requests"
  type        = bool
  default     = false
}
