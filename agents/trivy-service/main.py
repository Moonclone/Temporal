import subprocess
import json
import uvicorn
import psycopg2
from datetime import datetime
from fastapi import FastAPI, Body
from typing import Dict, List
from dataclasses import dataclass, asdict
import sys # Added for debug printing

# --- 1. Database Configuration and Logging ---

app = FastAPI()

DB_CONFIG = {
    "host": "postgres",
    "database": "chronos",
    "user": "chronos",
    "password": "chronos_password",
}

def log_vulnerability(image: str, vuln: Dict):
    """Inserts a single vulnerability into the PostgreSQL database."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # NOTE: Your original table structure:
        # id, image_name, vuln_id, pkg_name, severity, fixed_version, timestamp
        
        cur.execute("""
            INSERT INTO vulnerability_logs(image_name, vuln_id, pkg_name, severity, fixed_version, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            image,
            vuln['cve_id'],
            vuln['package'],
            vuln['severity'],
            vuln.get('fixed_version', 'N/A'),
            datetime.now(),
        ))
        conn.commit()
    except Exception as e:
        print(f"DATABASE ERROR: Failed to log vulnerability: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- 2. Vulnerability Scanner Classes (Modified to use logging) ---

@dataclass
class Vulnerability:
    """Represents a security vulnerability"""
    cve_id: str
    severity: str
    package: str
    installed_version: str
    fixed_version: str
    title: str

class VulnerabilityScanner:
    """Scans container images for security vulnerabilities using Trivy"""
    
    def __init__(self):
        # Assumes trivy is now installed inside the container and in PATH
        self.trivy_path = "trivy"  

    def scan_image(self, image: str) -> Dict:
        """Scan a container image for vulnerabilities and log results."""
        
        # Log command start to console
        print(f"\n🔍 Scanning image: {image}", file=sys.stderr) 

        try:
            cmd = [
                self.trivy_path,
                "image",
                "--format", "json",
                # Keep severity filter for performance, only log HIGH/CRITICAL
                "--severity", "HIGH,CRITICAL", 
                "--quiet",
                image
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300 # Increased timeout for pulling large images
            )

            if result.returncode != 0:
                print(f"❌ Trivy scan failed: {result.stderr}", file=sys.stderr)
                return {'status': 'error', 'image': image, 'error': result.stderr}

            scan_results = json.loads(result.stdout)
            
            # Parse vulnerabilities into objects
            vulnerabilities = self._parse_vulnerabilities(scan_results)

            # Log each HIGH/CRITICAL vulnerability to PostgreSQL
            for vuln in vulnerabilities:
                # Convert dataclass to dict for easier logging (and FastAPI return)
                log_vulnerability(image, asdict(vuln)) 

            summary = {
                'status': 'success',
                'image': image,
                'total_vulnerabilities': len(vulnerabilities),
                'critical': sum(1 for v in vulnerabilities if v.severity == 'CRITICAL'),
                'high': sum(1 for v in vulnerabilities if v.severity == 'HIGH'),
                'vulnerabilities': [asdict(v) for v in vulnerabilities] # Convert objects to dicts for JSON
            }
            
            self._print_summary(summary)
            return summary

        except subprocess.TimeoutExpired:
            print(f"⏱️ Scan timeout for {image}", file=sys.stderr)
            return {'status': 'timeout', 'image': image}
        except Exception as e:
            print(f"❌ Scan error: {e}", file=sys.stderr)
            # Print full traceback for deeper debugging
            import traceback
            traceback.print_exc(file=sys.stderr) 
            return {'status': 'error', 'image': image, 'error': str(e)}

    def _parse_vulnerabilities(self, scan_results: Dict) -> List[Vulnerability]:
        """Parse Trivy JSON output into Vulnerability objects"""
        # ... (Same logic as provided) ...
        vulnerabilities = []
        results = scan_results.get('Results', [])
        for result in results:
            vulns = result.get('Vulnerabilities', [])
            for vuln in vulns:
                # Only include HIGH/CRITICAL since Trivy was run with the filter
                if vuln.get('Severity') in ['HIGH', 'CRITICAL']: 
                    vulnerabilities.append(Vulnerability(
                        cve_id=vuln.get('VulnerabilityID', 'UNKNOWN'),
                        severity=vuln.get('Severity', 'UNKNOWN'),
                        package=vuln.get('PkgName', 'unknown'),
                        installed_version=vuln.get('InstalledVersion', 'unknown'),
                        fixed_version=vuln.get('FixedVersion', 'none'),
                        title=vuln.get('Title', 'No title')[:80]
                    ))
        return vulnerabilities

    def _print_summary(self, summary: Dict):
        """Print vulnerability scan summary to stderr for logging"""
        # ... (Same logic as provided, changed print to sys.stderr for better log capture) ...
        if summary['status'] != 'success':
            return
        total = summary['total_vulnerabilities']
        critical = summary['critical']
        high = summary['high']
        if total == 0:
            print(f"✅ No HIGH/CRITICAL vulnerabilities found!", file=sys.stderr)
            return
        print(f"⚠️  Found {total} HIGH/CRITICAL vulnerabilities:", file=sys.stderr)
        print(f"   🔴 CRITICAL: {critical}", file=sys.stderr)
        print(f"   🟠 HIGH: {high}", file=sys.stderr)

# NOTE: Removed the should_upgrade, get_recommendation, and main functions 
# as they are not needed for the API endpoint logic.

# --- 3. FastAPI Endpoint ---

# Initialize the scanner globally
scanner = VulnerabilityScanner()

@app.post("/scan")
async def scan_image_api(image: str = Body(..., embed=True)):
    """
    API endpoint to initiate a container image scan.
    
    Expects JSON body: {"image": "alpine:latest"}
    """
    # The scan_image method already handles the core logic, logging, and returns a dictionary.
    scan_result = scanner.scan_image(image)
    
    # Return the summary dict as the API response
    return scan_result

# --- 4. Uvicorn Server Startup ---

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)