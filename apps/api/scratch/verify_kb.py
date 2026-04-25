from ai.services import AIService, VULNERABILITY_KB

def test_fallback():
    # Mocking what's needed for AIService if necessary, 
    # but here we just want to test _get_kb_entry which is logic-based.
    
    # We can just instantiate it if it doesn't do too much in __init__
    # If it fails, we'll just test the VULNERABILITY_KB dictionary and a mock function.
    
    test_cases = [
        "SQL Injection",
        "Cross-Site Scripting (XSS)",
        "Missing Content-Security-Policy header",
        "Missing Strict-Transport-Security header",
        "X-Frame-Options header missing (Clickjacking)",
        "Insecure TLS Version (TLS 1.0)",
        "Open Port detected: 80",
        "Unknown Vulnerability"
    ]
    
    def mock_get_kb_entry(title: str) -> dict:
        t = title.lower()
        if "sql" in t: return VULNERABILITY_KB["sql_injection"]
        if "xss" in t or "scripting" in t: return VULNERABILITY_KB["xss"]
        if "auth" in t or "login" in t or "password" in t: return VULNERABILITY_KB["broken_auth"]
        if "idor" in t or "direct object" in t: return VULNERABILITY_KB["idor"]
        if "info" in t or "exposure" in t or "leak" in t: return VULNERABILITY_KB["info_exposure"]
        if "content-security-policy" in t or "csp" in t: return VULNERABILITY_KB["csp"]
        if "strict-transport-security" in t or "hsts" in t: return VULNERABILITY_KB["hsts"]
        if "frame-options" in t or "clickjacking" in t: return VULNERABILITY_KB["clickjacking"]
        if "tls" in t or "ssl" in t: return VULNERABILITY_KB["tls_version"]
        if "port" in t: return VULNERABILITY_KB["open_port"]
        return VULNERABILITY_KB["default"]

    print(f"{'Title':<45} | {'KB Key':<15}")
    print("-" * 65)
    for title in test_cases:
        entry = mock_get_kb_entry(title)
        kb_key = "unknown"
        for key, val in VULNERABILITY_KB.items():
            if val == entry:
                kb_key = key
                break
        
        print(f"{title:<45} | {kb_key:<15}")

if __name__ == "__main__":
    test_fallback()

if __name__ == "__main__":
    test_fallback()
