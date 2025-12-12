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
  description = "Name of the resource group"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "sku" {
  description = "SKU for ACR (Basic, Standard, Premium)"
  type        = string
  default     = "Standard"
}

variable "admin_enabled" {
  description = "Enable admin user"
  type        = bool
  default     = false
}

variable "enable_content_trust" {
  description = "Enable content trust"
  type        = bool
  default     = false
}

variable "retention_days" {
  description = "Days to retain untagged images (0 to disable)"
  type        = number
  default     = 7
}

variable "geo_replication_locations" {
  description = "Locations for geo-replication (Premium SKU only)"
  type        = list(string)
  default     = []
}

variable "private_endpoint_subnet_id" {
  description = "Subnet ID for private endpoint (optional)"
  type        = string
  default     = ""
}
