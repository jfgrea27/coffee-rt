variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the bastion VM"
  type        = string
}

variable "allowed_ssh_ips" {
  description = "List of IP addresses allowed to SSH to bastion"
  type        = list(string)
  default     = []
}

variable "admin_username" {
  description = "Admin username for the bastion VM"
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key" {
  description = "SSH public key for bastion access"
  type        = string
}

variable "vm_size" {
  description = "VM size for bastion"
  type        = string
  default     = "Standard_B1s"
}

variable "aks_cluster_id" {
  description = "AKS cluster ID to grant access to (optional)"
  type        = string
  default     = ""
}

variable "acr_id" {
  description = "ACR ID to grant pull access to (optional)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
