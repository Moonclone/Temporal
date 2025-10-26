import sys
import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

# --- Local Path Setup (Simplified relative import handling) ---
# NOTE: This is often replaced by proper package installation/setup
try:
    # Attempt to insert the project root into the path
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
except Exception:
    pass


# --- Project-Specific Imports ---
# Ensure these are only imported if they are guaranteed to exist,
# otherwise, they can lead to ImportError.
from agents.monitor.pod_monitor import PodAgeMonitor
from agents.monitor.intelligent_monitor import IntelligentMonitor
from agents.remediation.auto_fixer import AutoRemediationAgent
from agents.security.vulnerability_scanner import VulnerabilityScanner
from agents.temporal.code_archaeologist import CodeArchaeologist
from agents.temporal.debt_predictor import TechnicalDebtPredictor

# Third-party import used in a helper method
try:
    from crewai import Task, Crew
except ImportError:
    # Define placeholder for type hinting if not installed
    class Task: pass
    class Crew: pass


class ChronosOrchestrator:
    """
    Main orchestrator with predictive intelligence.

    Coordinates monitoring, security scanning, AI analysis, and
    optional auto-remediation, enhanced by temporal code predictions.
    """

    def __init__(self, age_threshold_days: int = 5, auto_fix: bool = False, enable_predictions: bool = False):
        """
        Initializes the Chronos Orchestrator.

        :param age_threshold_days: Max age for a pod before being flagged.
        :param auto_fix: Flag to enable or disable automatic remediation.
        :param enable_predictions: Flag to enable or disable temporal predictive analysis.
        """
        self.age_threshold = age_threshold_days
        self.auto_fix = auto_fix
        self.enable_predictions = enable_predictions

        # Initialize core components
        self.pod_monitor = PodAgeMonitor(age_threshold_days=age_threshold_days)
        self.intelligent_monitor = IntelligentMonitor()
        self.remediation_agent = AutoRemediationAgent()
        self.vulnerability_scanner = VulnerabilityScanner()

        # Temporal prediction components state
        self.archaeologist: Optional[CodeArchaeologist] = None
        self.predictor: Optional[TechnicalDebtPredictor] = None
        self.predictions: Optional[Dict[str, Any]] = None

        self.execution_log: List[Dict[str, Any]] = []

    def run_full_cycle(self) -> Dict[str, Any]:
        """
        Executes the complete autonomous DevOps cycle, including all phases.
        """
        print("\n" + "=" * 80)
        print("🚀 CHRONOS AUTONOMOUS DEVOPS CYCLE v0.3")
        print("   🔮 WITH PREDICTIVE INTELLIGENCE")
        print("=" * 80)
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Age Threshold: {self.age_threshold} days")
        print(f"🔧 Auto-Fix: {'ENABLED' if self.auto_fix else 'DISABLED'}")
        print(f"🔮 Predictions: {'ENABLED' if self.enable_predictions else 'DISABLED'}")
        print("=" * 80 + "\n")

        cycle_start = time.time()

        # PHASE 0: Temporal Predictions (if enabled)
        if self.enable_predictions:
            self.run_temporal_analysis()

        # PHASE 1: Detection
        print("📡 PHASE 1: INFRASTRUCTURE DETECTION")
        print("-" * 80)
        aged_deployments = self.pod_monitor.scan_all_pods()

        if not aged_deployments:
            print("✅ No aged deployments. System healthy!\n")
            return {'status': 'healthy', 'aged_deployments': 0}

        print(f"🔍 Found {len(aged_deployments)} aged deployments\n")

        # PHASE 2: Security Scanning
        print("🛡️ PHASE 2: SECURITY VULNERABILITY SCANNING")
        print("-" * 80)

        security_critical: List[str] = []
        for deployment in aged_deployments:
            image = deployment.get('image', '')
            deployment_name = deployment.get('deployment', '')

            print(f"\n🔎 Scanning {deployment_name}...")
            scan_result = self.vulnerability_scanner.scan_image(image)
            
            # Attach scan results and criticality flag to the deployment object
            deployment['vulnerability_scan'] = scan_result
            is_critical = self.vulnerability_scanner.should_upgrade(scan_result)
            deployment['security_critical'] = is_critical
            
            if is_critical:
                security_critical.append(deployment_name)

        print(f"\n🚨 Security Critical Deployments: {len(security_critical)}")

        # PHASE 3: AI Analysis with Predictions
        print("\n🧠 PHASE 3: AI ANALYSIS (Security + Predictions)")
        print("-" * 80)

        recommendations = self._get_ai_recommendations_with_context(aged_deployments)

        if not recommendations:
            print("⚠️ AI analysis failed\n")
            return {'status': 'error'}

        actionable = [r for r in recommendations if r.get('recommended_action') == 'Update']

        # Prioritize using predictions
        if self.predictions:
            actionable = self._prioritize_with_predictions(actionable)

        print(f"✅ {len(actionable)} deployments marked for update")

        # PHASE 4: Remediation
        remediation_results: List[Dict[str, Any]] = []

        if self.auto_fix and actionable:
            print("\n🔧 PHASE 4: AUTO-REMEDIATION")
            print("-" * 80)

            for item in actionable:
                deployment_name = item.get('deployment', '')

                print(f"\n🎯 {deployment_name}")
                print(f"   Severity: {item.get('severity')}")
                print(f"   Security: {'🚨 CRITICAL' if item.get('security_critical') else '✓'}")

                if item.get('predicted_issues'):
                    print(f"   🔮 Predicted: {item['predicted_issues']}")

                if self._should_auto_fix(item):
                    print("   🔧 Fixing...")
                    result = self.remediation_agent.fix_deployment(item)
                    remediation_results.append(result)

                    if result['status'] == 'success':
                        print("   ✅ Fixed!")
                    else:
                        print(f"   ❌ {result.get('error', 'Failed')}")
                else:
                    print("   ⏭️ Skipped (Auto-fix rules prevent action)")

        # Summary
        cycle_time = time.time() - cycle_start
        summary = self._generate_summary(cycle_time, aged_deployments, security_critical, remediation_results)

        self._print_summary(summary)
        
        return summary

    def run_temporal_analysis(self, repo_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Run predictive analysis on the codebase."""
        if not self.enable_predictions:
            return None

        print("\n" + "=" * 80)
        print("🔮 PHASE 0: TEMPORAL PREDICTION ANALYSIS")
        print("=" * 80)

        try:
            # Use project root directory if no repo specified
            if not repo_path:
                repo_path = _PROJECT_ROOT

            print(f"📂 Analyzing repository: {repo_path}")

            # Run code archaeology
            self.archaeologist = CodeArchaeologist(repo_path)
            self.archaeologist.clone_or_open_repo()
            self.archaeologist.analyze_history(months_back=6, max_commits=100)
            hotspots = self.archaeologist.identify_hotspots(top_n=5)
            decay = self.archaeologist.detect_decay_patterns()
            self.archaeologist.export_data()

            # Run predictions
            self.predictor = TechnicalDebtPredictor()
            self.predictor.load_analysis()
            complexity_pred = self.predictor.predict_complexity_growth(months_ahead=6)
            bug_pred = self.predictor.predict_bug_probability()

            self.predictions = {
                'hotspots': hotspots,
                'decay_patterns': decay,
                'complexity_predictions': complexity_pred,
                'bug_predictions': bug_pred
            }

            print("\n✅ Temporal analysis complete!")
            print(f"   🔥 Hotspots: {len(hotspots)}")
            print(f"   📉 Files with decay: {decay['summary']['files_with_decay']}")
            print(f"   🔮 Future complexity risks: {len(complexity_pred)}")
            # Filter for bug probability > 60 for better console output
            high_bug_risk_files = [p for p in bug_pred if p.get('bug_probability', 0) > 60]
            print(f"   🐛 High bug risk files: {len(high_bug_risk_files)}\n")

            return self.predictions

        except Exception as e:
            print(f"⚠️ Temporal analysis failed: {e}")
            return None

    # --------------------------------------------------------------------------
    # Private / Helper Methods
    # --------------------------------------------------------------------------

    def _get_ai_recommendations_with_context(self, deployments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Uses the IntelligentMonitor (CrewAI) to get actionable recommendations.
        """
        
        # CrewAI must be installed for this to work
        if 'Crew' not in globals():
             print("⚠️ CrewAI not imported. Skipping AI recommendations.")
             return []

        # Prepare context for the AI agent
        context_data = [
            {
                'deployment': d['deployment'], 
                'namespace': d['namespace'], 
                'image': d['image'], 
                'security_critical': d.get('security_critical', False)
            } for d in deployments
        ]

        task = Task(
            description=f"""Analyze deployments and provide recommendations.

Deployments:
{json.dumps(context_data, indent=2)}

CRITICAL RULES:
- If security_critical=true: severity="Critical", recommended_action="Update"
- If namespace="default": recommended_action="Update"
- recommended_action must be EXACTLY "Update" or "Monitor" (one word only!)

Return ONLY this JSON array format:
[
  {{
    "deployment": "exact-name",
    "namespace": "exact-namespace",
    "image": "exact-image",
    "severity": "High",
    "recommended_action": "Update",
    "reasoning": "brief reason"
  }}
]""",
            agent=self.intelligent_monitor.agent,
            expected_output="JSON array"
        )

        crew = Crew(agents=[self.intelligent_monitor.agent], tasks=[task], verbose=False)
        
        try:
            result = str(crew.kickoff())
        except Exception as e:
            print(f"⚠️ CrewAI kickoff failed: {e}")
            return []

        # Clean and parse JSON response
        if '```' in result:
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:].strip()
        
        # Remove non-ASCII characters that can break JSON parsing
        result = ''.join(char for char in result if ord(char) >= 32 or char == '\n').strip()
        
        # Attempt to find and load the JSON array
        start = result.find('[')
        end = result.rfind(']') + 1
        recommendations: List[Dict[str, Any]] = []

        if start != -1 and end > start:
            try:
                recommendations = json.loads(result[start:end])
            except json.JSONDecodeError as e:
                print(f"⚠️ Failed to parse AI JSON response: {e}")
                print(f"Raw Response: {result[start:end][:200]}...") # Print snippet for debugging
                return []
        
        # Merge data and enforce hard rules (safety check)
        for rec in recommendations:
            for dep in deployments:
                if rec.get('deployment') == dep['deployment']:
                    rec['security_critical'] = dep.get('security_critical', False)
                    rec['age_days'] = dep.get('age_days', 0) # Add age context

                    # FORCE correct recommended_action based on hard rules
                    if rec.get('security_critical') or dep.get('namespace') == 'default':
                        rec['recommended_action'] = 'Update'
                        rec['severity'] = rec.get('severity', 'Critical') if rec.get('security_critical') else 'High'

                    # Ensure essential fields are present
                    rec['namespace'] = rec.get('namespace') or dep['namespace']
                    rec['image'] = rec.get('image') or dep['image']
                    break
        
        return recommendations

    def _prioritize_with_predictions(self, actionable: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance prioritization of actionable items using predictions."""
        if not self.predictions:
            return actionable

        bug_predictions = {p['filename']: p for p in self.predictions.get('bug_predictions', [])}

        for item in actionable:
            deployment = item.get('deployment', '')
            
            # Check if deployment name matches predicted risky files
            matching_predictions = [p for f, p in bug_predictions.items() if deployment in f]
            
            if matching_predictions:
                max_bug_prob = max(p.get('bug_probability', 0) for p in matching_predictions)
                item['predicted_bug_probability'] = max_bug_prob
                item['predicted_issues'] = f"{max_bug_prob:.0f}% bug risk predicted"
                
                # Boost severity if prediction is high
                if max_bug_prob > 70 and item.get('severity') not in ['Critical', 'High']:
                    item['severity'] = 'High'

        # Sort: security critical (True comes before False) + predictions (higher probability first)
        severity_order = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
        
        actionable.sort(key=lambda x: (
            not x.get('security_critical', False),  # Primary: Critical first
            -x.get('predicted_bug_probability', 0), # Secondary: Higher predicted risk first
            -severity_order.get(x.get('severity', 'Low'), 0) # Tertiary: High severity first
        ))
        
        return actionable

    def _should_auto_fix(self, item: Dict[str, Any]) -> bool:
        """Determine if a deployment should be automatically remediated."""
        # Check if auto-fix is globally enabled
        if not self.auto_fix:
            return False
            
        # Hard rule 1: Auto-fix if security critical AND in default namespace
        if item.get('security_critical') and item.get('namespace') == 'default':
            return True

        # Hard rule 2: NEVER auto-fix critical infrastructure components
        critical_deployments = ['coredns', 'metrics-server', 'traefik', 'kube-']
        deployment_name = item.get('deployment', '').lower()
        
        for critical in critical_deployments:
            if critical in deployment_name:
                return False
        
        # Rule 3: Auto-fix if severity is High or Critical
        severity = item.get('severity', 'Low')
        return severity in ['High', 'Critical']
    
    def _generate_summary(self, cycle_time: float, aged_deployments: List[Dict[str, Any]], security_critical: List[str], remediation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates the final summary dictionary."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'cycle_duration': round(cycle_time, 2),
            'aged_deployments': len(aged_deployments),
            'security_critical': len(security_critical),
            'predictions_enabled': self.enable_predictions,
            'remediations_attempted': len(remediation_results),
            'remediations_successful': sum(1 for r in remediation_results if r['status'] == 'success'),
        }

        if self.predictions:
            bug_pred = self.predictions.get('bug_predictions', [])
            summary['prediction_summary'] = {
                'future_complexity_risks': len(self.predictions.get('complexity_predictions', [])),
                'high_bug_risk_files': len([p for p in bug_pred if p.get('bug_probability', 0) > 60])
            }

        return summary

    def _print_summary(self, summary: Dict[str, Any]) -> None:
        """Prints the final summary in a clean format."""
        print("\n" + "=" * 80)
        print("📊 CYCLE SUMMARY")
        print("=" * 80)
        print(f"⏱️  Duration: {summary['cycle_duration']}s")
        print(f"🔍 Aged Deployments Found: {summary['aged_deployments']}")
        print(f"🚨 Security Critical: {summary['security_critical']}")

        if summary.get('predictions_enabled'):
            pred = summary.get('prediction_summary', {})
            print("\n🔮 PREDICTIONS:")
            print(f"   Future Complexity Risks: {pred.get('future_complexity_risks', 0)}")
            print(f"   High Bug Risk Files: {pred.get('high_bug_risk_files', 0)}")

        attempted = summary['remediations_attempted']
        successful = summary['remediations_successful']
        print(f"\n🔧 Remediations: {successful}/{attempted} successful")
        print("=" * 80 + "\n")


def main():
    """Entry point for the Chronos Orchestrator application."""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   ██████╗██╗  ██╗██████╗  ██████╗ ███╗   ██╗ ██████╗ ███████╗║
    ║  ██╔════╝██║  ██║██╔══██╗██╔═══██╗████╗  ██║██╔═══██╗██╔════╝║
    ║  ██║     ███████║██████╔╝██║   ██║██╔██╗ ██║██║   ██║███████╗║
    ║  ██║     ██╔══██║██╔══██╗██║   ██║██║╚██╗██║██║   ██║╚════██║║
    ║  ╚██████╗██║  ██║██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝███████║║
    ║   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝║
    ║                                                              ║
    ║         🔮 PREDICTIVE AUTONOMOUS DEVOPS v0.3                 ║
    ║                                                              ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    orchestrator = ChronosOrchestrator(
        age_threshold_days=0,
        auto_fix=True,
        enable_predictions=True  # ENABLE PREDICTIONS!
    )
    
    orchestrator.run_full_cycle()


if __name__ == "__main__":
    main()