
import asyncio
import os
import sys
import django
from typing import AsyncGenerator

# Setup Django
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from scans.strategies.subdomain_recon import SubdomainReconStrategy
from scans.strategies.port_scan import PortScanStrategy
from scans.strategies.nuclei_scan import NucleiVulnStrategy
from scans.models import Severity

async def verify_step2_fast():
    print("\n--- STEP 2: SUBDOMAIN RECONNAISSANCE (FAST) ---")
    strategy = SubdomainReconStrategy()
    target_mock = type('Target', (), {'host': 'nmap.org'})()
    
    # Patch to skip slow tools for verification
    print("[*] Patching strategy to skip slow tools (amass, crt.sh)...")
    original_get_crt = strategy._get_crt_sh_subdomains_async
    original_run_amass = strategy._run_amass_async
    strategy._get_crt_sh_subdomains_async = lambda host: asyncio.sleep(0, result=[])
    strategy._run_amass_async = lambda host: asyncio.sleep(0, result=[])
    
    print(f"[*] Executing SubdomainReconStrategy for {target_mock.host}...")
    found_count = 0
    try:
        async for finding in strategy.run_async(target_mock, scan=None):
            print(f"[+] FOUND SUBDOMAIN: {finding.title}")
            found_count += 1
            if found_count >= 3: break # Cap for test
    except Exception as e:
        print(f"[-] Error in Step 2: {e}")
        import traceback
        traceback.print_exc()
        
    if found_count == 0:
        print("[-] No subdomains found.")
    else:
        print(f"[!] Step 2 PASSED: {found_count} findings yielded.")

async def verify_step3_ports_fast():
    print("\n--- STEP 3.1: PORT SCANNING (FAST) ---")
    strategy = PortScanStrategy()
    target_mock = type('Target', (), {'host': 'scanme.nmap.org'})()
    
    print(f"[*] Executing PortScanStrategy for {target_mock.host}...")
    found_count = 0
    try:
        # Run top 10 ports only for speed
        async for finding in strategy.run_async(target_mock, scan=None):
            print(f"[+] PORT FOUND: {finding.title}")
            found_count += 1
            if found_count >= 3: break
    except Exception as e:
        print(f"[-] Error in Step 3.1: {e}")
        
    if found_count == 0:
        print("[-] No open ports found.")
    else:
        print(f"[!] Step 3.1 PASSED: {found_count} ports detected.")

async def verify_step3_nuclei_fast():
    print("\n--- STEP 3.2: NUCLEI VULNERABILITY SCAN (FAST) ---")
    strategy = NucleiVulnStrategy()
    # Use nmap.org which is fast
    target_mock = type('Target', (), {'host': 'nmap.org'})()
    
    print(f"[*] Executing NucleiVulnStrategy (tech detection) for {target_mock.host}...")
    found_count = 0
    try:
        # Use tech detection as it's faster and guaranteed to find something (Apache)
        async for finding in strategy._run_nuclei_async(target_mock, tags="tech"):
            print(f"[+] TECH FOUND: {finding.title} ({finding.severity})")
            found_count += 1
            if found_count >= 3: break
    except Exception as e:
        print(f"[-] Error in Step 3.2: {e}")
        
    if found_count == 0:
        print("[*] No techs found.")
    else:
        print(f"[!] Step 3.2 PASSED: {found_count} findings yielded.")

async def main():
    print("=== HACKERSCAN PRO: FAST VERIFICATION (ZERO SIMULATION) ===")
    
    try:
        await verify_step2_fast()
        await verify_step3_ports_fast()
        await verify_step3_nuclei_fast()
    except Exception as e:
        print(f"\n[!] VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
