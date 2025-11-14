# Google SSO Configuration

This guide shows how to configure Atlantis with Google OAuth2 single sign-on.

## Google OAuth2 Setup

1. **Create OAuth2 Credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Application type: Web application
   - Name: "Atlantis Terraform Automation"

2. **Configure Authorized Redirect URIs**:
   ```
   https://atlantis.your-domain.com/oauth2/callback
   ```

3. **Configure Authorized Origins** (optional):
   ```
   https://atlantis.your-domain.com
   ```

## Google Workspace Configuration

If using Google Workspace (formerly G Suite):

1. **Domain Verification**:
   - Verify your domain in Google Search Console
   - Add domain to Google Workspace

2. **Admin Console Settings**:
   - Go to Google Admin Console
   - Security > API Controls > Domain-wide Delegation
   - Add client ID if using service account (optional)

## Kubernetes Secret

Create the OAuth2 secret with Google credentials:

```bash
kubectl create secret generic atlantis-oauth2 \
  --from-literal=google-client-id="YOUR-GOOGLE-CLIENT-ID" \
  --from-literal=google-client-secret="YOUR-GOOGLE-CLIENT-SECRET" \
  --from-literal=cookie-secret="$(openssl rand -base64 32)" \
  -n atlantis
```

## Service Account for Group Checking (Optional)

If you want to check Google Groups membership:

1. **Create Service Account**:
   ```bash
   gcloud iam service-accounts create atlantis-groups \
     --display-name="Atlantis Groups Checker"
   ```

2. **Download Key**:
   ```bash
   gcloud iam service-accounts keys create google-service-account.json \
     --iam-account=atlantis-groups@PROJECT-ID.iam.gserviceaccount.com
   ```

3. **Create Kubernetes Secret**:
   ```bash
   kubectl create secret generic google-service-account \
     --from-file=credentials.json=google-service-account.json \
     -n atlantis
   ```

4. **Enable Directory API**:
   - Go to Google Cloud Console > APIs & Services > Library
   - Search for "Admin SDK API" and enable it

## Helm Installation

```bash
helm upgrade --install atlantis atlantis/atlantis \
  --namespace atlantis \
  --values values-google.yaml \
  --values ../values.yaml
```

## Group-Based Access Control

To restrict access to specific Google Groups:

1. **Find Group Email**:
   ```bash
   # In Google Admin Console, find your group email
   # Example: devops@your-domain.com
   ```

2. **Add to configuration**:
   ```yaml
   - --google-group=devops@your-domain.com
   ```

## Troubleshooting

### Common Issues

**"Invalid redirect URI"**:
- Ensure redirect URI exactly matches Google OAuth2 configuration
- Verify HTTPS is used in production
- Check for trailing slashes

**"User not in allowed domain"**:
- Verify `--email-domain` matches your Google Workspace domain
- Check user's primary email domain in Google Admin Console

**"Groups checking failed"**:
- Verify service account has Directory API access
- Check domain-wide delegation is configured
- Ensure group email is correct

**"Cookie errors"**:
- Verify cookie secret is properly base64 encoded
- Check cookie domain matches your ingress hostname
- Ensure secure cookies are used with HTTPS

### Debug Commands
```bash
# Check OAuth2 proxy logs
kubectl logs deployment/atlantis -n atlantis -c oauth2-proxy

# Test Google API access
kubectl exec -it deployment/atlantis -n atlantis -c oauth2-proxy -- \
  curl -H "Authorization: Bearer TOKEN" \
  "https://www.googleapis.com/oauth2/v2/userinfo"
```

## Advanced Configuration

### Custom Scopes
```yaml
- --scope=openid profile email https://www.googleapis.com/auth/admin.directory.group.readonly
```

### Session Configuration
```yaml
- --cookie-expire=168h  # 1 week
- --cookie-refresh=1h   # Refresh every hour
- --session-store-type=redis  # For HA deployments
```

### Multiple Domains
```yaml
- --email-domain=domain1.com
- --email-domain=domain2.com
```