#!/bin/bash
set -e

# Atlantis with AI Analysis - Installation Script
echo "🚀 Installing Atlantis with AI-powered Terraform plan analysis..."

# Configuration
NAMESPACE="atlantis"
RELEASE_NAME="atlantis"
CHART_VERSION="5.18.0"

# Add Atlantis Helm repository
echo "📦 Adding Atlantis Helm repository..."
helm repo add atlantis https://runatlantis.github.io/helm-charts
helm repo update

# Create namespace if it doesn't exist
echo "📂 Creating namespace: $NAMESPACE"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Install Atlantis with custom values
echo "⚙️  Installing Atlantis with AI analysis capabilities..."
helm upgrade --install $RELEASE_NAME atlantis/atlantis \
  --namespace $NAMESPACE \
  --version $CHART_VERSION \
  --values values.yaml

echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update values.yaml with your specific configuration"
echo "2. Create required secrets (GitHub App, OAuth2, AWS credentials)"
echo "3. Configure DNS to point to your ingress"
echo "4. Update atlantis.yaml with your Terraform repository structure"
echo ""
echo "🔗 Access Atlantis at: https://atlantis.your-domain.com"