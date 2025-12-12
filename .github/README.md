# GitHub Actions CI/CD Setup

This document describes how to configure GitHub Actions to build and push images to Azure Container Registry (ACR).

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- GitHub repository with admin access to configure secrets
- Azure Container Registry deployed

## Setup OIDC Authentication

We use OpenID Connect (OIDC) for authentication, which is more secure than storing credentials as secrets. GitHub Actions requests a short-lived token from Azure AD for each workflow run.

```bash
# 1. Update github_org in the terragrunt config
cd infra/environments/dev/github-oidc
vi terragrunt.hcl  # Set your GitHub org/username

# 2. Deploy
terragrunt apply

# 3. Get the values for GitHub secrets
terragrunt output github_secrets_summary
```

Then add the output values as GitHub secrets (see step 4 below).

### 2. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

| Secret Name             | How to Get Value                                          |
| ----------------------- | --------------------------------------------------------- |
| `AZURE_CLIENT_ID`       | From Terraform output, or `echo $APP_ID`                  |
| `AZURE_TENANT_ID`       | `az account show --query tenantId -o tsv`                 |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv`                       |
| `ACR_NAME`              | Your ACR name (e.g., `coffeertdevacr`)                    |
| `ACR_LOGIN_SERVER`      | Your ACR login server (e.g., `coffeertdevacr.azurecr.io`) |

### 3. Verify Setup

Push a change to main branch and check the Actions tab. The workflow should:

1. Detect which services changed
2. Run linting and tests
3. Build and push Docker images to ACR
4. Push Helm chart to ACR (if helm/ changed)

## Workflow Overview

```
┌─────────────┐
│  changes    │ Detect which services need rebuilding
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│  lint-backend  │  lint-frontend  │  lint-flink │
└───────┬────────┴────────┬────────┴──────┬─────┘
        │                 │               │
        ▼                 ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ unit-tests-   │ │ unit-tests-   │ │ unit-tests-   │
│ backend       │ │ frontend      │ │ flink         │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │               │
        └────────────────┬┴───────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  build-and-push     │ (main branch only)
              │  push-helm-chart    │
              └─────────────────────┘
```

## Change Detection

The CI automatically detects which services need rebuilding based on:

- Direct changes to a service's directory
- Changes to local dependencies (parsed from `pyproject.toml`)
- Changes to root `pyproject.toml` or `uv.lock`

See `.github/scripts/detect_changes.py` for the detection logic.

## Troubleshooting

### OIDC Login Fails

```
AADSTS70021: No matching federated identity record found
```

Check that the federated credential subject matches exactly:

- Branch pushes: `repo:<org>/<repo>:ref:refs/heads/<branch>`
- Pull requests: `repo:<org>/<repo>:pull_request`
- Tags: `repo:<org>/<repo>:ref:refs/tags/<tag>`

### ACR Push Fails

```
denied: requested access to the resource is denied
```

Verify the service principal has `AcrPush` role:

```bash
az role assignment list --assignee $APP_ID --scope $ACR_ID
```

### Missing Secrets

If secrets are not found, verify they're set at the repository level (not environment level) and the names match exactly.
