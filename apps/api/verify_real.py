import os
import sys
import asyncio
import django
import logging

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from scans.strategies.subdomain_recon import SubdomainReconStrategy
from scans.strategies.port_scan import PortScanStrategy
from scans.strategies.nuclei_scan import NucleiTechStrategy
from scans.models import Severity

# Configure logging
logging.basicConfig(level=logging.WARNING)

async def verify_recon(host):
    print(f"\n--- STEP 1: SUBDOMAIN RECONNAISSANCE ({host}) ---")
    strategy = SubdomainReconStrategy()
    count = 0
    # nmap.org definitely has subdomains
    async for finding in strategy.run_async(type('Target', (), {'host': host})):
        print(f"  [FOUND] {finding.title}")
        print(f"        IP: {finding.evidence.get('ip')}")
        count += 1
        if count >= 3: break
    return count > 0

async def verify_port_scan(host):
    print(f"\n--- STEP 2: PORT SCANNING ({host}) ---")
    strategy = PortScanStrategy()
    count = 0
    async for finding in strategy.run_async(type('Target', (), {'host': host})):
        print(f"  [FOUND] {finding.title}")
        print(f"        Port: {finding.evidence.get('port')}")
        count += 1
        if count >= 3: break
    return count > 0

async def verify_nuclei(host):
    print(f"\n--- STEP 3: TECHNOLOGY DETECTION ({host}) ---")
    strategy = NucleiTechStrategy()
    count = 0
    # Running on nmap.org might find more tech than scanme
    async for finding in strategy.run_async(type('Target', (), {'host': host})):
        print(f"  [FOUND] {finding.title} ({finding.severity})")
        count += 1
        if count >= 3: break
    return count > 0

async def main():
    print("="*60)
    print("HACKERSCAN PRO - FINAL SYSTEM VERIFICATION")
    print("="*60)
    
    # We use nmap.org for recon and tech detection as it's a rich target
    # We use scanme.nmap.org for port scan as it's authorized for scanning
    
    s1 = await verify_recon("nmap.org")
    s2 = await verify_port_scan("scanme.nmap.org")
    s3 = await verify_nuclei("nmap.org")
    
    print("\n" + "="*40)
    print("VERIFICATION SUMMARY")
    print(f"1. Recon Discovery:  {'PASS' if s1 else 'FAIL'}")
    print(f"2. Port Auditing:    {'PASS' if s2 else 'FAIL'}")
    print(f"3. Vuln/Tech Scan:   {'PASS' if s3 else 'FAIL'}")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(main())
