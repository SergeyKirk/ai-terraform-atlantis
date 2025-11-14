# Security Guide

This guide covers security best practices for deploying Atlantis with AI analysis capabilities.

## 🔒 Threat Model

### Assets to Protect
- **Terraform State**: Infrastructure secrets and configuration
- **GitHub Access**: Repository write access and webhook secrets
- **AWS Credentials**: Bedrock and infrastructure management access
- **SSO Tokens**: User authentication and authorization data

### Attack Vectors
- Container escape and privilege escalation
- Network-based attacks on exposed services
- Credential theft and abuse
- Supply chain attacks via container images

## 🛡️ Security Controls

### 1. Secret Management

#### ✅ Kubernetes Secrets
```bash
# Never commit secrets - use Kubernetes secrets
kubectl create secret generic atlantis-github \
  --from-literal=app-id="12345" \
  --from-literal=webhook-secret="$(openssl rand -hex 32)" \
  --from-file=private-key=github-app-key.pem \
  -n atlantis

# Rotate secrets regularly
kubectl create secret generic atlantis-github-new \
  --from-literal=app-id="12345" \
  --from-literal=webhook-secret="$(openssl rand -hex 32)" \
  --from-file=private-key=github-app-key-new.pem \
  -n atlantis
```

#### ✅ External Secret Management (Recommended)
```yaml
# Using External Secrets Operator with AWS Secrets Manager
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: atlantis-secrets
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: atlantis
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: atlantis-github
spec:
  secretStoreRef:
    name: atlantis-secrets
    kind: SecretStore
  target:
    name: atlantis-github
  data:
  - secretKey: app-id
    remoteRef:
      key: atlantis/github
      property: app_id
```

#### ❌ Anti-Patterns
```yaml
# NEVER do this - secrets in values.yaml
githubApp:
  id: "12345"  # ❌ Exposed in Helm values
  secret: "plaintext-secret"  # ❌ Visible in git history
```

### 2. Network Security

#### ✅ Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: atlantis-network-policy
  namespace: atlantis
spec:
  podSelector:
    matchLabels:
      app: atlantis
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 4180
  egress:
  - to: []  # Allow all egress (required for GitHub/AWS API)
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

#### ✅ TLS Termination
```yaml
ingress:
  enabled: true
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
  tls:
    - secretName: atlantis-tls
      hosts:
        - atlantis.your-domain.com
```

### 3. Container Security

#### ✅ Security Context
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 100  # atlantis user
  runAsGroup: 1000
  fsGroup: 1000
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false

containerSecurityContext:
  runAsNonRoot: true
  runAsUser: 100
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
```

#### ✅ Resource Limits
```yaml
resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 2000m
    memory: 4Gi
    # Prevent DoS attacks
    ephemeral-storage: 10Gi
```

#### ✅ Image Security
```bash
# Scan images for vulnerabilities
docker scan your-account.dkr.ecr.region.amazonaws.com/atlantis-ai:latest

# Use specific tags, not 'latest'
image:
  repository: your-account.dkr.ecr.region.amazonaws.com/atlantis-ai
  tag: "0.35.0-ai.1.0"  # ✅ Specific version
  # tag: "latest"       # ❌ Unpredictable
```

### 4. IAM and RBAC

#### ✅ Minimal IAM Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "sts:AssumeRole"
            ],
            "Resource": [
                "arn:aws:iam::ACCOUNT:role/terraform-execution-role"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": ["us-east-1", "us-west-2"]
                }
            }
        }
    ]
}
```

#### ✅ Kubernetes RBAC
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: atlantis
  name: atlantis-role
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list"]
  resourceNames: ["atlantis-github", "atlantis-oauth2"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]
  resourceNames: ["atlantis-config"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: atlantis-binding
  namespace: atlantis
subjects:
- kind: ServiceAccount
  name: atlantis
  namespace: atlantis
roleRef:
  kind: Role
  name: atlantis-role
  apiGroup: rbac.authorization.k8s.io
```

### 5. Audit and Monitoring

#### ✅ Audit Logging
```yaml
# Enable audit logs in Atlantis
config: |
  ---
  log-level: info
  enable-diff-markdown-format: true
  
# CloudTrail for AWS API calls
{
  "eventVersion": "1.05",
  "userIdentity": {
    "type": "AssumedRole",
    "principalId": "AROABC123:atlantis",
    "arn": "arn:aws:sts::123456789012:assumed-role/AtlantisRole/atlantis"
  },
  "eventName": "InvokeModel",
  "sourceIPAddress": "10.0.1.100",
  "userAgent": "boto3/1.26.137",
  "requestParameters": {
    "modelId": "anthropic.claude-sonnet-4-20250514-v1:0"
  }
}
```

#### ✅ Security Monitoring
```yaml
# Prometheus alerts
groups:
- name: atlantis.rules
  rules:
  - alert: AtlantisHighMemoryUsage
    expr: container_memory_usage_bytes{pod=~"atlantis.*"} / container_spec_memory_limit_bytes > 0.9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Atlantis high memory usage"

  - alert: AtlantisUnauthorizedAccess
    expr: increase(nginx_ingress_controller_requests_total{service="atlantis",status=~"4.."}[5m]) > 10
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Multiple unauthorized access attempts to Atlantis"
```

## 🚨 Incident Response

### 1. Suspected Credential Compromise

```bash
# Immediate actions:
# 1. Rotate GitHub App credentials
gh api -X POST /app/installations/INSTALLATION_ID/access_tokens

# 2. Rotate AWS credentials
aws iam create-access-key --user-name atlantis-user
aws iam delete-access-key --access-key-id OLD-KEY-ID --user-name atlantis-user

# 3. Revoke user sessions
kubectl delete secret atlantis-oauth2
kubectl create secret generic atlantis-oauth2 \
  --from-literal=cookie-secret="$(openssl rand -base64 32)" \
  # ... other values
kubectl rollout restart deployment/atlantis -n atlantis
```

### 2. Suspicious Activity

```bash
# Check pod logs
kubectl logs -f deployment/atlantis -n atlantis --previous

# Check ingress logs
kubectl logs -f deployment/nginx-ingress-controller -n ingress-nginx | grep atlantis

# Check AWS CloudTrail
aws logs filter-log-events \
  --log-group-name CloudTrail/AuditLogs \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern '{ $.userIdentity.arn = "*atlantis*" }'
```

### 3. Container Compromise

```bash
# Immediate isolation
kubectl patch deployment atlantis -n atlantis -p '{"spec":{"replicas":0}}'

# Forensic analysis
kubectl exec -it atlantis-pod-name -n atlantis -- sh
# Check for:
# - Unexpected processes: ps aux
# - Network connections: netstat -tulnp
# - File modifications: find /app -type f -mtime -1
```

## ✅ Security Checklist

### Deployment
- [ ] Secrets stored in Kubernetes secrets (not values.yaml)
- [ ] Container runs as non-root user
- [ ] Resource limits configured
- [ ] Network policies applied
- [ ] TLS termination at ingress
- [ ] Security context configured

### Access Control
- [ ] GitHub App permissions minimized
- [ ] IAM roles follow least privilege
- [ ] SSO email domain restrictions configured
- [ ] Webhook endpoints bypass authentication only
- [ ] Service account RBAC configured

### Monitoring
- [ ] Audit logging enabled
- [ ] Security alerts configured
- [ ] CloudTrail enabled for AWS API calls
- [ ] Container image vulnerability scanning
- [ ] Regular credential rotation scheduled

### Incident Response
- [ ] Incident response procedures documented
- [ ] Emergency access procedures defined
- [ ] Contact information maintained
- [ ] Recovery procedures tested

## 📚 Additional Resources

- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
- [OWASP Container Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)

## 🔄 Regular Security Tasks

### Weekly
- [ ] Review access logs for anomalies
- [ ] Check for security updates to container images
- [ ] Verify backup procedures

### Monthly  
- [ ] Rotate OAuth2 cookie secrets
- [ ] Review IAM permissions and remove unused access
- [ ] Update security documentation

### Quarterly
- [ ] Rotate GitHub App credentials
- [ ] Conduct security assessment
- [ ] Review and test incident response procedures
- [ ] Update security training materials