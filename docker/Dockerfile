FROM ghcr.io/runatlantis/atlantis:v0.35.0

# Add labels
LABEL maintainer="your-email@example.com" \
      description="Atlantis with AI-powered Terraform plan analysis" \
      version="0.0.1"

# Terraform version - keep aligned with your infrastructure requirements
ARG TERRAFORM_VERSION=1.8.3

# Install Terraform and Python for AI analysis
WORKDIR /tmp
USER root

# Install specific Terraform version
RUN curl -LOs https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    mv terraform /usr/local/bin/terraform${TERRAFORM_VERSION} && \
    ln -sf /usr/local/bin/terraform${TERRAFORM_VERSION} /usr/local/bin/terraform && \
    rm -rf /tmp/*

# Install Python and required packages for AWS Bedrock AI integration
RUN apk add --no-cache python3 py3-pip && \
    pip3 install boto3 requests --break-system-packages

# Create scripts directory and add AI analyzer
RUN mkdir -p /scripts
COPY ai_analyzer.py /scripts/
RUN chmod +x /scripts/ai_analyzer.py

# Return to original settings
WORKDIR /
USER atlantis
