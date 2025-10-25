"""
Chronos Automated Remediation Agent 🛠️
A self-correcting system designed to automatically detect and fix common deployment issues,
primarily focusing on updating outdated container images in Kubernetes deployments.
"""

import os
import json
import subprocess
from typing import Dict, Any, Optional

# Conditional import for external dependencies
# It's best practice to handle large dependencies like 'kubernetes' only where they are needed
# or to clearly indicate that they are optional/must be installed.
try:
    from kubernetes import client, config, watch
    KUBERNETES_INSTALLED = True
except ImportError:
    # This prevents the script from crashing if kubernetes is not installed,
    # and provides a clear error message only when the functionality is attempted.
    KUBERNETES_INSTALLED = False

# The 'crewai' and 'github' imports were removed from the class-level/top-level imports
# as they aren't used in the provided methods (only the Agent class is used, which is mocked/assumed here).
# Assuming Agent, Task, Crew, LLM are available in the execution environment.
from crewai import Agent, Task, Crew, LLM

# --- Configuration Constants ---
# Use an environment variable for the kubeconfig path for better portability.
KUBECONFIG_PATH = os.getenv('KUBECONFIG_PATH', r"D:\Chronos\chronos-devops\kubeconfig.yaml")
LLM_BASE_URL = "http://localhost:11434"
LLM_MODEL = "ollama/llama3.2"
# -------------------------------

class AutoRemediationAgent:
    """
    Manages the lifecycle of automated deployment fixes, from analysis to execution and verification.
    """

    def __init__(self, github_token: Optional[str] = None):
        """Initializes the agent with necessary configurations."""
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        
        if not KUBERNETES_INSTALLED:
            print("⚠️ WARNING: Python 'kubernetes' client is not installed. Deployment update functionality is disabled.")

        # --- AI Agent Setup ---
        try:
            self.llm = LLM(
                model=LLM_MODEL,
                base_url=LLM_BASE_URL
            )
            
            self.fixer_agent = Agent(
                role='Automated Remediation Specialist',
                goal='Fix deployment issues by safely updating container configurations.',
                backstory='A highly specialized expert in Kubernetes, Docker, and CI/CD automation, focused on immediate, non-disruptive fixes.',
                llm=self.llm,
                verbose=False
            )
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize LLM/CrewAI Agents. Check your CrewAI/LLM setup. Error: {e}")
            self.fixer_agent = None

    def fix_deployment(self, deployment_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Main entry point to automatically fix a deployment issue.
        ... (rest of the method remains the same) ...
        """
        deployment_name = deployment_info.get('deployment')
        namespace = deployment_info.get('namespace')
        current_image = deployment_info.get('image')

        if not all([deployment_name, namespace, current_image]):
            return {
                'status': 'failed',
                'error': 'Missing required fields in deployment_info (deployment, namespace, or image).'
            }

        print("\n" + "="*80)
        print(f"🔧 Starting Remediation for Deployment: **{deployment_name}** in namespace **{namespace}**")
        print("="*80)

        # 1. Analyze the Issue (AI-driven)
        analysis_result = self._analyze_issue(deployment_info)
        print(f"📊 **Analysis:** {analysis_result}")
        print("-" * 80)

        # 2. Determine New Image Version
        new_image = self._get_latest_image(current_image)
        if new_image == current_image:
             print(f"⏭️ No newer image found or update logic skipped. Current image: {current_image}")
             return {
                 'status': 'skipped',
                 'deployment': deployment_name,
                 'message': 'No newer image determined for update.'
               }
        print(f"🆕 **Update Plan:** Changing image from **{current_image}** to **{new_image}**")
        print("-" * 80)

        # 3. Update Deployment
        # _update_deployment now contains the logic to find the container name
        update_result = self._update_deployment(deployment_name, namespace, new_image)
        
        # 4. Handle Result and Rollback if necessary
        if update_result['success']:
            print(f"✅ Successfully initiated update for **{deployment_name}**.")
            # Optional: Add a verification step here to wait for rollout completion
            # self._verify_rollout(deployment_name, namespace)
            return {
                'status': 'success',
                'deployment': deployment_name,
                'old_image': current_image,
                'new_image': new_image
            }
        else:
            print(f"❌ Failed to update **{deployment_name}**. Attempting rollback...")
            rollback_success = self.rollback_deployment(deployment_name, namespace)
            
            return {
                'status': 'failed',
                'deployment': deployment_name,
                'error': update_result['error'],
                'rollback_attempted': True,
                'rollback_success': rollback_success
            }

    def _analyze_issue(self, deployment_info: Dict[str, str]) -> str:
        """
        Uses the AI agent to analyze the deployment information and suggest a fix.
        ... (method remains the same) ...
        """
        if not self.fixer_agent:
            return "Local AI Agent not available, skipping detailed analysis."

        task = Task(
            description=f"""Analyze the following deployment issue and suggest a **precise, single-sentence fix action**.
            
            Deployment: {deployment_info.get('deployment')}
            Current Image: {deployment_info.get('image')}
            Severity: {deployment_info.get('severity', 'Unknown')}
            Reasoning: {deployment_info.get('reasoning', 'No reasoning provided')}

            Your output must be only the recommended action, e.g., 'Update nginx:1.21 to nginx:latest for security.'
            Be concise.""",
            agent=self.fixer_agent,
            expected_output="A brief, one-sentence analysis and recommended fix."
        )
        
        try:
            crew = Crew(agents=[self.fixer_agent], tasks=[task])
            result = crew.kickoff()
            return str(result).strip()
        except Exception as e:
            return f"AI Analysis failed. Reason: {e}"

    def _get_latest_image(self, current_image: str) -> str:
        """
        Determines the latest stable version of an image based on a set of heuristics.
        ... (method remains the same) ...
        """
        image_name = current_image.split(':')[0]
        
        # Heuristics for the placeholder:
        if 'nginx' in image_name.lower():
            return f"{image_name}:latest" # Forces upgrade to :latest
        elif 'klipper' in image_name.lower():
            # Example: Keep specific images as-is if they are tightly coupled to a system
            return current_image
        else:
            # Default to latest for other images if a tag exists
            return f"{image_name}:latest"

    # --- REMOVED: _get_container_name is no longer needed ---

    def _update_deployment(self, deployment_name: str, namespace: str, new_image: str) -> Dict[str, Any]:
        """
        Updates the Kubernetes Deployment or DaemonSet's container image using kubectl.
        
        Returns: {'success': bool, 'error': str or None}
        """
        if not KUBERNETES_INSTALLED:
            return {'success': False, 'error': "Kubernetes client not installed. Cannot update."}

        try:
            # Load config once (or ensure it's loaded)
            config.load_kube_config(config_file=KUBECONFIG_PATH)
            apps_v1 = client.AppsV1Api()
            
            container_name = None
            resource_type = None

            # 1. Try reading as a Deployment
            try:
                deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
                # Assumes the first container is the main one to update
                container_name = deployment.spec.template.spec.containers[0].name
                resource_type = "deployment"
            except client.ApiException as e:
                # If Deployment is not found (404), try DaemonSet
                if e.status != 404:
                    raise e # Re-raise if it's a different API error

                # 2. Try reading as a DaemonSet
                try:
                    daemonset = apps_v1.read_namespaced_daemon_set(deployment_name, namespace)
                    container_name = daemonset.spec.template.spec.containers[0].name
                    resource_type = "daemonset"
                except client.ApiException as e:
                    if e.status == 404:
                        return {'success': False, 'error': f"Resource '{deployment_name}' not found in namespace '{namespace}' as a Deployment or DaemonSet."}
                    raise e # Re-raise if it's a different API error

            # Final check before running kubectl
            if not container_name:
                 return {'success': False, 'error': 'Could not determine the container name for the resource.'}
                 
            print(f"🔍 Found {resource_type}: **{deployment_name}**, primary container: **{container_name}**")

            # Execute kubectl set image command
            cmd = [
                'kubectl', 'set', 'image',
                f'{resource_type}/{deployment_name}',
                f'{container_name}={new_image}',
                '-n', namespace,
                '--kubeconfig', KUBECONFIG_PATH
            ]
            
            print(f"🔨 Executing command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,  # Raise an exception for non-zero return codes
                timeout=45
            )
            
            print(f"✅ **kubectl output:** {result.stdout.strip()}")
            return {'success': True, 'error': None}

        except subprocess.CalledProcessError as e:
            error_msg = f"kubectl failed. Stderr: {e.stderr.strip()}"
            print(f"❌ **kubectl error:** {error_msg}")
            return {'success': False, 'error': error_msg}
            
        except subprocess.TimeoutExpired:
            error_msg = "kubectl command timed out."
            print(f"❌ **kubectl error:** {error_msg}")
            return {'success': False, 'error': error_msg}
            
        except Exception as e:
            # Catches API errors, configuration errors, and other unexpected exceptions
            error_msg = f"An unexpected error occurred during update: {e}"
            print(f"❌ **Update failed:** {error_msg}")
            return {'success': False, 'error': error_msg}

    def rollback_deployment(self, deployment_name: str, namespace: str) -> bool:
        """Rolls back a deployment to the previous revision if the update fails."""
        # Note: Rollout undo works for both Deployment and DaemonSet, so this method is fine.
        kubeconfig_path = KUBECONFIG_PATH
        
        cmd = [
            'kubectl', 'rollout', 'undo',
            f'deployment/{deployment_name}', # kubectl rollout undo assumes deployment unless specified
            '-n', namespace,
            '--kubeconfig', kubeconfig_path
        ]
        
        print(f"⏪ Executing rollback for: **{deployment_name}**")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            print(f"👍 Rollback successful: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Rollback failed. Stderr: {e.stderr.strip()}")
            return False
        except Exception as e:
            print(f"❌ Rollback failed with an unexpected error: {e}")
            return False

# --- Main Execution Block remains the same ---

def main():
    """Test the remediation agent"""
    
    # Define a realistic example deployment issue
    test_deployment = {
        'deployment': 'test-app-old',
        'namespace': 'default',
        'image': 'nginx:1.21', # Intentionally outdated version
        'severity': 'High',
        'recommended_action': 'Update',
        'reasoning': 'Outdated nginx version with known high-severity vulnerabilities (e.g., CVE-2021-3617).'
    }
    
    print("\n" + "#"*80)
    print("🤖 CHRONOS AUTO-REMEDIATION AGENT - DEMO RUN")
    print("#"*80)
    
    # Initialize the agent
    agent = AutoRemediationAgent()
    
    # Execute the fix
    result = agent.fix_deployment(test_deployment)
    if result.returncode == 0:
     print(f"✅ {result.stdout}")
     return True
    else:
     error_msg = result.stderr
     print(f"❌ kubectl error: {error_msg}")
     return False
    
    # Print the final result
    print("\n" + "="*80)
    print("📋 FINAL REMEDIATION RESULT:")
    print("="*80)
    print(json.dumps(result, indent=2))
    print("\n" + "#"*80)


if __name__ == "__main__":
    main()