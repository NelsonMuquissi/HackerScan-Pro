#!/usr/bin/env python3
"""
HackerScan Pro - CI/CD Integration Script
This script can be run inside GitHub Actions, GitLab CI, or Bitbucket Pipelines.
It initiates a fast scan against a deployed environment or staging URL and fails the pipeline
if any High or Critical vulnerabilities are found.

Usage:
  python hackerscan-ci.py --target-url https://staging.myapp.com --api-key $HACKERSCAN_API_KEY
"""
import os
import sys
import time
import argparse
import requests

API_BASE_URL = os.environ.get("HACKERSCAN_API_URL", "https://api.hackerscan.com/v1")

def parse_args():
    parser = argparse.ArgumentParser(description="HackerScan Pro CI/CD Integration")
    parser.add_argument("--target-url", required=True, help="Target URL to scan (e.g., https://staging.example.com)")
    parser.add_argument("--api-key", required=True, help="HackerScan Pro API Key")
    parser.add_argument("--workspace-id", required=False, help="Workspace ID (optional if API key is bound to one)")
    parser.add_argument("--fail-on", default="high,critical", help="Comma-separated severities that fail the build")
    parser.add_argument("--scan-type", default="quick", help="Type of scan to run (quick, vuln, full)")
    parser.add_argument("--timeout", type=int, default=1800, help="Max wait time in seconds (default: 30m)")
    return parser.parse_args()

def main():
    args = parse_args()
    headers = {
        "Authorization": f"Bearer {args.api_key}",
        "Content-Type": "application/json"
    }

    print(f"🚀 Starting HackerScan Pro CI/CD integration for {args.target_url}")

    # 1. Create or Find Target
    target_data = {
        "name": f"CI/CD Target: {args.target_url}",
        "host": args.target_url,
        "target_type": "url",
        "description": "Auto-generated target from CI/CD pipeline",
        "tags": ["cicd", "automated"]
    }
    
    if args.workspace_id:
        target_data["workspace_id"] = args.workspace_id

    print("📌 Provisioning target environment in HackerScan...")
    target_resp = requests.post(f"{API_BASE_URL}/scans/targets/", json=target_data, headers=headers)
    
    if target_resp.status_code not in [200, 201]:
        print(f"❌ Failed to create target: {target_resp.text}")
        sys.exit(1)
        
    target_id = target_resp.json()["id"]
    print(f"✅ Target ready. ID: {target_id}")

    # 2. Trigger the Scan
    scan_payload = {
        "target_id": target_id,
        "scan_type": args.scan_type,
        "config": {
            "source": "ci_cd_pipeline"
        }
    }
    
    if args.workspace_id:
        scan_payload["workspace_id"] = args.workspace_id

    print(f"🔫 Triggering '{args.scan_type}' scan...")
    scan_resp = requests.post(f"{API_BASE_URL}/scans/", json=scan_payload, headers=headers)
    
    if scan_resp.status_code not in [200, 201]:
        print(f"❌ Failed to start scan: {scan_resp.text}")
        sys.exit(1)
        
    scan_id = scan_resp.json()["id"]
    print(f"✅ Scan initiated. ID: {scan_id}")

    # 3. Poll for Completion
    print("⏳ Waiting for scan to complete...")
    start_time = time.time()
    
    while True:
        if time.time() - start_time > args.timeout:
            print(f"⏱️ Scan timed out after {args.timeout} seconds.")
            sys.exit(1)
            
        status_resp = requests.get(f"{API_BASE_URL}/scans/{scan_id}/", headers=headers)
        if status_resp.status_code != 200:
            print(f"⚠️ Error checking status: {status_resp.status_code} - {status_resp.text}")
            time.sleep(10)
            continue
            
        status_data = status_resp.json()
        status = status_data.get("status")
        
        if status == "completed":
            print(f"\n🎉 Scan completed successfully in {int(time.time() - start_time)} seconds.")
            break
        elif status in ["failed", "error", "cancelled"]:
            print(f"\n❌ Scan ended with status: {status}")
            sys.exit(1)
            
        print(".", end="", flush=True)
        time.sleep(15)

    # 4. Fetch Findings and Evaluate Pipeline Status
    print("📊 Fetching security findings...")
    findings_resp = requests.get(f"{API_BASE_URL}/scans/{scan_id}/findings/", headers=headers)
    if findings_resp.status_code != 200:
        print(f"❌ Failed to fetch findings: {findings_resp.text}")
        sys.exit(1)
        
    findings = findings_resp.json()
    if isinstance(findings, dict) and "results" in findings:
        findings = findings["results"]
        
    fail_on_severities = [s.strip().lower() for s in args.fail_on.split(",")]
    
    issues_found = False
    print("\n--- HackerScan Pro Security Report ---")
    
    for f in findings:
        sev = f.get("severity", "info").lower()
        title = f.get("title", "Unknown")
        print(f"[{sev.upper()}] {title}")
        
        if sev in fail_on_severities:
            issues_found = True
            
    print("--------------------------------------")
            
    if issues_found:
        print("\n🚨 CI/CD Pipeline FAILED due to detection of blocking security vulnerabilities!")
        print("Please review the full report in the HackerScan Pro dashboard.")
        sys.exit(1)
    else:
        print("\n✅ Security gates passed. No blocking vulnerabilities detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()
