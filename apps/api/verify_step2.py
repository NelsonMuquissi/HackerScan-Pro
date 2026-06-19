
import asyncio
import os
import sys
import django

# Setup Django
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from scans.strategies.subdomain_recon import SubdomainReconStrategy
from scans.models import Scan

async def test_recon():
    strategy = SubdomainReconStrategy()
    target_mock = type('Target', (), {'host': 'nmap.org'})()
    
    print(f"[*] Testing SubdomainReconStrategy for {target_mock.host}...")
    
    found = False
    async for finding in strategy.run_async(target_mock, scan=None):
        print(f"[+] FOUND: {finding.title}")
        print(f"    - Endpoint: {finding.endpoint}")
        print(f"    - Severity: {finding.severity}")
        found = True
        
    if not found:
        print("[-] No subdomains found (this might be normal or a failure).")
    else:
        print("[!] Step 2 PASSED: Subdomain discovery is working.")

if __name__ == "__main__":
    asyncio.run(test_recon())
