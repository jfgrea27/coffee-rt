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

## GitHub Actions OIDC Setup

To enable CI/CD to deploy to Azure, create an App Registration with federated credentials:

```bash
# 1. Create the app registration
APP_ID=$(az ad app create --display-name "coffee-rt-github-actions" --query appId -o tsv)

# 2. Create service principal
az ad sp create --id $APP_ID

# 3. Add federated credential for GitHub OIDC
az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:jfgrea27/coffee-rt:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'

# 4. Grant Contributor role on subscription
az role assignment create --assignee $APP_ID --role Contributor \
  --scope /subscriptions/$(az account show --query id -o tsv)

# 5. Get values for GitHub secrets
echo "AZURE_CLIENT_ID: $APP_ID"
az account show --query "{AZURE_TENANT_ID: tenantId, AZURE_SUBSCRIPTION_ID: id}" -o table
```

Set these as repository secrets in GitHub (Settings → Secrets and variables → Actions):
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

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
export API_VERSION=v2

export BASTION_IP=$(az vm list-ip-addresses \
    --resource-group coffee-rt-dev-rg \
    --name coffee-rt-dev-bastion \
    --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)

scp -i ~/.ssh/id_rsa_azure helm/coffee-rt/values.deploy.$API_VERSION.yaml azureuser@$BASTION_IP:~/

```

```sh

export API_VERSION=v2

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
    --set flink.job.image.repository=${ACR_LOGIN_SERVER}/coffee-rt/flink-job \
    --set redis.image

```
