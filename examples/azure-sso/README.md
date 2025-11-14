# Azure AD SSO Configuration

This guide shows how to configure Atlantis with Azure Active Directory single sign-on.

## Azure AD App Registration

1. **Register Application**:
   ```bash
   # Via Azure CLI
   az ad app create \
     --display-name "Atlantis Terraform Automation" \
     --web-redirect-uris "https://atlantis.your-domain.com/oauth2/callback"
   ```

2. **Configure Authentication**:
   - Platform: Web
   - Redirect URI: `https://atlantis.your-domain.com/oauth2/callback`
   - Logout URL: `https://atlantis.your-domain.com/oauth2/sign_out`
   - ID tokens: Enabled

3. **API Permissions**:
   - Microsoft Graph: `User.Read` (required)
   - Microsoft Graph: `GroupMember.Read.All` (optional, for group-based access)

4. **Create Client Secret**:
   ```bash
   az ad app credential reset --id YOUR-APP-ID
   ```

## Kubernetes Secret

Create the OAuth2 secret with Azure AD credentials:

```bash
kubectl create secret generic atlantis-oauth2 \
  --from-literal=azure-client-id="YOUR-AZURE-CLIENT-ID" \
  --from-literal=azure-client-secret="YOUR-AZURE-CLIENT-SECRET" \
  --from-literal=cookie-secret="$(openssl rand -base64 32)" \
  -n atlantis
```

## Helm Installation

```bash
helm upgrade --install atlantis atlantis/atlantis \
  --namespace atlantis \
  --values values-azure.yaml \
  --values ../values.yaml
```

## Group-Based Access Control

To restrict access to specific Azure AD groups:

1. **Find Group ID**:
   ```bash
   az ad group show --group "DevOps Team" --query objectId
   ```

2. **Add to configuration**:
   ```yaml
   - --allowed-group=YOUR-GROUP-OBJECT-ID
   ```

## Troubleshooting

### Common Issues

**"User not in allowed domain"**:
- Verify `--email-domain` matches your Azure AD domain
- Check user's primary email in Azure AD

**"Invalid redirect URI"**:
- Ensure redirect URI exactly matches Azure AD app registration
- Verify HTTPS is used in production

**"Token validation failed"**:
- Check tenant ID in issuer URL
- Verify app registration has correct permissions