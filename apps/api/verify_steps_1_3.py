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

async def verify_step_1():
    host = "nmap.org"
    print(f"\n--- STEP 1: SUBDOMAIN RECONNAISSANCE ({host}) ---")
    strategy = SubdomainReconStrategy()
    count = 0
    async for finding in strategy.run_async(type('Target', (), {'host': host})):
        print(f"  [SUCCESS] Found Asset: {finding.title}")
        count += 1
        if count >= 2: break
    return count > 0

async def verify_step_2():
    host = "scanme.nmap.org"
    print(f"\n--- STEP 2: PORT SCANNING ({host}) ---")
    strategy = PortScanStrategy()
    count = 0
    async for finding in strategy.run_async(type('Target', (), {'host': host})):
        print(f"  [SUCCESS] Found Port: {finding.title}")
        count += 1
        if count >= 2: break
    return count > 0

async def verify_step_3():
    host = "nmap.org"
    print(f"\n--- STEP 3: VULNERABILITY/TECH SCAN ({host}) ---")
    strategy = NucleiTechStrategy()
    count = 0
    # Nuclei on nmap.org should find something (e.g. Apache, WAF, etc.)
    async for finding in strategy.run_async(type('Target', (), {'host': host})):
        print(f"  [SUCCESS] Found Finding: {finding.title} ({finding.severity})")
        count += 1
        if count >= 2: break
    return count > 0

async def main():
    print("="*60)
    print("HACKERSCAN PRO - CORE SYSTEM VALIDATION")
    print("Rules: Real Tools, No Simulations, Real Data Proofs")
    print("="*60)
    
    s1 = await verify_step_1()
    s2 = await verify_step_2()
    s3 = await verify_step_3()
    
    print("\n" + "="*40)
    print("VERIFICATION SUMMARY")
    print(f"STEP 1 (Discovery): {'PASS' if s1 else 'FAIL'}")
    print(f"STEP 2 (Auditing):  {'PASS' if s2 else 'FAIL'}")
    print(f"STEP 3 (Vuln/Tech): {'PASS' if s3 else 'FAIL'}")
    print("="*40)
    
    if s1 and s2 and s3:
        print("\n[!!!] CERTIFIED: All core scanning engines are fully operational.")
    else:
        print("\n[xxx] FAILED: Some engines are not producing results.")

if __name__ == "__main__":
    asyncio.run(main())
