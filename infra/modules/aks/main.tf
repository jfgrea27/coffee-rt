# AKS Module - Azure Kubernetes Service for coffee-rt

# User-assigned identity for AKS
resource "azurerm_user_assigned_identity" "aks" {
  name                = "${var.project}-${var.environment}-aks-identity"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "main" {
  name                = "${var.project}-${var.environment}-aks"
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = "${var.project}-${var.environment}"
  kubernetes_version  = var.kubernetes_version
  tags                = var.tags

  default_node_pool {
    name            = "system"
    node_count      = var.system_node_count
    vm_size         = var.system_node_size
    vnet_subnet_id  = var.aks_subnet_id
    os_disk_size_gb = 30
    os_disk_type    = "Managed"
    max_pods        = 110
    min_count       = var.enable_autoscaling ? var.system_node_min : null
    max_count       = var.enable_autoscaling ? var.system_node_max : null

    node_labels = {
      "nodepool" = "system"
    }

    tags = var.tags
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    service_cidr      = var.service_cidr
    dns_service_ip    = var.dns_service_ip
    load_balancer_sku = "standard"
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  # Private cluster - API server only accessible from VNet
  private_cluster_enabled = var.private_cluster_enabled

  azure_active_directory_role_based_access_control {
    managed                = true
    azure_rbac_enabled     = true
    admin_group_object_ids = var.admin_group_ids
  }

  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  dynamic "oms_agent" {
    for_each = var.enable_monitoring ? [1] : []
    content {
      log_analytics_workspace_id = azurerm_log_analytics_workspace.aks[0].id
    }
  }

  lifecycle {
    ignore_changes = [
      default_node_pool[0].node_count,
    ]
  }
}

# Workload node pool - for application workloads (optional)
resource "azurerm_kubernetes_cluster_node_pool" "workload" {
  count = var.workload_node_count > 0 ? 1 : 0

  name                  = "workload"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.workload_node_size
  node_count            = var.workload_node_count
  vnet_subnet_id        = var.aks_subnet_id
  os_disk_size_gb       = 30
  os_disk_type          = "Managed"
  max_pods              = 110
  min_count             = var.enable_autoscaling ? var.workload_node_min : null
  max_count             = var.enable_autoscaling ? var.workload_node_max : null

  # Spot instances for cost savings (dev only)
  priority        = var.use_spot_instances ? "Spot" : "Regular"
  eviction_policy = var.use_spot_instances ? "Delete" : null
  spot_max_price  = var.use_spot_instances ? -1 : null # -1 = pay up to on-demand price

  node_labels = {
    "nodepool"                              = "workload"
    "kubernetes.azure.com/scalesetpriority" = var.use_spot_instances ? "spot" : "regular"
  }

  node_taints = var.use_spot_instances ? ["kubernetes.azure.com/scalesetpriority=spot:NoSchedule"] : []

  tags = var.tags

  lifecycle {
    ignore_changes = [
      node_count,
    ]
  }
}

# Log Analytics Workspace for monitoring (optional)
resource "azurerm_log_analytics_workspace" "aks" {
  count = var.enable_monitoring ? 1 : 0

  name                = "${var.project}-${var.environment}-logs"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = var.tags
}

# Role assignment for AKS to pull from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  count                            = var.acr_id != "" ? 1 : 0
  scope                            = var.acr_id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

# Role assignment for AKS identity on the VNet
resource "azurerm_role_assignment" "aks_network_contributor" {
  scope                            = var.vnet_id
  role_definition_name             = "Network Contributor"
  principal_id                     = azurerm_user_assigned_identity.aks.principal_id
  skip_service_principal_aad_check = true
}
