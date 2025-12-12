#!/bin/bash
#
# Initialize Azure Storage for Terraform state
# Usage: ./init-tf-state.sh [environment]
# Example: ./init-tf-state.sh dev

set -euo pipefail

ENVIRONMENT="${1:-dev}"
RESOURCE_GROUP="coffee-rt-tfstate-rg"
STORAGE_ACCOUNT="coffeertstate${ENVIRONMENT}"
CONTAINER_NAME="tfstate"
LOCATION="${AZ_REGION:-ukwest}"

echo "=== Terraform State Bootstrap ==="
echo "Environment:     $ENVIRONMENT"
echo "Resource Group:  $RESOURCE_GROUP"
echo "Storage Account: $STORAGE_ACCOUNT"
echo "Container:       $CONTAINER_NAME"
echo "Location:        $LOCATION"
echo ""

# Check if logged in to Azure
if ! az account show &>/dev/null; then
    echo "Error: Not logged in to Azure. Run 'az login' first."
    exit 1
fi

# Create resource group if it doesn't exist
echo "Checking resource group..."
if az group show --name "$RESOURCE_GROUP" &>/dev/null; then
    echo "✓ Resource group '$RESOURCE_GROUP' already exists"
else
    echo "Creating resource group '$RESOURCE_GROUP'..."
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --output none
    echo "✓ Resource group created"
fi

# Create storage account if it doesn't exist
echo "Checking storage account..."
if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "✓ Storage account '$STORAGE_ACCOUNT' already exists"
else
    echo "Creating storage account '$STORAGE_ACCOUNT'..."
    az storage account create \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Standard_LRS \
        --min-tls-version TLS1_2 \
        --allow-blob-public-access false \
        --output none
    echo "✓ Storage account created"
fi

# Get storage account key
echo "Retrieving storage account key..."
ACCOUNT_KEY=$(az storage account keys list \
    --resource-group "$RESOURCE_GROUP" \
    --account-name "$STORAGE_ACCOUNT" \
    --query '[0].value' \
    --output tsv)

# Create container if it doesn't exist
echo "Checking container..."
if az storage container show --name "$CONTAINER_NAME" --account-name "$STORAGE_ACCOUNT" --account-key "$ACCOUNT_KEY" &>/dev/null; then
    echo "✓ Container '$CONTAINER_NAME' already exists"
else
    echo "Creating container '$CONTAINER_NAME'..."
    az storage container create \
        --name "$CONTAINER_NAME" \
        --account-name "$STORAGE_ACCOUNT" \
        --account-key "$ACCOUNT_KEY" \
        --output none
    echo "✓ Container created"
fi

echo ""
echo "=== Bootstrap Complete ==="
echo "Terraform backend configuration:"
echo "  resource_group_name  = \"$RESOURCE_GROUP\""
echo "  storage_account_name = \"$STORAGE_ACCOUNT\""
echo "  container_name       = \"$CONTAINER_NAME\""
echo ""
echo "Run 'cd environments/$ENVIRONMENT && terragrunt run-all init' to initialize"
