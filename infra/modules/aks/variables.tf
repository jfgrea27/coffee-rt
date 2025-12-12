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

variable "aks_subnet_id" {
  description = "ID of the AKS subnet"
  type        = string
}

variable "vnet_id" {
  description = "ID of the VNet"
  type        = string
}

variable "acr_id" {
  description = "ID of the Azure Container Registry (optional)"
  type        = string
  default     = ""
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.33"
}

# System node pool
variable "system_node_count" {
  description = "Number of system nodes"
  type        = number
  default     = 2
}

variable "system_node_size" {
  description = "VM size for system nodes"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "system_node_min" {
  description = "Minimum system nodes (when autoscaling)"
  type        = number
  default     = 2
}

variable "system_node_max" {
  description = "Maximum system nodes (when autoscaling)"
  type        = number
  default     = 5
}

# Workload node pool
variable "workload_node_count" {
  description = "Number of workload nodes"
  type        = number
  default     = 3
}

variable "workload_node_size" {
  description = "VM size for workload nodes"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "workload_node_min" {
  description = "Minimum workload nodes (when autoscaling)"
  type        = number
  default     = 2
}

variable "workload_node_max" {
  description = "Maximum workload nodes (when autoscaling)"
  type        = number
  default     = 10
}

variable "enable_autoscaling" {
  description = "Enable cluster autoscaling"
  type        = bool
  default     = true
}

variable "use_spot_instances" {
  description = "Use spot instances for workload nodes (dev only, can be evicted)"
  type        = bool
  default     = false
}

# Networking
variable "service_cidr" {
  description = "CIDR for Kubernetes services"
  type        = string
  default     = "10.1.0.0/16"
}

variable "dns_service_ip" {
  description = "DNS service IP (must be within service_cidr)"
  type        = string
  default     = "10.1.0.10"
}

# Admin access
variable "admin_group_ids" {
  description = "Azure AD group IDs for cluster admin access"
  type        = list(string)
  default     = []
}

# Monitoring
variable "enable_monitoring" {
  description = "Enable Log Analytics monitoring"
  type        = bool
  default     = true
}

variable "private_cluster_enabled" {
  description = "Enable private cluster (API server only accessible from VNet)"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "Log retention in days (only used if enable_monitoring = true)"
  type        = number
  default     = 30
}
