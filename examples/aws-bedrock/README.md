# AWS Bedrock Setup for AI Analysis

This guide shows how to configure AWS Bedrock for AI-powered Terraform plan analysis.

## Prerequisites

- AWS account with Bedrock access
- Claude Sonnet 4 model enabled in your region
- IAM permissions for Bedrock

## Model Access

1. **Enable Claude Sonnet 4**:
   ```bash
   # Check available models
   aws bedrock list-foundation-models --region us-east-1
   
   # Request access to Claude Sonnet 4
   # Go to AWS Console > Bedrock > Model access
   # Request access to "anthropic.claude-sonnet-4-20250514-v1:0"
   ```

2. **Verify Access**:
   ```bash
   aws bedrock-runtime invoke-model \
     --model-id anthropic.claude-sonnet-4-20250514-v1:0 \
     --body '{"anthropic_version": "bedrock-2023-05-31", "max_tokens": 100, "messages": [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]}' \
     --region us-east-1 \
     /tmp/test-response.json
   ```

## IAM Configuration

### IAM Policy for Atlantis
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
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0"
            ]
        }
    ]
}
```

### IAM Role for EKS (IRSA)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::YOUR-ACCOUNT:oidc-provider/oidc.eks.REGION.amazonaws.com/id/CLUSTER-ID"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "oidc.eks.REGION.amazonaws.com/id/CLUSTER-ID:sub": "system:serviceaccount:atlantis:atlantis",
                    "oidc.eks.REGION.amazonaws.com/id/CLUSTER-ID:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
```

## Cost Optimization

### Inference Profiles
Use inference profiles for cost optimization:

```bash
# Create inference profile
aws bedrock create-application-inference-profile \
    --inference-profile-name "atlantis-cost-optimized" \
    --description "Cost-optimized profile for Atlantis AI analysis" \
    --model-source '{"copyFrom": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0"}'
```

### Environment Variables
```yaml
environment:
  AWS_REGION: us-east-1
  BEDROCK_MODEL_ID: "anthropic.claude-sonnet-4-20250514-v1:0"
  # Use inference profile for cost optimization
  BEDROCK_INFERENCE_PROFILE_ID: "your-inference-profile-id"
  # Or use ARN
  BEDROCK_INFERENCE_PROFILE_ARN: "arn:aws:bedrock:us-east-1:account:application-inference-profile/profile-id"
```

## Regional Considerations

### Supported Regions
Claude Sonnet 4 is available in:
- `us-east-1` (N. Virginia)
- `us-west-2` (Oregon) 
- `eu-west-1` (Ireland)
- `ap-southeast-1` (Singapore)

### Cross-Region Access
```yaml
environment:
  AWS_REGION: us-east-1  # Use closest supported region
  BEDROCK_REGION: us-east-1  # Override for Bedrock specifically
```

## Monitoring and Logging

### CloudWatch Logs
```bash
# Create log group for Atlantis
aws logs create-log-group --log-group-name "/atlantis/ai-analysis"

# Set retention
aws logs put-retention-policy \
    --log-group-name "/atlantis/ai-analysis" \
    --retention-in-days 30
```

### Bedrock Metrics
Monitor these CloudWatch metrics:
- `AWS/Bedrock/InvocationsCount`
- `AWS/Bedrock/InputTokens`
- `AWS/Bedrock/OutputTokens`
- `AWS/Bedrock/InvocationLatency`

## Security Best Practices

1. **Least Privilege**: Only grant `bedrock:InvokeModel` for specific models
2. **VPC Endpoints**: Use VPC endpoints for private access
3. **Logging**: Enable CloudTrail for audit logging
4. **Cost Controls**: Set up billing alerts for Bedrock usage

## Troubleshooting

### Common Issues

**"Access Denied to Bedrock"**:
- Verify model access is granted in AWS Console
- Check IAM permissions
- Confirm region availability

**"Model Not Found"**:
- Verify model ID is correct
- Check region supports the model
- Ensure model access is approved

**"Rate Limiting"**:
- Implement exponential backoff
- Consider using inference profiles
- Monitor usage patterns

### Debug Commands
```bash
# Check Atlantis pod logs
kubectl logs -f deployment/atlantis -n atlantis -c atlantis

# Test Bedrock access from pod
kubectl exec -it deployment/atlantis -n atlantis -- \
  python3 -c "import boto3; print(boto3.client('bedrock-runtime', region_name='us-east-1').list_foundation_models())"
```