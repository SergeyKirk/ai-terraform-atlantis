# AI Analysis Deep Dive

This guide provides a comprehensive overview of the AI-powered Terraform plan analysis capabilities.

## 🤖 How It Works

The AI analyzer uses AWS Bedrock's Claude Sonnet 4 model to perform multi-pass analysis of Terraform plans:

1. **Plan Extraction**: Converts binary Terraform plans to text and JSON formats
2. **Resource Analysis**: Identifies and categorizes resource changes by criticality
3. **Context Gathering**: Collects git diffs and configuration files for full context
4. **Multi-Pass AI Analysis**: Three-stage analysis for comprehensive insights
5. **Formatted Output**: Structured recommendations for operations teams

## 📊 Analysis Phases

### Phase 1: Blast Radius Assessment
```python
# Risk levels are automatically determined based on:
CRITICAL = "Resources that can cause service outages"
HIGH = "Resources that affect security or performance" 
MEDIUM = "Resources with moderate operational impact"
LOW = "Resources with minimal impact"

# Critical resource types include:
critical_resources = {
    'aws_eks_cluster', 'aws_eks_node_group', 'aws_eks_addon',
    'aws_iam_role', 'aws_iam_policy', 'aws_security_group',
    'aws_rds_cluster', 'aws_rds_instance', 'aws_vpc'
}
```

### Phase 2: Technical Analysis
- **Implementation Details**: Specific configuration changes and effects
- **Security Implications**: IAM, networking, encryption analysis
- **Performance Impact**: Capacity, scaling, resource optimization
- **Deployment Considerations**: Order of operations and timing

### Phase 3: Synthesis & Recommendations
- **Executive Summary**: Key findings for stakeholders
- **Pre-deployment Actions**: Required steps before applying
- **Monitoring Strategy**: What to watch during deployment
- **Rollback Planning**: Recovery procedures if issues arise

## 🎯 Analysis Examples

### EKS Cluster Update
```
🚨 **RISK: HIGH** | 🎯 **SERVICES: EKS, Networking** | ⏱️ **DOWNTIME: 5-10 minutes**

=== 🎯 BLAST RADIUS & IMPACT ASSESSMENT ===
📊 EKS cluster version upgrade from 1.27 to 1.28 affects all workloads
🔄 Node group rolling update will cause pod rescheduling
⚠️ API server briefly unavailable during control plane upgrade
🔗 Dependencies: All applications in this cluster will be impacted

=== 🔧 TECHNICAL ANALYSIS ===
🛡️ Security: New RBAC permissions required for v1.28 features
📊 Performance: Improved scheduling and resource allocation
🔄 Deployment: Control plane upgrade takes 10-15 minutes
⚠️ Risk: Workloads may experience brief connection interruptions

=== 📋 RECOMMENDATIONS & NEXT STEPS ===
📋 **Executive Summary**: EKS upgrade with security improvements, 15min maintenance window
🎯 **Pre-deployment**: Schedule during low-traffic period, verify addon compatibility
🔍 **Monitoring**: Watch cluster status, node readiness, pod scheduling
🚨 **Rollback Strategy**: Not supported - ensure thorough testing in staging
```

### IAM Policy Changes
```
⚠️ **RISK: MEDIUM** | 🎯 **SERVICES: IAM** | ⏱️ **DOWNTIME: None**

=== 🎯 BLAST RADIUS & IMPACT ASSESSMENT ===
📊 IAM policy update affects 3 service accounts in production
🔒 Removing overprivileged S3 permissions, adding specific bucket access
✅ No service interruption expected for properly configured applications
🔗 Dependencies: Applications using wildcard S3 permissions

=== 🔧 TECHNICAL ANALYSIS ===
🛡️ Security: Improves security posture by removing S3:* permissions
📊 Performance: No performance impact expected
🔄 Deployment: Policy changes take effect immediately
⚠️ Risk: Applications with hardcoded bucket access may fail

=== 📋 RECOMMENDATIONS & NEXT STEPS ===
📋 **Executive Summary**: IAM hardening with minimal risk
🎯 **Pre-deployment**: Verify applications use environment-specific bucket variables
🔍 **Monitoring**: Watch application logs for S3 access denied errors
🚨 **Rollback Strategy**: Keep previous policy version for 24h quick rollback
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BEDROCK_MODEL_ID` | Claude model to use | `anthropic.claude-sonnet-4-20250514-v1:0` |
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `BEDROCK_INFERENCE_PROFILE_ARN` | Cost optimization profile | None |
| `BASE_REPO_OWNER` | GitHub organization | `your-org` |
| `BASE_REPO_NAME` | Repository name | `your-repo` |
| `PROJECT_NAME` | Project identifier | From environment |
| `WORKSPACE` | Terraform workspace | From Atlantis |

### Analysis Customization

```python
# Modify critical resource types in ai_analyzer.py
self.critical_resources = {
    'aws_eks_cluster',           # Kubernetes clusters
    'aws_rds_cluster',          # Databases
    'aws_security_group',       # Network security
    'aws_iam_role',            # Access control
    'aws_lambda_function',      # Add Lambda functions
    'aws_api_gateway_rest_api', # Add API Gateway
    # Add your organization-specific critical resources
}
```

## 📈 Cost Considerations

### Bedrock Pricing
- **Input Tokens**: ~$0.003 per 1K tokens
- **Output Tokens**: ~$0.015 per 1K tokens
- **Typical Plan Analysis**: 5K-15K input tokens, 1K-3K output tokens
- **Estimated Cost**: $0.05-$0.20 per analysis

### Cost Optimization
```yaml
# Use inference profiles for reduced costs
environment:
  BEDROCK_INFERENCE_PROFILE_ARN: "arn:aws:bedrock:region:account:application-inference-profile/profile-id"
  
# Alternative: Regional optimization
  AWS_REGION: us-west-2  # May have different pricing
```

### Usage Monitoring
```bash
# Monitor Bedrock costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --filter file://bedrock-filter.json
```

## 🚀 Performance Optimization

### Analysis Speed
- **Small Plans** (<50 resources): 10-20 seconds
- **Medium Plans** (50-200 resources): 20-45 seconds  
- **Large Plans** (>200 resources): 45-90 seconds

### Optimization Strategies
```python
# Truncate large plans for faster analysis
def _truncate_text(self, text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    
    # Keep beginning and end for context
    head_chars = int(max_chars * 0.7)
    tail_chars = max_chars - head_chars - 20
    return text[:head_chars] + "\n... [truncated] ...\n" + text[-tail_chars:]
```

## 🔍 Troubleshooting

### Common Issues

**"Bedrock Access Denied"**
```bash
# Check IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::account:role/atlantis-role \
  --action-names bedrock:InvokeModel \
  --resource-arns arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0

# Verify model access
aws bedrock list-foundation-models --region us-east-1 | grep claude-sonnet-4
```

**"Analysis Failed"**
```bash
# Check Atlantis logs
kubectl logs deployment/atlantis -n atlantis -c atlantis | grep -A 10 -B 10 "AI analysis"

# Test analysis script directly
kubectl exec -it deployment/atlantis -n atlantis -- \
  python3 /scripts/ai_analyzer.py /tmp/test-plan.tfplan
```

**"Slow Analysis Performance"**
```python
# Enable debug logging in ai_analyzer.py
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add timing measurements
start_time = time.time()
# ... analysis code ...
logger.info(f"Analysis completed in {time.time() - start_time:.2f} seconds")
```

## 🛠️ Customization Examples

### Custom Risk Assessment
```python
def _assess_criticality(self, resource_type: str, actions: List[str]) -> CriticalityLevel:
    # Organization-specific critical resources
    org_critical_resources = {
        'aws_route53_zone',      # DNS is critical for your org
        'aws_cloudfront_distribution', # CDN impacts all users
        'custom_resource_type'   # Your custom resources
    }
    
    if resource_type in org_critical_resources:
        if 'delete' in actions:
            return CriticalityLevel.CRITICAL
        return CriticalityLevel.HIGH
    
    # Default logic
    return super()._assess_criticality(resource_type, actions)
```

### Custom Analysis Prompts
```python
def _analyze_context(self, plan_file_path: str, blast_radius: BlastRadiusAssessment, 
                    total_changes: int, critical_count: int, high_count: int) -> str:
    
    # Organization-specific context
    org_context = f"""
    Organization Guidelines:
    - All production changes require approval from @platform-team
    - Database changes must include rollback plan
    - Network changes require security team review
    """
    
    prompt = f"""
    Role: Senior Platform Engineer at YourOrg analyzing infrastructure changes.
    
    {org_context}
    
    Context:
    - Repository: {self.repo_owner}/{self.repo_name}
    # ... rest of prompt
    """
```

## 📚 Advanced Features

### Multi-Region Analysis
Configure analysis for multiple regions:
```yaml
environment:
  AWS_REGIONS: "us-east-1,eu-west-1,ap-southeast-1"
  PRIMARY_REGION: "us-east-1"
```

### Integration with External Tools
```python
# Send analysis to Slack
def send_to_slack(self, analysis: str, webhook_url: str):
    payload = {
        "text": f"🤖 Terraform Plan Analysis for PR #{self.pr_number}",
        "attachments": [{
            "color": "warning" if "HIGH" in analysis else "good",
            "text": analysis[:3000]  # Slack message limit
        }]
    }
    requests.post(webhook_url, json=payload)

# Save analysis to database
def save_analysis(self, analysis: str):
    # Store for trend analysis and reporting
    pass
```

### Custom Metrics
```python
# Export metrics to CloudWatch
def export_metrics(self, blast_radius: BlastRadiusAssessment):
    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_metric_data(
        Namespace='Atlantis/Analysis',
        MetricData=[
            {
                'MetricName': 'CriticalChanges',
                'Value': len(blast_radius.critical_changes),
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Workspace', 'Value': self.workspace},
                    {'Name': 'Repository', 'Value': self.repo_name}
                ]
            }
        ]
    )
```

This AI analysis system transforms Terraform plan review from a manual, error-prone process into an intelligent, consistent, and comprehensive evaluation that helps teams make better infrastructure decisions.