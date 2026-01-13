variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group for the managed identity"
  type        = string
}

variable "tfstate_resource_group_name" {
  description = "Resource group containing the tfstate storage account"
  type        = string
  default     = "coffee-rt-tfstate-rg"
}

variable "storage_account_name" {
  description = "Name of the existing tfstate storage account"
  type        = string
}

variable "aks_oidc_issuer_url" {
  description = "OIDC issuer URL from the AKS cluster for workload identity"
  type        = string
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace where load-tester runs"
  type        = string
  default     = "coffee-ns"
}

variable "kubernetes_service_account_name" {
  description = "Kubernetes service account name for load-tester"
  type        = string
  default     = "load-tester"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
