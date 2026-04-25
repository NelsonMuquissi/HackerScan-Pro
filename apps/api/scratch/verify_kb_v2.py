import os
import django
import sys

# Add the apps/api directory to the path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from ai.services import AIService

def test_kb_logic():
    ai = AIService()
    test_cases = [
        "Open port 5432/PostgreSQL",
        "SQL Injection in login form",
        "Cross-Site Scripting (XSS) detected",
        "Missing Content-Security-Policy header",
        "Strict-Transport-Security header is not present",
        "X-Frame-Options missing",
        "Insecure TLS 1.0 supported",
        "Unknown random finding"
    ]
    
    print(f"{'Title':<50} | {'KB Key Detected'}")
    print("-" * 75)
    for title in test_cases:
        entry = ai._get_kb_entry(title)
        
        # Find which key in VULNERABILITY_KB corresponds to this entry
        kb_key = "default"
        from ai.services import VULNERABILITY_KB
        for key, val in VULNERABILITY_KB.items():
            if val == entry:
                kb_key = key
                break
        
        print(f"{title:<50} | {kb_key}")

if __name__ == "__main__":
    test_kb_logic()
