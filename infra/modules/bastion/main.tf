# Bastion Module - Jump box for secure AKS access

# Public IP for bastion
resource "azurerm_public_ip" "bastion" {
  name                = "${var.project}-${var.environment}-bastion-pip"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

# Network Security Group for bastion
resource "azurerm_network_security_group" "bastion" {
  name                = "${var.project}-${var.environment}-bastion-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  # Allow SSH only from specified IPs
  security_rule {
    name                       = "AllowSSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefixes    = var.allowed_ssh_ips
    destination_address_prefix = "*"
  }

  # Deny all other inbound
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# Network interface for bastion VM
resource "azurerm_network_interface" "bastion" {
  name                = "${var.project}-${var.environment}-bastion-nic"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.bastion.id
  }
}

# Associate NSG with NIC
resource "azurerm_network_interface_security_group_association" "bastion" {
  network_interface_id      = azurerm_network_interface.bastion.id
  network_security_group_id = azurerm_network_security_group.bastion.id
}

# Cloud-init script to install kubectl, helm, az cli, terragrunt
locals {
  cloud_init = <<-EOF
    #cloud-config
    package_update: true
    package_upgrade: true

    packages:
      - apt-transport-https
      - ca-certificates
      - curl
      - gnupg
      - lsb-release
      - jq
      - unzip

    runcmd:
      # Install Azure CLI
      - curl -sL https://aka.ms/InstallAzureCLIDeb | bash

      # Install kubectl and kubelogin (required for AAD-enabled AKS)
      - az aks install-cli

      # Install Helm
      - curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

      # Install Terragrunt
      - curl -sL https://github.com/gruntwork-io/terragrunt/releases/download/v0.55.0/terragrunt_linux_amd64 -o /usr/local/bin/terragrunt
      - chmod +x /usr/local/bin/terragrunt

      # Install Terraform (required by terragrunt)
      - curl -sL https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip -o terraform.zip
      - unzip terraform.zip -d /usr/local/bin/
      - rm terraform.zip

      # Install k9s
      - curl -sL https://github.com/derailed/k9s/releases/download/v0.32.0/k9s_Linux_amd64.tar.gz | tar xz -C /usr/local/bin k9s

      # Create kubectl config directory
      - mkdir -p /home/${var.admin_username}/.kube
      - chown -R ${var.admin_username}:${var.admin_username} /home/${var.admin_username}/.kube

    final_message: "Bastion setup complete after $UPTIME seconds"
  EOF
}

# Bastion VM
resource "azurerm_linux_virtual_machine" "bastion" {
  name                = "${var.project}-${var.environment}-bastion"
  location            = var.location
  resource_group_name = var.resource_group_name
  size                = var.vm_size
  admin_username      = var.admin_username
  tags                = var.tags

  network_interface_ids = [
    azurerm_network_interface.bastion.id
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb         = 30
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  custom_data = base64encode(local.cloud_init)

  identity {
    type = "SystemAssigned"
  }
}

# Grant bastion VM access to get AKS credentials
resource "azurerm_role_assignment" "bastion_aks_user" {
  count = var.aks_cluster_id != "" ? 1 : 0

  scope                = var.aks_cluster_id
  role_definition_name = "Azure Kubernetes Service Cluster User Role"
  principal_id         = azurerm_linux_virtual_machine.bastion.identity[0].principal_id
}

# Grant bastion VM Kubernetes RBAC admin (for kubectl commands)
resource "azurerm_role_assignment" "bastion_aks_rbac_admin" {
  count = var.aks_cluster_id != "" ? 1 : 0

  scope                = var.aks_cluster_id
  role_definition_name = "Azure Kubernetes Service RBAC Cluster Admin"
  principal_id         = azurerm_linux_virtual_machine.bastion.identity[0].principal_id
}

# Grant bastion VM access to pull from ACR (for helm charts and images)
resource "azurerm_role_assignment" "bastion_acr_pull" {
  count = var.acr_id != "" ? 1 : 0

  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_virtual_machine.bastion.identity[0].principal_id
}
