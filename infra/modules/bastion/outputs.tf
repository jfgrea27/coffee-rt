output "public_ip" {
  description = "Public IP address of the bastion"
  value       = azurerm_public_ip.bastion.ip_address
}

output "private_ip" {
  description = "Private IP address of the bastion"
  value       = azurerm_network_interface.bastion.private_ip_address
}

output "vm_id" {
  description = "ID of the bastion VM"
  value       = azurerm_linux_virtual_machine.bastion.id
}

output "vm_identity_principal_id" {
  description = "Principal ID of the bastion VM managed identity"
  value       = azurerm_linux_virtual_machine.bastion.identity[0].principal_id
}

output "ssh_command" {
  description = "SSH command to connect to bastion"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.bastion.ip_address}"
}

output "connection_info" {
  description = "Connection instructions"
  value       = <<-EOT
    Bastion is ready. To connect:

    1. SSH to bastion:
       ssh ${var.admin_username}@${azurerm_public_ip.bastion.ip_address}

    2. On the bastion, login to Azure and get AKS credentials:
       az login --identity
       az aks get-credentials --resource-group ${var.resource_group_name} --name <aks-cluster-name>

    3. Verify kubectl access:
       kubectl get nodes
  EOT
}
