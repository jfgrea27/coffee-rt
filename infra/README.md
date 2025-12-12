# Coffee-RT Infrastructure

Terragrunt configuration for deploying coffee-rt to Azure Kubernetes Service (AKS).

## Architecture

```
infra/
├── root.hcl                    # Root config (providers, remote state)
├── modules/
│   ├── resource-group/         # Azure Resource Group (foundation)
│   ├── vnet/                   # Azure Virtual Network + subnets
│   ├── aks/                    # Azure Kubernetes Service (private cluster)
│   ├── acr/                    # Azure Container Registry
│   ├── bastion/                # Bastion VM for private cluster access
│   └── github-oidc/            # GitHub Actions OIDC authentication
└── environments/
    └── dev/                    # Development environment
        ├── env.hcl             # Dev-specific defaults
        ├── resource-group/
        ├── vnet/
        ├── acr/
        ├── aks/
        ├── bastion/
        └── github-oidc/
```

## Prerequisites

1. **Azure CLI** - authenticated with `az login`
2. **Terraform** >= 1.5.0
3. **Terragrunt** >= 0.50.0

### Create State Storage (one-time setup)

```bash
cd infra
./init-tf-state.sh dev
```

Or manually:

```bash
az group create --name coffee-rt-tfstate-rg --location ukwest
az storage account create --name coffeertstatedev --resource-group coffee-rt-tfstate-rg --location ukwest --sku Standard_LRS
az storage container create --name tfstate --account-name coffeertstatedev
```

## Usage

### Deploy Infrastructure

```bash
cd infra/environments/dev

# Deploy in order (dependencies)
cd resource-group && terragrunt apply
cd ../vnet && terragrunt apply
cd ../acr && terragrunt apply
cd ../aks && terragrunt apply

# Or deploy all at once
terragrunt run-all apply
```

### Connect to AKS

The cluster is private - see [Bastion](#bastion-private-cluster-access) section for access instructions.

### Push Images and Chart to ACR

```bash
# Login to ACR
ACR_NAME=$(terragrunt output -raw -chdir=environments/dev/acr name)
az acr login --name $ACR_NAME

# Tag and push images
docker tag coffee-rt/cafe-order-api:latest $ACR_NAME.azurecr.io/coffee-rt/cafe-order-api:latest
docker push $ACR_NAME.azurecr.io/coffee-rt/cafe-order-api:latest

# Package and push Helm chart to ACR (OCI)
cd helm/coffee-rt
helm package .
helm push coffee-rt-0.1.0.tgz oci://$ACR_NAME.azurecr.io/helm
```

### Deploy Application

Deploy the application and dependencies manually using Helm:

```bash
# Create namespace
kubectl create namespace coffee-ns

# Add Bitnami repo for dependencies
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Deploy PostgreSQL
helm install postgresql bitnami/postgresql \
  --namespace coffee-ns \
  --set auth.database=coffee-rt \
  --set auth.username=coffee-rt \
  --set auth.password=your-password

# Deploy Redis
helm install redis bitnami/redis \
  --namespace coffee-ns \
  --set auth.enabled=false

# Deploy Kafka (for v3 architecture)
helm install kafka bitnami/kafka \
  --namespace coffee-ns \
  --set kraft.enabled=true

# Deploy coffee-rt from ACR
ACR_NAME=$(terragrunt output -raw -chdir=infra/environments/dev/acr name)
helm install coffee-rt oci://$ACR_NAME.azurecr.io/helm/coffee-rt \
  --namespace coffee-ns \
  --set api.image.repository=$ACR_NAME.azurecr.io/coffee-rt/cafe-order-api \
  --set api.image.tag=latest
```

## Module Details

### Resource Group Module

Creates the Azure Resource Group that contains all other resources. This module is the foundation and must be deployed first.

### VNet Module

Creates Azure Virtual Network with:

- AKS subnet (CNI networking)
- Network Security Group

### AKS Module

Creates AKS cluster with:

- System node pool (control plane workloads)
- Workload node pool (application workloads)
- Azure CNI networking
- Workload Identity enabled
- Azure RBAC integration
- Log Analytics monitoring

### ACR Module

Creates Azure Container Registry for storing Docker images and Helm charts.

## Scaling

### Node Scaling

```bash
# Enable autoscaling with higher limits
cd infra/environments/dev/aks
terragrunt apply \
  -var="enable_autoscaling=true" \
  -var="workload_node_max=10"
```

### Application Scaling

```bash
# Scale deployments via kubectl
kubectl scale deployment coffee-rt-api --replicas=5 -n coffee-ns

# Or via Helm upgrade
helm upgrade coffee-rt oci://$ACR_NAME.azurecr.io/helm/coffee-rt \
  --namespace coffee-ns \
  --set api.replicas=5
```

## Cleanup

```bash
# Delete application first
helm uninstall coffee-rt -n coffee-ns
helm uninstall kafka -n coffee-ns
helm uninstall redis -n coffee-ns
helm uninstall postgresql -n coffee-ns
kubectl delete namespace coffee-ns

# Destroy infrastructure
cd infra/environments/dev
terragrunt run-all destroy
```

## Bastion (Private Cluster Access)

The AKS cluster is private - the API server is only accessible from within the VNet. Use the bastion VM to access the cluster.

### Prerequisites

Generate an RSA SSH key (Azure doesn't support ed25519):

```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_azure -C "your-email@example.com"
```

### Deploy Bastion

```bash
cd infra/environments/dev/bastion

# Set environment variables
export BASTION_SSH_PUBLIC_KEY="$(cat ~/.ssh/id_rsa_azure.pub)"
export BASTION_ALLOWED_IP="$(curl -s ifconfig.me)/32"

# Deploy
terragrunt apply
```

### Connect to Bastion

```bash
# Get bastion public IP
BASTION_IP=$(az vm list-ip-addresses \
  --resource-group coffee-rt-dev-rg \
  --name coffee-rt-dev-bastion \
  --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)

# SSH to bastion
ssh -i ~/.ssh/id_rsa_azure azureuser@$BASTION_IP
```

### Access AKS from Bastion

Once connected to the bastion:

```bash
# Get AKS credentials
az login
az aks get-credentials --resource-group coffee-rt-dev-rg --name coffee-rt-dev-aks

# Verify connection
kubectl get nodes

# Access services via port-forward
kubectl port-forward svc/coffee-rt-frontend 8080:80 -n coffee-ns &
kubectl port-forward svc/coffee-rt-grafana 3000:80 -n coffee-ns &
```

### Update Allowed IPs

If your IP changes:

```bash
export BASTION_ALLOWED_IP="$(curl -s ifconfig.me)/32"
terragrunt apply
```

### Upgrade in bastion

```sh
# copy values.yaml
export API_VERSION=v1

export BASTION_IP=$(az vm list-ip-addresses \
    --resource-group coffee-rt-dev-rg \
    --name coffee-rt-dev-bastion \
    --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)

scp -i ~/.ssh/id_rsa_azure helm/coffee-rt/values.deploy.$API_VERSION.yaml azureuser@$BASTION_IP:~/

```

```sh
export API_VERSION=v1

# inside bastion
kubectl create namespace coffee-ns --dry-run=client -o yaml | kubectl apply -f -

export ACR_NAME=coffeertdevacr
#
CHART_VERSION=$(az acr repository show-tags --name $ACR_NAME --repository helm/coffee-rt --orderby time_desc --top 1 -o tsv)


ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"

# helm login
ACCESS_TOKEN=$(az acr login --name $ACR_NAME --expose-token --query accessToken -o tsv)
echo $ACCESS_TOKEN | helm registry login ${ACR_NAME}.azurecr.io \
  --username 00000000-0000-0000-0000-000000000000 \
  --password-stdin

# helm upgrade
helm upgrade --install coffee oci://${ACR_LOGIN_SERVER}/helm/coffee-rt --version $CHART_VERSION \
    --namespace coffee-ns \
    -f ~/values.deploy.${API_VERSION}.yaml \
    --set api.image.repository=${ACR_LOGIN_SERVER}/coffee-rt/cafe-order-api \
    --set aggregator.image.repository=${ACR_LOGIN_SERVER}/coffee-rt/cafe-order-aggregator \
    --set frontend.image.repository=${ACR_LOGIN_SERVER}/coffee-rt/cafe-dashboard \
    --set stream-worker.image.repository=${ACR_LOGIN_SERVER}/coffee-rt/stream-worker \
    --set flink.job.image.repository=${ACR_LOGIN_SERVER}/coffee-rt/flink-job

```
