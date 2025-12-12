# ACR Module - Azure Container Registry for coffee-rt

resource "azurerm_container_registry" "main" {
  name                = replace("${var.project}${var.environment}acr", "-", "")
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  admin_enabled       = var.admin_enabled
  tags                = var.tags

  # Enable content trust for production
  dynamic "trust_policy" {
    for_each = var.enable_content_trust ? [1] : []
    content {
      enabled = true
    }
  }

  # Retention policy for untagged images
  dynamic "retention_policy" {
    for_each = var.retention_days > 0 ? [1] : []
    content {
      days    = var.retention_days
      enabled = true
    }
  }

  # Geo-replication for Premium SKU
  dynamic "georeplications" {
    for_each = var.sku == "Premium" ? var.geo_replication_locations : []
    content {
      location                = georeplications.value
      zone_redundancy_enabled = true
      tags                    = var.tags
    }
  }
}

# Private endpoint for ACR (optional)
resource "azurerm_private_endpoint" "acr" {
  count               = var.private_endpoint_subnet_id != "" ? 1 : 0
  name                = "${var.project}-${var.environment}-acr-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.project}-${var.environment}-acr-psc"
    private_connection_resource_id = azurerm_container_registry.main.id
    subresource_names              = ["registry"]
    is_manual_connection           = false
  }
}
