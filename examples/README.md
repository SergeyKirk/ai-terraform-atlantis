# Configuration Examples

This directory contains example configurations for different deployment scenarios.

## 🔗 SSO Providers

### [Azure SSO](azure-sso/)
Complete setup for Azure Active Directory single sign-on integration.

**Files:**
- `README.md` - Step-by-step Azure AD configuration guide
- `values-azure.yaml` - Helm values for Azure SSO

**Features:**
- Azure AD v2.0 endpoint integration
- Group-based access control
- Domain restrictions

### [Google SSO](google-sso/)
Google OAuth2 and Google Workspace integration.

**Files:**
- `README.md` - Google Cloud Console and Workspace setup
- `values-google.yaml` - Helm values for Google SSO

**Features:**
- Google Workspace domain restrictions
- Google Groups membership checking
- Service account integration

## 🤖 AI Provider

### [AWS Bedrock](aws-bedrock/)
AWS Bedrock configuration for AI-powered Terraform plan analysis.

**Files:**
- `README.md` - Comprehensive Bedrock setup guide
- `values-bedrock.yaml` - Helm values for Bedrock integration

**Features:**
- Claude Sonnet 4 model configuration
- IAM roles and permissions
- Cost optimization with inference profiles
- Regional deployment considerations

## 🚀 Quick Start

1. **Choose your SSO provider** (Azure or Google)
2. **Follow the provider's README** for external service setup
3. **Copy and customize the values file**:
   ```bash
   cp examples/azure-sso/values-azure.yaml my-values.yaml
   # Edit my-values.yaml with your configuration
   ```
4. **Install with multiple values files**:
   ```bash
   helm upgrade --install atlantis atlantis/atlantis \
     --namespace atlantis \
     --values helm/values.yaml \
     --values my-values.yaml
   ```

## 🔧 Customization

### Multiple Providers
You can combine configurations from different examples:

```bash
# Install with Azure SSO + Bedrock AI
helm upgrade --install atlantis atlantis/atlantis \
  --namespace atlantis \
  --values helm/values.yaml \
  --values examples/azure-sso/values-azure.yaml \
  --values examples/aws-bedrock/values-bedrock.yaml
```

### Override Specific Values
```bash
# Override just the domain
helm upgrade --install atlantis atlantis/atlantis \
  --namespace atlantis \
  --values examples/azure-sso/values-azure.yaml \
  --set ingress.host=atlantis.mydomain.com
```

## 📋 Configuration Matrix

| Example | SSO Provider | AI Analysis | Use Case |
|---------|-------------|-------------|----------|
| `azure-sso` | Azure AD | ✅ | Enterprise with Microsoft 365 |
| `google-sso` | Google | ✅ | Enterprise with Google Workspace |
| `aws-bedrock` | Any | ✅ | Focus on AI analysis features |

## 🛠️ Advanced Examples

For more complex scenarios, see:
- **Multi-region deployments**: [aws-bedrock/README.md](aws-bedrock/README.md#regional-considerations)
- **High availability**: Multiple replicas with shared storage
- **Cost optimization**: [aws-bedrock/README.md](aws-bedrock/README.md#cost-optimization)
- **Security hardening**: [../docs/SECURITY.md](../docs/SECURITY.md)

## 🤝 Contributing

Have a configuration for another SSO provider or cloud service? Please contribute!

1. Create a new directory: `examples/your-provider/`
2. Add `README.md` with setup instructions
3. Add `values-your-provider.yaml` with Helm values
4. Update this README with your example
5. Submit a pull request