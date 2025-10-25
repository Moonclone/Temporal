import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from datetime import datetime
from typing import List, Dict
from agents.monitor.pod_monitor import PodAgeMonitor
from agents.monitor.intelligent_monitor import IntelligentMonitor
from agents.remediation.auto_fixer import AutoRemediationAgent
from agents.security.vulnerability_scanner import VulnerabilityScanner


class ChronosOrchestrator:
    """Main orchestrator with vulnerability-aware remediation"""
    
    def __init__(self, age_threshold_days: int = 5, auto_fix: bool = False):
        self.age_threshold = age_threshold_days
        self.auto_fix = auto_fix
        
        # Initialize components
        self.pod_monitor = PodAgeMonitor(age_threshold_days=age_threshold_days)
        self.intelligent_monitor = IntelligentMonitor()
        self.remediation_agent = AutoRemediationAgent()
        self.vulnerability_scanner = VulnerabilityScanner()
        
        self.execution_log = []
    
    def run_full_cycle(self):
        """Execute complete detection → analysis → vulnerability scan → remediation cycle"""
        
        print("\n" + "="*80)
        print("🚀 CHRONOS AUTONOMOUS DEVOPS CYCLE WITH SECURITY SCANNING")
        print("="*80)
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Age Threshold: {self.age_threshold} days")
        print(f"🔧 Auto-Fix Mode: {'ENABLED' if self.auto_fix else 'DISABLED'}")
        print("="*80 + "\n")
        
        cycle_start = time.time()
        
        # PHASE 1: Detection
        print("📡 PHASE 1: DETECTION")
        print("-" * 80)
        aged_deployments = self.pod_monitor.scan_all_pods()
        
        if not aged_deployments:
            print("✅ No aged deployments found. System healthy!\n")
            return {
                'status': 'healthy',
                'aged_deployments': 0,
                'actions_taken': 0
            }
        
        print(f"🔍 Found {len(aged_deployments)} aged deployments\n")
        
        # PHASE 2: VULNERABILITY SCANNING
        print("🛡️  PHASE 2: SECURITY VULNERABILITY SCANNING")
        print("-" * 80)
        
        vulnerability_results = {}
        security_critical = []
        
        for deployment in aged_deployments:
            image = deployment.get('image', '')
            deployment_name = deployment.get('deployment', '')
            
            print(f"\n🔎 Scanning {deployment_name}...")
            scan_result = self.vulnerability_scanner.scan_image(image)
            vulnerability_results[deployment_name] = scan_result
            
            # Mark as security critical if needed
            if self.vulnerability_scanner.should_upgrade(scan_result):
                security_critical.append(deployment_name)
                deployment['security_critical'] = True
                deployment['vulnerability_scan'] = scan_result
                print(f"   🚨 SECURITY CRITICAL - needs immediate attention!")
            else:
                deployment['security_critical'] = False
                deployment['vulnerability_scan'] = scan_result
        
        print(f"\n🚨 Security Critical Deployments: {len(security_critical)}")
        if security_critical:
            for dep in security_critical:
                print(f"   • {dep}")
        
        # PHASE 3: AI Analysis (now with vulnerability context)
        print("\n🧠 PHASE 3: AI ANALYSIS (with security context)")
        print("-" * 80)
        
        recommendations = self._get_ai_recommendations_with_security(aged_deployments)
        
        if not recommendations:
            print("⚠️  AI analysis returned no recommendations\n")
            return {
                'status': 'error',
                'message': 'AI analysis failed'
            }
        
        # Prioritize security critical items
        actionable = [r for r in recommendations if r.get('recommended_action') == 'Update']
        
        # Sort by security criticality
        actionable.sort(key=lambda x: (
            not x.get('security_critical', False),  # Security critical first
            x.get('severity', 'Low')  # Then by severity
        ))
        
        print(f"✅ AI identified {len(actionable)} deployments requiring updates")
        if security_critical:
            security_actionable = [a for a in actionable if a.get('security_critical')]
            print(f"   🚨 {len(security_actionable)} are SECURITY CRITICAL\n")
        
        # PHASE 4: Remediation
        remediation_results = []
        
        if self.auto_fix and actionable:
            print("🔧 PHASE 4: AUTO-REMEDIATION (Security-Prioritized)")
            print("-" * 80)
            
            for item in actionable:
                deployment_name = item.get('deployment', '')
                is_security_critical = item.get('security_critical', False)
                
                print(f"\n🎯 Processing: {deployment_name}")
                print(f"   Severity: {item.get('severity', 'Unknown')}")
                print(f"   Security Critical: {'🚨 YES' if is_security_critical else 'No'}")
                
                vuln_scan = item.get('vulnerability_scan', {})
                if vuln_scan.get('status') == 'success':
                    print(f"   Vulnerabilities: {vuln_scan.get('critical', 0)} CRITICAL, {vuln_scan.get('high', 0)} HIGH")
                
                if self._should_auto_fix(item):
                    print(f"   🔧 Attempting remediation...")
                    result = self.remediation_agent.fix_deployment(item)

                    # Print detailed error if failed
                    if result['status'] == 'failed':
                        print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
                        if 'details' in result:
                          print(f"      Details: {result['details']}")

                    result['security_critical'] = is_security_critical
                    result['vulnerabilities_fixed'] = vuln_scan
                    remediation_results.append(result)
                    
                    if result['status'] == 'success':
                        print(f"   ✅ Successfully remediated!")
                        if is_security_critical:
                            print(f"   🛡️  Security vulnerabilities addressed!")
                    else:
                        print(f"   ❌ Remediation failed")
                else:
                    print(f"   ⏭️  Skipped (safety check)")
        else:
            print("\n⏭️  PHASE 4: REMEDIATION SKIPPED (auto-fix disabled)")
            print("-" * 80)
            print("💡 Enable auto-fix with: ChronosOrchestrator(auto_fix=True)\n")
        
        # PHASE 5: Summary Report
        cycle_time = time.time() - cycle_start
        
        print("\n" + "="*80)
        print("📊 CYCLE SUMMARY")
        print("="*80)
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'cycle_duration_seconds': round(cycle_time, 2),
            'aged_deployments_detected': len(aged_deployments),
            'security_scans_performed': len(vulnerability_results),
            'security_critical_deployments': len(security_critical),
            'ai_recommendations': len(recommendations),
            'actionable_items': len(actionable),
            'auto_fix_enabled': self.auto_fix,
            'remediations_attempted': len(remediation_results),
            'remediations_successful': sum(1 for r in remediation_results if r['status'] == 'success'),
            'remediations_failed': sum(1 for r in remediation_results if r['status'] == 'failed'),
            'security_issues_fixed': sum(1 for r in remediation_results if r.get('security_critical') and r['status'] == 'success'),
            'details': {
                'vulnerability_scans': vulnerability_results,
                'recommendations': recommendations,
                'remediation_results': remediation_results
            }
        }
        
        self._print_summary(summary)
        self.execution_log.append(summary)
        
        return summary
    
    def _get_ai_recommendations_with_security(self, aged_deployments: List[Dict]) -> List[Dict]:
     """Get AI recommendations enhanced with security context"""
     try:
        from crewai import Task, Crew
        
        # Prepare deployment data with security context
        deployments_summary = []
        for dep in aged_deployments:
            vuln = dep.get('vulnerability_scan', {})
            dep_summary = {
                'deployment': dep['deployment'],
                'namespace': dep['namespace'],
                'image': dep['image'],
                'age_days': dep['age_days'],
                'security_critical': dep.get('security_critical', False),
                'critical_cves': vuln.get('critical', 0),
                'high_cves': vuln.get('high', 0)
            }
            deployments_summary.append(dep_summary)
        
        task = Task(
            description=f"""Analyze deployments with security vulnerability data.

Deployments:
{json.dumps(deployments_summary, indent=2)}

CRITICAL: Include ALL fields in response: deployment, namespace, image, severity, recommended_action, reasoning, security_critical

Return ONLY valid JSON array:
[
  {{
    "deployment": "exact-deployment-name",
    "namespace": "exact-namespace",
    "image": "exact-image:tag",
    "severity": "Critical",
    "recommended_action": "Update",
    "reasoning": "X critical CVEs found",
    "security_critical": true
  }}
]""",
            agent=self.intelligent_monitor.agent,
            expected_output="Valid JSON array with ALL fields"
        )
        
        crew = Crew(
            agents=[self.intelligent_monitor.agent],
            tasks=[task],
            verbose=False
        )
        
        result = crew.kickoff()
        result_str = str(result).strip()
        
        # Clean and parse JSON
        if '```' in result_str:
            result_str = result_str.split('```')[1]
            if result_str.startswith('json'):
                result_str = result_str[4:]
        
        result_str = ''.join(char for char in result_str if ord(char) >= 32 or char == '\n')
        
        start = result_str.find('[')
        end = result_str.rfind(']') + 1
        
        if start != -1 and end > start:
            json_str = result_str[start:end]
            recommendations = json.loads(json_str)
            
            # CRITICAL FIX: Merge missing fields from original deployment data
            for rec in recommendations:
                for dep in aged_deployments:
                    if rec.get('deployment') == dep['deployment']:
                        # Ensure all required fields exist
                        rec['namespace'] = rec.get('namespace') or dep['namespace']
                        rec['image'] = rec.get('image') or dep['image']
                        rec['deployment'] = dep['deployment']  # Ensure exact match
                        rec['vulnerability_scan'] = dep.get('vulnerability_scan', {})
                        rec['security_critical'] = dep.get('security_critical', False)
                        break
            
            return recommendations
        else:
            print("⚠️  Could not find JSON array")
            return []
            
     except Exception as e:
        print(f"❌ AI analysis error: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    def _should_auto_fix(self, item: Dict) -> bool:
        """Determine if item should be auto-fixed (with security override)"""
        
        # ALWAYS auto-fix security critical items in user namespaces
        if item.get('security_critical') and item.get('namespace') == 'default':
            return True
        
        # Don't auto-fix critical system components
        critical_deployments = ['coredns', 'metrics-server', 'traefik', 'kube-']
        deployment_name = item.get('deployment', '').lower()
        
        for critical in critical_deployments:
            if critical in deployment_name:
                return False
        
        # Auto-fix High and Critical severity
        severity = item.get('severity', 'Low')
        if severity in ['High', 'Critical']:
            return True
        
        return False
    
    def _print_summary(self, summary: Dict):
        """Print enhanced summary with security metrics"""
        
        print(f"⏱️  Cycle Duration: {summary['cycle_duration_seconds']}s")
        print(f"🔍 Deployments Scanned: {summary['aged_deployments_detected']}")
        print(f"🛡️  Security Scans: {summary['security_scans_performed']}")
        print(f"🚨 Security Critical: {summary['security_critical_deployments']}")
        print(f"🤖 AI Recommendations: {summary['ai_recommendations']}")
        print(f"⚡ Actionable Items: {summary['actionable_items']}")
        
        if summary['auto_fix_enabled']:
            success = summary['remediations_successful']
            failed = summary['remediations_failed']
            total = summary['remediations_attempted']
            security_fixed = summary['security_issues_fixed']
            
            print(f"\n🔧 Remediation Results:")
            print(f"   ✅ Successful: {success}/{total}")
            print(f"   ❌ Failed: {failed}/{total}")
            print(f"   🛡️  Security Issues Fixed: {security_fixed}")
            
            if security_fixed > 0:
                print(f"\n🎉 {security_fixed} CRITICAL security issue(s) automatically resolved!")
        
        print("\n" + "="*80 + "\n")


def main():
    """Main entry point"""
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██████╗██╗  ██╗██████╗  ██████╗ ███╗   ██╗ ██████╗ ███████╗║
    ║  ██╔════╝██║  ██║██╔══██╗██╔═══██╗████╗  ██║██╔═══██╗██╔════╝║
    ║  ██║     ███████║██████╔╝██║   ██║██╔██╗ ██║██║   ██║███████╗║
    ║  ██║     ██╔══██║██╔══██╗██║   ██║██║╚██╗██║██║   ██║╚════██║║
    ║  ╚██████╗██║  ██║██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝███████║║
    ║   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝║
    ║                                                               ║
    ║        🛡️  SECURITY-AWARE AUTONOMOUS DEVOPS v0.2             ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    orchestrator = ChronosOrchestrator(
        age_threshold_days=0,
        auto_fix=True
    )
    
    result = orchestrator.run_full_cycle()


if __name__ == "__main__":
    main()