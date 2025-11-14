#!/usr/bin/env python3
"""
AI-powered Terraform Plan Analyzer for Atlantis
Analyzes Terraform plans using AWS Bedrock Claude models to provide:
- Risk assessment and blast radius analysis
- Infrastructure change impact evaluation
- Deployment recommendations
"""
import boto3
import json
import sys
import os
import subprocess
import re
from datetime import datetime, timezone
from typing import Optional, Dict, List, Set, Any
from dataclasses import dataclass
from enum import Enum

class CriticalityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ResourceChange:
    address: str
    resource_type: str
    actions: List[str]
    criticality: CriticalityLevel = CriticalityLevel.LOW

@dataclass
class BlastRadiusAssessment:
    critical_changes: List[ResourceChange]
    affected_services: List[str]
    criticality_level: CriticalityLevel
    estimated_downtime: Optional[str] = None
    downstream_impacts: List[str] = None
    
    def __post_init__(self):
        if self.downstream_impacts is None:
            self.downstream_impacts = []

class TerraformPlanAnalyzer:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        self.repo_owner = os.environ.get('BASE_REPO_OWNER', 'your-org')
        self.repo_name = os.environ.get('BASE_REPO_NAME', 'your-repo')
        self.pr_number = os.environ.get('PULL_NUM', 'unknown')
        self.project_name = os.environ.get('PROJECT_NAME', 'unknown')
        self.workspace = os.environ.get('WORKSPACE', 'unknown')
        self.base_branch = os.environ.get('BASE_BRANCH', 'main')
        self.bedrock_model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-sonnet-4-20250514-v1:0')
        self.bedrock_inference_profile_arn = os.environ.get('BEDROCK_INFERENCE_PROFILE_ARN')
        self.bedrock_inference_profile_id = os.environ.get('BEDROCK_INFERENCE_PROFILE_ID')
        
        # Critical resource types for prioritized analysis
        self.critical_resources = {
            'aws_eks_cluster', 'aws_eks_node_group', 'aws_eks_addon',
            'aws_iam_role', 'aws_iam_policy', 'aws_iam_role_policy_attachment',
            'aws_security_group', 'aws_security_group_rule', 'aws_vpc', 'aws_subnet',
            'aws_launch_template', 'aws_secretsmanager_secret', 'aws_ssm_parameter',
            'aws_cloudwatch_event_rule', 'aws_eventbridge_rule',
            'aws_sqs_queue', 'aws_sqs_queue_policy',
            'aws_rds_cluster', 'aws_rds_instance', 'aws_db_subnet_group'
        }

    def convert_plan_to_text(self, tfplan_path):
        """Convert binary terraform plan to readable text format"""
        try:
            print(f"🔄 Converting plan file to text: {tfplan_path}", flush=True)
            result = subprocess.run(['terraform', 'show', '-no-color', tfplan_path], 
                                  capture_output=True, text=True, cwd=os.path.dirname(tfplan_path))
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"❌ Error converting plan: {result.stderr}", flush=True)
                return None
        except Exception as e:
            print(f"❌ Exception converting plan: {str(e)}", flush=True)
            return None

    def convert_plan_to_json(self, tfplan_path):
        """Convert binary terraform plan to JSON for precise analysis"""
        try:
            print(f"🔄 Converting plan file to JSON: {tfplan_path}", flush=True)
            result = subprocess.run(['terraform', 'show', '-json', tfplan_path],
                                    capture_output=True, text=True, cwd=os.path.dirname(tfplan_path))
            if result.returncode == 0 and result.stdout:
                return result.stdout
            else:
                if result.stderr:
                    print(f"❌ Error converting plan to JSON: {result.stderr}", flush=True)
                return None
        except Exception as e:
            print(f"❌ Exception converting plan to JSON: {str(e)}", flush=True)
            return None
    
    def get_git_diff(self, plan_file_path: str, max_chars: int = 10000) -> Optional[str]:
        """Get git diff for terraform files in the current workspace"""
        try:
            work_dir = os.path.dirname(os.path.abspath(plan_file_path))
            subprocess.run(['git', 'fetch', '--all', '--prune', '-q'], cwd=work_dir)

            repo_root_proc = subprocess.run(['git', 'rev-parse', '--show-toplevel'], 
                                          capture_output=True, text=True, cwd=work_dir)
            if repo_root_proc.returncode != 0:
                return None
            repo_root = repo_root_proc.stdout.strip()
            rel_dir = os.path.relpath(work_dir, repo_root)

            # Get terraform file changes
            names_proc = subprocess.run(
                ['git', 'diff', f'origin/{self.base_branch}...HEAD', '--name-only', '--', rel_dir],
                capture_output=True, text=True, cwd=repo_root
            )
            if names_proc.returncode != 0:
                return None
                
            changed_files = [f.strip() for f in names_proc.stdout.splitlines() 
                           if f.strip().endswith(('.tf', '.tfvars'))]
            if not changed_files:
                return None

            # Get diff for terraform files
            diff_cmd = ['git', 'diff', f'origin/{self.base_branch}...HEAD', '--no-color', '--unified=3', '--'] + changed_files
            diff_proc = subprocess.run(diff_cmd, capture_output=True, text=True, cwd=repo_root)
            if diff_proc.returncode != 0:
                return None
                
            diff_text = diff_proc.stdout.strip()
            if len(diff_text) > max_chars:
                return diff_text[:max_chars] + "\n... [diff truncated]"
            return diff_text if diff_text else None
        except Exception:
            return None

    def collect_terraform_config(self, plan_file_path: str, max_chars: int = 20000) -> Optional[str]:
        """Collect relevant Terraform configuration files"""
        try:
            work_dir = os.path.dirname(os.path.abspath(plan_file_path))
            collected = []
            total = 0
            
            for root, dirs, files in os.walk(work_dir):
                dirs[:] = [d for d in dirs if d not in ['.terraform', '.git']]
                for f in sorted(files):
                    if not (f.endswith('.tf') or f.endswith('.tfvars')):
                        continue
                    file_path = os.path.join(root, f)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as fh:
                            content = fh.read()
                    except Exception:
                        continue
                    
                    rel_path = os.path.relpath(file_path, work_dir)
                    block = f"=== {rel_path} ===\n{content}"
                    
                    if (total + len(block)) > max_chars:
                        break
                    collected.append(block)
                    total += len(block)
                else:
                    continue
                break
            
            return "\n\n".join(collected) if collected else None
        except Exception:
            return None
    
    def extract_resource_changes(self, plan_json: Optional[str]) -> List[ResourceChange]:
        """Extract and categorize resource changes from plan JSON"""
        if not plan_json:
            return []
        
        try:
            data = json.loads(plan_json)
            resource_changes = []
            
            for rc in data.get('resource_changes', []):
                address = rc.get('address', '')
                resource_type = rc.get('type', '')
                actions = rc.get('change', {}).get('actions', [])
                
                # Assess criticality
                criticality = self._assess_criticality(resource_type, actions)
                
                resource_changes.append(ResourceChange(
                    address=address,
                    resource_type=resource_type,
                    actions=actions,
                    criticality=criticality
                ))
            
            return resource_changes
        except Exception as e:
            print(f"❌ Error extracting resource changes: {str(e)}", flush=True)
            return []
    
    def _assess_criticality(self, resource_type: str, actions: List[str]) -> CriticalityLevel:
        """Assess criticality level of a resource change"""
        if resource_type in self.critical_resources:
            if 'delete' in actions or 'replace' in actions:
                return CriticalityLevel.CRITICAL
            elif 'update' in actions:
                return CriticalityLevel.HIGH
            elif 'create' in actions:
                return CriticalityLevel.MEDIUM
        
        if 'delete' in actions or 'replace' in actions:
            return CriticalityLevel.MEDIUM
        
        return CriticalityLevel.LOW
    
    def assess_blast_radius(self, resource_changes: List[ResourceChange]) -> BlastRadiusAssessment:
        """Assess blast radius and potential impact"""
        critical_changes = [rc for rc in resource_changes 
                          if rc.criticality in [CriticalityLevel.HIGH, CriticalityLevel.CRITICAL]]
        
        affected_services = set()
        downstream_impacts = []
        max_criticality = CriticalityLevel.LOW
        
        for rc in critical_changes:
            if rc.criticality == CriticalityLevel.CRITICAL:
                max_criticality = CriticalityLevel.CRITICAL
            elif rc.criticality == CriticalityLevel.HIGH and max_criticality != CriticalityLevel.CRITICAL:
                max_criticality = CriticalityLevel.HIGH
            
            # Map resource types to services
            if 'eks' in rc.resource_type:
                affected_services.add('EKS')
                if 'delete' in rc.actions or 'replace' in rc.actions:
                    downstream_impacts.append('EKS workloads may experience disruption')
            elif 'iam' in rc.resource_type:
                affected_services.add('IAM')
                if 'delete' in rc.actions:
                    downstream_impacts.append('Services may lose access permissions')
            elif 'security_group' in rc.resource_type:
                affected_services.add('Networking')
                if 'delete' in rc.actions or 'replace' in rc.actions:
                    downstream_impacts.append('Network connectivity may be interrupted')
            elif 'rds' in rc.resource_type:
                affected_services.add('Database')
                if 'delete' in rc.actions or 'replace' in rc.actions:
                    downstream_impacts.append('Database downtime expected')
            elif 'sqs' in rc.resource_type:
                affected_services.add('Messaging')
                if 'delete' in rc.actions:
                    downstream_impacts.append('Message queue data will be lost')
        
        # Estimate downtime
        estimated_downtime = None
        if max_criticality == CriticalityLevel.CRITICAL:
            if any('rds' in rc.resource_type for rc in critical_changes):
                estimated_downtime = "5-15 minutes"
            elif any('eks' in rc.resource_type for rc in critical_changes):
                estimated_downtime = "2-10 minutes"
        
        return BlastRadiusAssessment(
            critical_changes=critical_changes,
            affected_services=list(affected_services),
            criticality_level=max_criticality,
            estimated_downtime=estimated_downtime,
            downstream_impacts=downstream_impacts
        )
    
    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncate text to max_chars with context preservation"""
        if not text or len(text) <= max_chars:
            return text or ''
        
        # Keep beginning and end for context
        head_chars = int(max_chars * 0.7)
        tail_chars = max_chars - head_chars - 20
        
        if tail_chars > 0:
            return text[:head_chars] + "\n... [truncated] ...\n" + text[-tail_chars:]
        else:
            return text[:max_chars] + "\n... [truncated]"
    
    def analyze_terraform_plan(self, plan_content: str, plan_file_path: str, 
                             code_diff: Optional[str] = None, tf_config: Optional[str] = None, 
                             plan_json: Optional[str] = None) -> str:
        """Advanced multi-pass Terraform plan analysis"""
        try:
            print("🔄 Phase 1: Extracting and analyzing resource changes...", flush=True)
            
            # Extract structured data
            resource_changes = self.extract_resource_changes(plan_json)
            blast_radius = self.assess_blast_radius(resource_changes)
            
            # Prepare analysis context
            total_changes = len(resource_changes)
            critical_count = len([rc for rc in resource_changes if rc.criticality == CriticalityLevel.CRITICAL])
            high_count = len([rc for rc in resource_changes if rc.criticality == CriticalityLevel.HIGH])
            
            print("🔄 Phase 2: Multi-pass AI analysis...", flush=True)
            
            # Pass 1: Context and blast radius analysis
            context_analysis = self._analyze_context(
                plan_file_path, blast_radius, total_changes, critical_count, high_count
            )
            
            # Pass 2: Technical analysis with plan details
            technical_analysis = self._analyze_technical(
                plan_content, code_diff, tf_config, resource_changes, context_analysis
            )
            
            # Pass 3: Final synthesis and recommendations
            final_synthesis = self._synthesize_analysis(
                context_analysis, technical_analysis, blast_radius
            )
            
            return self._format_final_output(context_analysis, technical_analysis, final_synthesis, blast_radius)
            
        except Exception as e:
            return f"❌ Error in analysis: {str(e)}"
    
    def _analyze_context(self, plan_file_path: str, blast_radius: BlastRadiusAssessment,
                        total_changes: int, critical_count: int, high_count: int) -> str:
        """First pass: Context and blast radius analysis"""
        
        risk_emoji = {
            CriticalityLevel.CRITICAL: "🚨",
            CriticalityLevel.HIGH: "⚠️",
            CriticalityLevel.MEDIUM: "📋",
            CriticalityLevel.LOW: "✅"
        }.get(blast_radius.criticality_level, "📋")
        
        prompt = f"""
Role: Principal DevOps Engineer analyzing Terraform infrastructure changes.

Context:
- Repository: {self.repo_owner}/{self.repo_name}
- PR: #{self.pr_number}
- Workspace: {self.workspace}
- Project: {self.project_name}

Change Summary:
- Total resources: {total_changes}
- Critical risk: {critical_count}
- High risk: {high_count}
- Risk level: {blast_radius.criticality_level.value.upper()}
- Affected services: {', '.join(blast_radius.affected_services) if blast_radius.affected_services else 'None'}
- Estimated downtime: {blast_radius.estimated_downtime or 'None expected'}

Critical Changes:
{chr(10).join([f"- {rc.address} ({rc.resource_type}): {', '.join(rc.actions)}" 
               for rc in blast_radius.critical_changes[:10]])}

Provide analysis focusing on:
1. {risk_emoji} **Blast Radius**: What systems/services will be affected?
2. ⚠️ **Risk Assessment**: Why this risk level and what could go wrong?
3. 🔗 **Dependencies**: Infrastructure dependencies and prerequisites
4. 🚨 **Breaking Changes**: Potential service disruptions

Output: Concise operational impact analysis (15-20 lines), use emojis.
"""
        
        return self._call_bedrock(prompt, 1500)
    
    def _analyze_technical(self, plan_content: str, code_diff: Optional[str], 
                          tf_config: Optional[str], resource_changes: List[ResourceChange],
                          context_analysis: str) -> str:
        """Second pass: Technical deep dive"""
        
        plan_snippet = self._truncate_text(plan_content or '', 15000)
        diff_snippet = self._truncate_text(code_diff or '<none>', 8000)
        config_snippet = self._truncate_text(tf_config or '<none>', 12000)
        
        critical_resources = [rc for rc in resource_changes 
                            if rc.criticality in [CriticalityLevel.HIGH, CriticalityLevel.CRITICAL]]
        
        prompt = f"""
Role: Continue technical analysis building on context.

Previous Context Analysis:
{self._truncate_text(context_analysis, 40000)}

Technical Details:

Critical Resource Changes:
{chr(10).join([f"- {rc.address} ({rc.resource_type}): {', '.join(rc.actions)} [{rc.criticality.value}]" 
               for rc in critical_resources[:15]])}

Plan Output:
{plan_snippet}

Code Changes:
{diff_snippet}

Current Config:
{config_snippet}

Provide technical analysis focusing on:
1. 🔧 **Implementation**: Specific configuration changes and their effects
2. 🛡️ **Security**: IAM, networking, encryption implications
3. 📊 **Performance**: Capacity, scaling, resource impacts
4. 🔄 **Deployment**: Order of operations and timing

Output: Technical deep-dive (15-20 lines), focus on specific risks.
"""
        
        return self._call_bedrock(prompt, 1500)
    
    def _synthesize_analysis(self, context_analysis: str, technical_analysis: str,
                           blast_radius: BlastRadiusAssessment) -> str:
        """Third pass: Synthesis and recommendations"""
        
        prompt = f"""
Role: Synthesize findings into actionable recommendations.

Context Analysis Summary:
{self._truncate_text(context_analysis, 30000)}

Technical Analysis Summary:
{self._truncate_text(technical_analysis, 30000)}

Risk Level: {blast_radius.criticality_level.value.upper()}
Affected Services: {', '.join(blast_radius.affected_services)}

Provide synthesis focusing on:
1. 📋 **Executive Summary**: Key findings in 2-3 bullets
2. 🎯 **Pre-deployment**: Required actions before applying
3. 🔍 **Monitoring**: What to watch during/after deployment
4. 🚨 **Rollback Strategy**: Recovery plan if things fail

Output: Actionable recommendations (15-20 lines), specific next steps.
"""
        
        return self._call_bedrock(prompt, 1500)
    
    def _call_bedrock(self, prompt: str, max_tokens: int) -> str:
        """Call AWS Bedrock with the given prompt"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            }
            
            target_model_id = (
                self.bedrock_inference_profile_arn or 
                self.bedrock_inference_profile_id or 
                self.bedrock_model_id
            )
            
            response = self.bedrock.invoke_model(modelId=target_model_id, body=json.dumps(body))
            result = json.loads(response['body'].read())
            return result['content'][0]['text']
        except Exception as e:
            return f"❌ AI analysis failed: {str(e)}"
    
    def _format_final_output(self, context_analysis: str, technical_analysis: str,
                           synthesis: str, blast_radius: BlastRadiusAssessment) -> str:
        """Format the comprehensive analysis output"""
        
        risk_emoji = {
            CriticalityLevel.CRITICAL: "🚨",
            CriticalityLevel.HIGH: "⚠️",
            CriticalityLevel.MEDIUM: "📋",
            CriticalityLevel.LOW: "✅"
        }.get(blast_radius.criticality_level, "📋")
        
        services = ', '.join(blast_radius.affected_services) if blast_radius.affected_services else 'None'
        
        return f"""
{risk_emoji} **RISK: {blast_radius.criticality_level.value.upper()}** | 🎯 **SERVICES: {services}** | ⏱️ **DOWNTIME: {blast_radius.estimated_downtime or 'None'}**

=== 🎯 BLAST RADIUS & IMPACT ASSESSMENT ===
{context_analysis.strip()}

=== 🔧 TECHNICAL ANALYSIS ===
{technical_analysis.strip()}

=== 📋 RECOMMENDATIONS & NEXT STEPS ===
{synthesis.strip()}
"""
    
    def print_analysis(self, analysis_result):
        """Print analysis result for Atlantis to capture"""
        # Clean up any ANSI escape sequences
        ansi_escape = re.compile(r"\x1B\[[0-9;]*[A-Za-z]")
        cleaned = ansi_escape.sub('', analysis_result)
        
        print("```", flush=True)  # Close any previous code block
        print("\n" + "="*80, flush=True)
        print("🤖 AI TERRAFORM PLAN ANALYSIS", flush=True)
        print("="*80, flush=True)
        print(f"Repository: {self.repo_owner}/{self.repo_name}", flush=True)
        print(f"PR: #{self.pr_number} | Workspace: {self.workspace} | Project: {self.project_name}", flush=True)
        print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", flush=True)
        print("-"*80, flush=True)
        print(cleaned, flush=True)
        print("="*80, flush=True)


def main():
    print("🚀 Starting Advanced Terraform Plan Analysis...", flush=True)
    analyzer = TerraformPlanAnalyzer()
    
    # Get plan file
    plan_file = None
    if len(sys.argv) > 1:
        plan_file = sys.argv[1]
    elif os.environ.get('PLANFILE'):
        plan_file = os.environ.get('PLANFILE')
    
    if not plan_file or not os.path.exists(plan_file):
        print("❌ Plan file not found. Usage: python3 bedrock_analyzer.py <plan_file>", flush=True)
        sys.exit(1)
    
    print(f"📂 Processing plan file: {plan_file}", flush=True)
    
    # Convert plan formats
    text_plan = analyzer.convert_plan_to_text(plan_file)
    if not text_plan:
        print("❌ Failed to convert plan to text", flush=True)
        sys.exit(1)
    
    json_plan = analyzer.convert_plan_to_json(plan_file)
    code_diff = analyzer.get_git_diff(plan_file)
    tf_config = analyzer.collect_terraform_config(plan_file)
    
    print("🔍 Running advanced multi-pass AI analysis...", flush=True)
    analysis = analyzer.analyze_terraform_plan(text_plan, plan_file, code_diff, tf_config, json_plan)
    
    analyzer.print_analysis(analysis)
    print("\n✅ Analysis completed", flush=True)

if __name__ == "__main__":
    main()