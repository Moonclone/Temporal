from kubernetes import client, config
from datetime import datetime, timezone
from typing import List, Dict
import os # Kept, although not strictly used in the final logic

class PodAgeMonitor:
    """Monitors Kubernetes pods and detects aged deployments"""
    
    def __init__(self, age_threshold_days: int = 5):
        self.age_threshold_days = age_threshold_days
        # Initialize clients to None before setup
        self.v1 = None
        self.apps_v1 = None
        self.setup_k8s_client()
    
    def setup_k8s_client(self):
        """Initializes the Kubernetes API clients by loading kubeconfig."""
        try:
            # Load Kubernetes configuration (handles both in-cluster and kubeconfig)
            # NOTE: config.load_kube_config() raises an exception if config is not found,
            # which is correctly caught below.
            kubeconfig = r"D:\Chronos\chronos-devops\kubeconfig.yaml"
            config.load_kube_config(config_file=kubeconfig)
            print("Using local kubeconfig")
            
            # Initialize clients ONLY ONCE after successful config load
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            
        except config.ConfigException:
            # Fallback for in-cluster configuration if kubeconfig fails
            try:
                config.load_incluster_config()
                print("Using in-cluster config")
                self.v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
            except Exception as e:
                print(f"Failed to setup K8s client: Could not load kubeconfig or in-cluster config: {e}")
                raise
        except Exception as e:
            print(f"Failed to setup K8s client: {e}")
            raise
        
        # REMOVED: Redundant and potentially erroneous re-initialization outside the try/except:
        # self.v1 = client.CoreV1Api()
        # self.apps_v1 = client.AppsV1Api()
        
    def scan_all_pods(self) -> List[Dict]:
        """Scan all pods across all namespaces"""
        if not self.v1:
            print("❌ K8s client not initialized. Cannot scan pods.")
            return []
            
        print(f"\n🔍 Scanning pods (threshold: {self.age_threshold_days} days)...")
        
        aged_deployments = []
        
        try:
            # Get all pods
            pods = self.v1.list_pod_for_all_namespaces(watch=False)
            
            for pod in pods.items:
                # Exclude pods that are not running or completed (e.g., pending, failed)
                # We typically only care about running pods for 'age' monitoring
                if pod.status.phase not in ["Running", "Succeeded"]: 
                    continue
                    
                age_days = self._calculate_pod_age(pod)
                
                if age_days >= self.age_threshold_days:
                    deployment_info = self._extract_deployment_info(pod)
                    
                    # Ensure we have a deployment name to report
                    if deployment_info and deployment_info['deployment']: 
                        aged_deployments.append({
                            'pod_name': pod.metadata.name,
                            'namespace': pod.metadata.namespace,
                            'age_days': age_days,
                            'status': pod.status.phase,
                            'deployment': deployment_info['deployment'],
                            # Check if containers list is valid before accessing [0]
                            'image': pod.spec.containers[0].image if pod.spec.containers else 'N/A', 
                            'labels': pod.metadata.labels or {}
                        })
            
            print(f"Found {len(aged_deployments)} aged deployments")
            
        except Exception as e:
            print(f"Error scanning pods: {e}")
            return []
        
        return aged_deployments
    
    def _calculate_pod_age(self, pod) -> float:
        """Calculate pod age in days"""
        if not pod.status.start_time:
            return 0
        
        start_time = pod.status.start_time
        
        # Kubernetes client already returns timezone-aware datetime objects,
        # so explicit replacement/checking for tzinfo is usually redundant
        # but kept for robustness. Ensure comparison uses the same timezone.
        
        now = datetime.now(timezone.utc)
        
        # Convert start_time to UTC if it's not (though the client should handle this)
        if start_time.tzinfo is None:
             start_time = start_time.replace(tzinfo=timezone.utc)
        else:
             start_time = start_time.astimezone(timezone.utc)
             
        age = now - start_time
        
        # Using total_seconds is cleaner than manual calculation
        return age.total_seconds() / 86400  # Convert total seconds to decimal days
    
    def _extract_deployment_info(self, pod) -> Dict:
        """Extract deployment name and image from pod"""
        # NOTE: Image extraction is now done directly in scan_all_pods for simplicity/error handling
        
        try:
            deployment_name = None
            
            # Look for ReplicaSet owner
            if pod.metadata.owner_references:
                for owner in pod.metadata.owner_references:
                    if owner.kind == "ReplicaSet":
                        # Get deployment from ReplicaSet
                        deployment_name = self._get_deployment_from_replicaset(
                            owner.name, 
                            pod.metadata.namespace
                        )
                        break
            
            # If still None, use the pod name as a fallback for objects not managed by a Deployment
            return {
                'deployment': deployment_name or pod.metadata.name, 
            }
        
        except Exception as e:
            # Reduced the output message for a cleaner log
            # print(f"⚠️ Could not extract deployment info: {e}")
            return None
    
    def _get_deployment_from_replicaset(self, replicaset_name: str, namespace: str) -> str:
        """Get deployment name from ReplicaSet"""
        # Ensure client is initialized
        if not self.apps_v1:
            return None
            
        try:
            rs = self.apps_v1.read_namespaced_replica_set(replicaset_name, namespace)
            if rs.metadata.owner_references:
                for owner in rs.metadata.owner_references:
                    if owner.kind == "Deployment":
                        return owner.name
        except client.ApiException as e:
            # print(f"Could not find ReplicaSet {replicaset_name} in {namespace}: {e}")
            pass # Suppress specific K8s API errors like "not found"
            
        return None
    
    # Kept get_deployment_details and print_report as they are mostly fine,
    # though print_report now relies on the revised scan_all_pods output
    
    def get_deployment_details(self, deployment_name: str, namespace: str) -> Dict:
        """Get detailed information about a deployment"""
        if not self.apps_v1:
            print("K8s client not initialized. Cannot get deployment details.")
            return None
            
        try:
            deployment = self.apps_v1.read_namespaced_deployment(deployment_name, namespace)
            
            return {
                'name': deployment_name,
                'namespace': namespace,
                'replicas': deployment.spec.replicas,
                'available_replicas': deployment.status.available_replicas or 0,
                'image': deployment.spec.template.spec.containers[0].image,
                'labels': deployment.metadata.labels or {},
                'annotations': deployment.metadata.annotations or {}
            }
        
        except Exception as e:
            print(f"Could not get deployment details: {e}")
            return None
    
    def print_report(self, aged_deployments: List[Dict]):
        """Print a nice report of aged deployments"""
        if not aged_deployments:
            print("\n No aged deployments found. All systems fresh! ✨")
            return
        
        print("\n" + "="*80)
        print(f" AGED DEPLOYMENTS REPORT")
        print("="*80)
        
        for idx, dep in enumerate(aged_deployments, 1):
            print(f"\n[{idx}] {dep['deployment']}")
            print(f"      Namespace: {dep['namespace']}")
            print(f"      Pod: {dep['pod_name']}") # Added pod name for clarity in report
            print(f"      Age: {dep['age_days']:.1f} days")
            print(f"      Image: {dep['image']}")
            print(f"      Status: {dep['status']}")
        
        print("\n" + "="*80)
        print(f"Total: {len(aged_deployments)} deployments need attention ⚠️")
        print("="*80 + "\n")


if __name__ == "__main__":
    # Test the monitor
    try:
        monitor = PodAgeMonitor(age_threshold_days=5)
        aged_deps = monitor.scan_all_pods()
        monitor.print_report(aged_deps)
    except Exception as e:
        print(f"\nScript terminated due to critical error: {e}")