output "name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "id" {
  description = "ID of the resource group"
  value       = azurerm_resource_group.main.id
}

output "location" {
  description = "Azure region of the resource group"
  value       = azurerm_resource_group.main.location
}
