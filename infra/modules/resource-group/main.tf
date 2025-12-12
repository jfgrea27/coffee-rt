# Resource Group Module - Foundation for all coffee-rt Azure resources

resource "azurerm_resource_group" "main" {
  name     = "${var.project}-${var.environment}-rg"
  location = var.location
  tags     = var.tags
}
