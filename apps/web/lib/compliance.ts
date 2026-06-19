/**
 * HackerScan Pro Compliance Intelligence Library
 * Centralized logic for mapping vulnerability patterns to industry standards.
 */

export interface ComplianceMapping {
  owasp: string;
  mitre: string;
  description?: string;
}

export const COMPLIANCE_STANDARDS = {
  INJECTION: {
    owasp: 'A03:2021-Injection',
    mitre: 'CWE-89',
    keywords: ['sql', 'sqli', 'query', 'database']
  },
  XSS: {
    owasp: 'A03:2021-Injection',
    mitre: 'CWE-79',
    keywords: ['xss', 'cross-site', 'scripting', 'javascript', 'html injection']
  },
  BROKEN_AUTH: {
    owasp: 'A07:2021-Identification and Authentication Failures',
    mitre: 'CWE-287',
    keywords: ['login', 'auth', 'password', 'session', 'jwt', 'mfa']
  },
  BROKEN_ACCESS: {
    owasp: 'A01:2021-Broken Access Control',
    mitre: 'CWE-285',
    keywords: ['idor', 'permission', 'unauthorized', 'access control', 'privilege escalation']
  },
  SSRF: {
    owasp: 'A10:2021-Server-Side Request Forgery',
    mitre: 'CWE-918',
    keywords: ['ssrf', 'internal request', 'metadata', 'proxy']
  },
  RCE: {
    owasp: 'A03:2021-Injection',
    mitre: 'CWE-94',
    keywords: ['rce', 'command execution', 'shell', 'remote code']
  },
  CRYPTO_FAILURE: {
    owasp: 'A02:2021-Cryptographic Failures',
    mitre: 'CWE-311',
    keywords: ['encryption', 'ssl', 'tls', 'cipher', 'cryptography']
  },
  SEC_MISCONFIG: {
    owasp: 'A05:2021-Security Misconfiguration',
    mitre: 'CWE-16',
    keywords: ['config', 'header', 'cors', 'debug', 'default credentials']
  },
  VULN_COMPONENTS: {
    owasp: 'A06:2021-Vulnerable and Outdated Components',
    mitre: 'CWE-1104',
    keywords: ['outdated', 'library', 'version', 'cve']
  }
};

export function suggestCompliance(title: string, description: string): ComplianceMapping | null {
  const text = (title + ' ' + description).toLowerCase();
  
  for (const [key, standard] of Object.entries(COMPLIANCE_STANDARDS)) {
    if (standard.keywords.some(keyword => text.includes(keyword))) {
      return {
        owasp: standard.owasp,
        mitre: standard.mitre,
        description: `Suggested based on detected pattern: ${key}`
      };
    }
  }
  
  return null;
}
