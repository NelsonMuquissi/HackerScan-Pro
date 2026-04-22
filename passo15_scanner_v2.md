# HackerScan Pro — Passo 15: Scanner Engine v2
# Prompt completo para Antigravity

---

## CONTEXTO

O scanner actual (v1) tem score 6.5/10 — faz port scan (19 portas TCP),
SSL check e headers check. O objectivo deste passo é subir para 9.0/10
adicionando 7 engines novas: Nuclei, Subfinder, Full Port Scan,
TLS Cipher Scan, Directory Bruteforce, Web Spidering e Authenticated Scanning.

Lê o ficheiro `hackscan_pro_master_v2.md` antes de começar.
Segue a SKILL Scanner Engine do guia `antigravity_prompt_hackscan.md`.

**Regra absoluta: zero simulações. Cada engine executa ferramentas reais.**

---

## ARQUITECTURA DO SCANNER V2

O sistema usa o padrão Strategy já implementado.
Cada nova feature é uma nova `BaseScanStrategy` que:
1. Executa ferramenta real via subprocess
2. Faz broadcast em tempo real via `broadcast_terminal_line()`
3. Persiste findings no modelo `Finding`
4. Retorna `FindingResult` estruturado

Estrutura de ficheiros a criar:

```
apps/api/scans/strategies/
├── nuclei_scan.py          ← NOVA — Nuclei CVE/vuln scanner
├── subfinder_scan.py       ← NOVA — Subdomain discovery
├── full_port_scan.py       ← NOVA — Top 1000 TCP + UDP
├── tls_cipher_scan.py      ← NOVA — TLS/SSL cipher analysis
├── dir_bruteforce.py       ← NOVA — Directory/file discovery
├── web_spider.py           ← NOVA — Web crawler/spidering
├── auth_scan.py            ← NOVA — Authenticated scanning
└── __init__.py             ← MODIFICAR — registar engines novas

apps/api/scans/
├── wordlists/
│   ├── common.txt          ← wordlist para gobuster (top 1000 paths)
│   └── subdomains.txt      ← wordlist para subfinder fallback

requirements/base.txt       ← MODIFICAR — adicionar sslyze, playwright
docker-compose.yml          ← MODIFICAR — instalar nuclei, subfinder,
                                           gobuster no container scanner
```

---

## PASSO A PASSO — LISTA ANTES DE CRIAR

Antes de escrever qualquer código, lista os ficheiros e
aguarda confirmação.

---

## ENGINE 1 — NUCLEI (prioridade máxima)

**O que faz:** executa templates Nuclei contra o target.
Detecta CVEs conhecidos, misconfigs, exposições de painéis admin,
tokens expostos, SQLi, XSS, SSRF e muito mais.

**Modelo a usar para este ficheiro: Claude Opus 4.6 (Thinking)**
Nuclei é o core da detecção de vulnerabilidades reais.

```python
# apps/api/scans/strategies/nuclei_scan.py

import subprocess
import json
import shutil
from pathlib import Path
from .base import BaseScanStrategy, FindingResult

class NucleiScanStrategy(BaseScanStrategy):
    """
    Executa Nuclei templates contra o target.
    Detecta CVEs, misconfigs, exposições, injecções.
    """
    name = "nuclei_scan"
    
    SEVERITY_MAP = {
        "critical": "critical",
        "high": "high", 
        "medium": "medium",
        "low": "low",
        "info": "info",
        "unknown": "info",
    }
    
    def is_available(self) -> bool:
        return shutil.which("nuclei") is not None
    
    def execute(self, target: str, config: dict, scan_id: str) -> list[FindingResult]:
        if not self.is_available():
            self.log(scan_id, "[nuclei] ERRO: Nuclei não está instalado.", "error")
            return []
        
        self.log(scan_id, f"[nuclei] Iniciando scan de vulnerabilidades em {target}...", "info")
        self.log(scan_id, "[nuclei] Carregando templates actualizados...", "info")
        
        # Actualizar templates antes do scan
        subprocess.run(
            ["nuclei", "-update-templates", "-silent"],
            capture_output=True, timeout=60
        )
        
        cmd = [
            "nuclei",
            "-u", target,
            "-json",           # output JSON por linha
            "-silent",
            "-no-color",
            "-timeout", "10",
            "-retries", "2",
            "-severity", "critical,high,medium,low,info",
            "-exclude-tags", "dos,fuzz",  # evitar DoS em targets reais
        ]
        
        # Auth se configurada
        auth = config.get("auth", {})
        if auth.get("type") == "bearer":
            cmd.extend(["-H", f"Authorization: Bearer {auth['token']}"])
        elif auth.get("type") == "cookie":
            cmd.extend(["-H", f"Cookie: {auth['cookie']}"])
        elif auth.get("type") == "basic":
            cmd.extend(["-H", f"Authorization: Basic {auth['encoded']}"])
        
        findings = []
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue
            try:
                result = json.loads(line)
                finding = self._parse_nuclei_result(result, scan_id)
                if finding:
                    findings.append(finding)
                    self.log(
                        scan_id,
                        f"[nuclei] ENCONTRADO [{finding.severity.upper()}]: "
                        f"{finding.title} @ {finding.endpoint}",
                        "finding"
                    )
            except json.JSONDecodeError:
                continue
        
        process.wait()
        self.log(
            scan_id,
            f"[nuclei] Scan concluído. {len(findings)} vulnerabilidades encontradas.",
            "success"
        )
        return findings
    
    def _parse_nuclei_result(self, raw: dict, scan_id: str) -> FindingResult | None:
        info = raw.get("info", {})
        severity = self.SEVERITY_MAP.get(
            info.get("severity", "info").lower(), "info"
        )
        
        # Extrair CWE e CVE
        classification = info.get("classification", {})
        cwe_ids = classification.get("cwe-id", [])
        cve_ids = classification.get("cve-id", [])
        cvss_score = classification.get("cvss-score")
        
        return FindingResult(
            title=info.get("name", "Unknown Finding"),
            type=raw.get("template-id", "nuclei-generic"),
            severity=severity,
            endpoint=raw.get("matched-at", raw.get("host", "")),
            method=raw.get("request", {}).get("method"),
            parameter=raw.get("matcher-name"),
            description=info.get("description", ""),
            evidence=raw.get("response", "")[:1000],  # truncar
            proof_of_concept=raw.get("request", ""),
            curl_command=self._build_curl(raw),
            remediation=info.get("remediation", 
                "Consulte a documentação OWASP para remediação."),
            cvss_score=float(cvss_score) if cvss_score else None,
            cwe_id=cwe_ids[0] if cwe_ids else None,
            references=cve_ids + info.get("reference", []),
            engine="nuclei",
            template_id=raw.get("template-id"),
        )
    
    def _build_curl(self, raw: dict) -> str | None:
        req = raw.get("request", {})
        if not req or isinstance(req, str):
            return None
        method = req.get("method", "GET")
        url = raw.get("matched-at", "")
        headers = " ".join(
            f'-H "{k}: {v}"'
            for k, v in (req.get("headers") or {}).items()
            if k.lower() not in ("host",)
        )
        body = f"-d '{req.get('body')}'" if req.get("body") else ""
        return f"curl -X {method} {headers} {body} '{url}'"
```

**Implementa exactamente assim. Sem simplificações.**

---

## ENGINE 2 — SUBFINDER (subdomain discovery)

**O que faz:** descobre subdomínios do target usando DNS,
certificate transparency logs, APIs públicas.

**Modelo: Claude Sonnet 4.6 (Thinking)**

```python
# apps/api/scans/strategies/subfinder_scan.py

import subprocess
import json
import shutil
from urllib.parse import urlparse
from .base import BaseScanStrategy, FindingResult

class SubfinderScanStrategy(BaseScanStrategy):
    name = "subfinder_scan"
    
    def is_available(self) -> bool:
        return shutil.which("subfinder") is not None
    
    def execute(self, target: str, config: dict, scan_id: str) -> list[FindingResult]:
        # Extrair domínio base do URL
        parsed = urlparse(target)
        domain = parsed.netloc or parsed.path
        domain = domain.replace("www.", "")
        
        self.log(scan_id, f"[subfinder] Descobrindo subdomínios de {domain}...", "info")
        
        cmd = [
            "subfinder",
            "-d", domain,
            "-json",
            "-silent",
            "-timeout", "30",
        ]
        
        if not self.is_available():
            # Fallback: crt.sh via HTTP
            return self._fallback_crtsh(domain, scan_id)
        
        findings = []
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        
        subdomains = set()
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                subdomain = data.get("host", "")
                if subdomain and subdomain not in subdomains:
                    subdomains.add(subdomain)
                    self.log(scan_id, f"[subfinder] ENCONTRADO: {subdomain}", "info")
                    findings.append(FindingResult(
                        title=f"Subdomínio descoberto: {subdomain}",
                        type="subdomain_discovery",
                        severity="info",
                        endpoint=f"https://{subdomain}",
                        description=f"Subdomínio activo encontrado: {subdomain}",
                        remediation="Verifique se este subdomínio deve ser público "
                                    "e se está devidamente protegido.",
                        engine="subfinder",
                        metadata={"source": data.get("source", "unknown")},
                    ))
            except json.JSONDecodeError:
                continue
        
        process.wait()
        self.log(
            scan_id,
            f"[subfinder] {len(findings)} subdomínios encontrados em {domain}.",
            "success"
        )
        return findings
    
    def _fallback_crtsh(self, domain: str, scan_id: str) -> list[FindingResult]:
        """Fallback para crt.sh quando subfinder não está instalado."""
        import requests
        self.log(scan_id, "[subfinder] Usando crt.sh como fallback...", "info")
        try:
            resp = requests.get(
                f"https://crt.sh/?q=%.{domain}&output=json",
                timeout=15
            )
            entries = resp.json()
            subdomains = {
                e["name_value"].strip()
                for e in entries
                if e.get("name_value") and "*" not in e["name_value"]
            }
            findings = []
            for sub in subdomains:
                self.log(scan_id, f"[subfinder] crt.sh: {sub}", "info")
                findings.append(FindingResult(
                    title=f"Subdomínio descoberto: {sub}",
                    type="subdomain_discovery",
                    severity="info",
                    endpoint=f"https://{sub}",
                    description=f"Subdomínio encontrado via Certificate Transparency: {sub}",
                    remediation="Verifique se este subdomínio deve ser público.",
                    engine="crtsh",
                ))
            return findings
        except Exception as e:
            self.log(scan_id, f"[subfinder] Erro no fallback crt.sh: {e}", "error")
            return []
```

---

## ENGINE 3 — FULL PORT SCAN (top 1000 + UDP)

**O que faz:** scan das top 1000 portas TCP (padrão Nmap)
mais portas UDP críticas. Substitui o port_scan.py actual (19 portas).

**Modelo: Claude Sonnet 4.6 (Thinking)**

```python
# apps/api/scans/strategies/full_port_scan.py

import socket
import concurrent.futures
from .base import BaseScanStrategy, FindingResult

# Top 1000 portas TCP (Nmap default)
TOP_1000_TCP = [
    1,3,4,6,7,9,13,17,19,20,21,22,23,24,25,26,30,32,33,37,42,43,49,53,
    70,79,80,81,82,83,84,85,88,89,90,99,100,106,109,110,111,113,119,125,
    135,139,143,144,146,161,163,179,199,211,212,222,254,255,256,259,264,
    280,301,306,311,340,366,389,406,407,416,417,425,427,443,444,445,458,
    464,465,481,497,500,512,513,514,515,524,541,543,544,545,548,554,555,
    563,587,593,616,617,625,631,636,646,648,666,667,668,683,687,691,700,
    705,711,714,720,722,726,749,765,777,783,787,800,801,808,843,873,880,
    888,898,900,901,902,903,911,912,981,987,990,992,993,995,999,1000,
    1001,1002,1007,1009,1010,1011,1021,1022,1023,1024,1025,1026,1027,
    1028,1029,1030,1031,1032,1033,1034,1035,1036,1037,1038,1039,1040,
    1041,1042,1043,1044,1045,1046,1047,1048,1049,1050,1051,1052,1053,
    1054,1055,1056,1057,1058,1059,1060,1061,1062,1063,1064,1065,1066,
    1067,1068,1069,1070,1071,1072,1073,1074,1075,1076,1077,1078,1079,
    1080,1081,1082,1083,1084,1085,1086,1087,1088,1089,1090,1091,1092,
    1093,1094,1095,1096,1097,1098,1099,1100,1102,1104,1105,1106,1107,
    1108,1110,1111,1112,1113,1114,1117,1119,1121,1122,1123,1124,1126,
    1130,1131,1132,1137,1138,1141,1145,1147,1148,1149,1151,1152,1154,
    1163,1164,1165,1166,1169,1174,1175,1183,1185,1186,1187,1192,1198,
    1199,1201,1213,1216,1217,1218,1233,1234,1236,1244,1247,1248,1259,
    1271,1272,1277,1287,1296,1300,1301,1309,1310,1311,1322,1328,1334,
    1352,1417,1433,1434,1443,1455,1461,1494,1500,1501,1503,1521,1524,
    1533,1556,1580,1583,1594,1600,1641,1658,1666,1687,1688,1700,1717,
    1718,1719,1720,1721,1723,1755,1761,1782,1783,1801,1805,1812,1839,
    1840,1862,1863,1864,1875,1900,1914,1935,1947,1971,1972,1974,1984,
    1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,
    2013,2020,2021,2022,2030,2033,2034,2035,2038,2040,2041,2042,2043,
    2045,2046,2047,2048,2049,2065,2068,2099,2100,2103,2105,2106,2107,
    2111,2119,2121,2126,2135,2144,2160,2161,2170,2179,2190,2191,2196,
    2200,2222,2251,2260,2288,2301,2323,2366,2381,2382,2383,2393,2394,
    2399,2401,2492,2500,2522,2525,2557,2601,2602,2604,2605,2607,2608,
    2638,2701,2702,2710,2717,2718,2725,2800,2809,2811,2869,2875,2909,
    2910,2920,2967,2968,2998,3000,3001,3003,3005,3006,3007,3011,3013,
    3017,3030,3031,3052,3071,3077,3128,3168,3211,3221,3260,3261,3268,
    3269,3283,3300,3301,3306,3322,3323,3324,3325,3333,3351,3367,3369,
    3370,3371,3372,3389,3390,3404,3476,3493,3517,3527,3546,3551,3580,
    3659,3689,3690,3703,3737,3766,3784,3800,3801,3809,3814,3826,3827,
    3828,3851,3869,3871,3878,3880,3889,3905,3914,3918,3920,3945,3971,
    3986,3995,3998,4000,4001,4002,4003,4004,4005,4006,4045,4111,4125,
    4126,4129,4224,4242,4279,4321,4343,4443,4444,4445,4446,4449,4550,
    4567,4662,4848,4899,4900,4998,5000,5001,5002,5003,5004,5009,5030,
    5033,5050,5051,5054,5060,5061,5080,5087,5100,5101,5102,5120,5190,
    5200,5214,5221,5222,5225,5226,5269,5280,5298,5357,5405,5414,5431,
    5432,5440,5500,5510,5544,5550,5555,5560,5566,5631,5633,5666,5678,
    5679,5718,5730,5800,5801,5802,5810,5811,5815,5822,5825,5850,5859,
    5862,5877,5900,5901,5902,5903,5904,5906,5907,5910,5911,5915,5922,
    5925,5950,5952,5959,5960,5961,5962,5963,5987,5988,5989,5998,5999,
    6000,6001,6002,6003,6004,6005,6006,6007,6009,6025,6059,6100,6101,
    6106,6112,6123,6129,6156,6346,6389,6502,6510,6543,6547,6565,6566,
    6567,6580,6646,6666,6667,6668,6669,6689,6692,6699,6779,6788,6789,
    6792,6839,6881,6901,6969,7000,7001,7002,7004,7007,7019,7025,7070,
    7100,7103,7106,7200,7201,7402,7435,7443,7496,7512,7625,7627,7676,
    7741,7777,7778,7800,7911,7920,7921,7937,7938,7999,8000,8001,8002,
    8007,8008,8009,8010,8011,8021,8022,8031,8042,8045,8080,8081,8082,
    8083,8084,8085,8086,8087,8088,8089,8090,8093,8099,8100,8180,8181,
    8192,8193,8194,8200,8222,8254,8290,8291,8292,8300,8333,8383,8400,
    8402,8443,8500,8600,8649,8651,8652,8654,8701,8800,8873,8888,8899,
    8994,9000,9001,9002,9003,9009,9010,9011,9040,9050,9071,9080,9081,
    9090,9091,9099,9100,9101,9102,9103,9110,9111,9200,9207,9220,9290,
    9415,9418,9485,9500,9502,9503,9535,9575,9593,9594,9595,9618,9666,
    9876,9877,9878,9898,9900,9917,9929,9943,9944,9968,9998,9999,10000,
    10001,10002,10003,10004,10009,10010,10012,10024,10025,10082,10180,
    10215,10243,10566,10616,10617,10621,10626,10628,10629,10778,11110,
    11111,11967,12000,12174,12265,12345,13456,13722,13782,13783,14000,
    14238,14441,14442,15000,15002,15003,15004,15660,15742,16000,16001,
    16012,16016,16018,16080,16113,16992,16993,17877,17988,18040,18101,
    18988,19101,19283,19315,19350,19780,19801,19842,20000,20005,20031,
    20221,20222,20828,21571,22939,23502,24444,24800,25734,25735,26214,
    27000,27352,27353,27355,27356,27715,28201,30000,30718,30951,31038,
    31337,32768,32769,32770,32771,32772,32773,32774,32775,32776,32777,
    32778,32779,32780,32781,32782,32783,32784,32785,33354,33899,34571,
    34572,34573,35500,38292,40193,40911,41511,42510,44176,44442,44443,
    44501,45100,48080,49152,49153,49154,49155,49156,49157,49158,49159,
    49160,49161,49163,49165,49167,49175,49176,49400,49999,50000,50001,
    50002,50003,50006,50300,50389,50500,50636,50800,51103,51493,52673,
    52822,52848,52869,54045,54328,55055,55056,55555,55600,56737,56738,
    57294,57797,58080,60020,60443,61532,61900,62078,63331,64623,64680,
    65000,65129,65389
]

# Portas UDP críticas
CRITICAL_UDP = [53, 67, 68, 69, 123, 161, 162, 500, 514, 1194, 1900, 4500, 5353]

PORT_SERVICES = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 135: "RPC", 139: "NetBIOS", 143: "IMAP",
    443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
    1433: "MSSQL", 1521: "Oracle", 3306: "MySQL", 3389: "RDP",
    5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 27017: "MongoDB", 9200: "Elasticsearch",
}

HIGH_RISK_PORTS = {23, 135, 139, 445, 1433, 1521, 3389, 5900, 6379, 27017, 9200}

class FullPortScanStrategy(BaseScanStrategy):
    name = "full_port_scan"
    
    def execute(self, target: str, config: dict, scan_id: str) -> list[FindingResult]:
        from urllib.parse import urlparse
        parsed = urlparse(target)
        host = parsed.netloc or parsed.path
        host = host.split(":")[0]  # remover porta se presente
        
        self.log(scan_id, f"[port_scan] Iniciando scan completo em {host}...", "info")
        self.log(scan_id, f"[port_scan] Verificando {len(TOP_1000_TCP)} portas TCP + {len(CRITICAL_UDP)} UDP...", "info")
        
        findings = []
        open_ports = []
        
        # TCP scan paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = {
                executor.submit(self._check_tcp, host, port): port
                for port in TOP_1000_TCP
            }
            for future in concurrent.futures.as_completed(futures):
                port = futures[future]
                is_open = future.result()
                if is_open:
                    service = PORT_SERVICES.get(port, "Unknown")
                    open_ports.append((port, service))
                    severity = "high" if port in HIGH_RISK_PORTS else "info"
                    self.log(
                        scan_id,
                        f"[port_scan] ABERTA: {port}/TCP ({service})",
                        "finding" if severity == "high" else "info"
                    )
                    finding = self._create_port_finding(host, port, service, "tcp", severity)
                    findings.append(finding)
        
        # UDP scan (portas críticas)
        self.log(scan_id, "[port_scan] Verificando portas UDP críticas...", "info")
        for port in CRITICAL_UDP:
            is_open = self._check_udp(host, port)
            if is_open:
                service = PORT_SERVICES.get(port, "UDP Service")
                self.log(scan_id, f"[port_scan] UDP ABERTA: {port} ({service})", "info")
                findings.append(
                    self._create_port_finding(host, port, service, "udp", "medium")
                )
        
        self.log(
            scan_id,
            f"[port_scan] Scan concluído. {len(open_ports)} portas abertas encontradas.",
            "success"
        )
        return findings
    
    def _check_tcp(self, host: str, port: int, timeout: float = 1.0) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
    
    def _check_udp(self, host: str, port: int, timeout: float = 2.0) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.sendto(b"\x00" * 8, (host, port))
            sock.recvfrom(1024)
            return True
        except socket.timeout:
            return True  # Sem resposta = porta possivelmente aberta (UDP)
        except OSError:
            return False
        finally:
            sock.close()
    
    def _create_port_finding(
        self, host: str, port: int, service: str, proto: str, severity: str
    ) -> FindingResult:
        is_risky = port in HIGH_RISK_PORTS
        return FindingResult(
            title=f"Porta {port}/{proto.upper()} aberta ({service})",
            type="open_port",
            severity=severity,
            endpoint=f"{host}:{port}",
            description=(
                f"A porta {port}/{proto.upper()} ({service}) está acessível externamente. "
                + ("Esta porta é considerada de alto risco e não deve estar exposta."
                   if is_risky else "")
            ),
            remediation=(
                f"Restrinja o acesso à porta {port} via firewall. "
                "Apenas IPs autorizados devem ter acesso a este serviço."
                if is_risky else
                f"Verifique se o serviço na porta {port} é necessário ser público."
            ),
            engine="full_port_scan",
            metadata={"port": port, "protocol": proto, "service": service},
        )
```

---

## ENGINE 4 — TLS CIPHER SCAN

**O que faz:** analisa a configuração TLS — protocolos obsoletos
(SSLv3, TLS 1.0, TLS 1.1), ciphers fracos, certificado completo.

**Modelo: Claude Sonnet 4.6 (Thinking)**

```python
# apps/api/scans/strategies/tls_cipher_scan.py
# Usa sslyze (pip install sslyze)

from sslyze import (
    Scanner, ServerNetworkLocation, ServerScanRequest,
    ScanCommand,
)
from sslyze.errors import ConnectionToServerFailed
from .base import BaseScanStrategy, FindingResult

WEAK_CIPHERS = [
    "RC4", "DES", "3DES", "EXPORT", "NULL", "ANON", "MD5",
    "PSK", "SRP", "DSS", "ECDSA",
]

WEAK_PROTOCOLS = ["ssl_2_0", "ssl_3_0", "tls_1_0", "tls_1_1"]

class TLSCipherScanStrategy(BaseScanStrategy):
    name = "tls_cipher_scan"
    
    def execute(self, target: str, config: dict, scan_id: str) -> list[FindingResult]:
        from urllib.parse import urlparse
        parsed = urlparse(target)
        host = parsed.netloc or parsed.path
        host = host.split(":")[0]
        
        self.log(scan_id, f"[tls_scan] Analisando configuração TLS/SSL de {host}...", "info")
        
        findings = []
        
        try:
            location = ServerNetworkLocation(host, 443)
            request = ServerScanRequest(
                server_location=location,
                scan_commands={
                    ScanCommand.SSL_2_0_CIPHER_SUITES,
                    ScanCommand.SSL_3_0_CIPHER_SUITES,
                    ScanCommand.TLS_1_0_CIPHER_SUITES,
                    ScanCommand.TLS_1_1_CIPHER_SUITES,
                    ScanCommand.TLS_1_2_CIPHER_SUITES,
                    ScanCommand.TLS_1_3_CIPHER_SUITES,
                    ScanCommand.CERTIFICATE_INFO,
                    ScanCommand.HEARTBLEED,
                    ScanCommand.ROBOT,
                    ScanCommand.SESSION_RESUMPTION,
                },
            )
            
            scanner = Scanner()
            scanner.queue_scans([request])
            
            for result in scanner.get_results():
                findings.extend(
                    self._analyse_result(result, host, scan_id)
                )
        
        except ConnectionToServerFailed as e:
            self.log(scan_id, f"[tls_scan] Não foi possível conectar: {e}", "error")
        except Exception as e:
            self.log(scan_id, f"[tls_scan] Erro na análise TLS: {e}", "error")
        
        self.log(
            scan_id,
            f"[tls_scan] Análise TLS concluída. {len(findings)} problemas encontrados.",
            "success"
        )
        return findings
    
    def _analyse_result(self, result, host: str, scan_id: str) -> list[FindingResult]:
        findings = []
        
        # Verificar protocolos fracos
        weak_checks = [
            ("ssl_2_0", result.scan_result.ssl_2_0_cipher_suites, "SSLv2", "critical"),
            ("ssl_3_0", result.scan_result.ssl_3_0_cipher_suites, "SSLv3", "critical"),
            ("tls_1_0", result.scan_result.tls_1_0_cipher_suites, "TLS 1.0", "high"),
            ("tls_1_1", result.scan_result.tls_1_1_cipher_suites, "TLS 1.1", "medium"),
        ]
        
        for proto_id, scan_cmd_result, proto_name, severity in weak_checks:
            if (scan_cmd_result and 
                not scan_cmd_result.is_scan_command_attempt_extra_exception and
                scan_cmd_result.result and
                scan_cmd_result.result.accepted_cipher_suites):
                
                self.log(
                    scan_id,
                    f"[tls_scan] VULNERÁVEL: Protocolo {proto_name} aceite",
                    "finding"
                )
                findings.append(FindingResult(
                    title=f"Protocolo obsoleto aceite: {proto_name}",
                    type="weak_tls_protocol",
                    severity=severity,
                    endpoint=f"https://{host}:443",
                    description=(
                        f"O servidor aceita conexões usando {proto_name}, "
                        f"um protocolo considerado inseguro e obsoleto."
                    ),
                    remediation=(
                        f"Desactive {proto_name} na configuração do servidor web. "
                        "Use apenas TLS 1.2 e TLS 1.3."
                    ),
                    cvss_score=8.1 if severity == "critical" else 6.5,
                    references=["https://cve.mitre.org/cgi-bin/cvekey.cgi?keyword=ssl"],
                    engine="tls_cipher_scan",
                ))
        
        # Verificar Heartbleed
        heartbleed = result.scan_result.heartbleed
        if (heartbleed and not heartbleed.is_scan_command_attempt_extra_exception and
                heartbleed.result and heartbleed.result.is_vulnerable_to_heartbleed):
            self.log(scan_id, "[tls_scan] CRÍTICO: Vulnerável ao Heartbleed!", "finding")
            findings.append(FindingResult(
                title="Vulnerabilidade Heartbleed (CVE-2014-0160)",
                type="heartbleed",
                severity="critical",
                endpoint=f"https://{host}:443",
                description="O servidor é vulnerável ao Heartbleed — um atacante pode "
                            "extrair chaves privadas e dados sensíveis da memória.",
                remediation="Actualize o OpenSSL imediatamente para versão >= 1.0.1g.",
                cvss_score=9.8,
                cwe_id="CWE-119",
                references=["https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-0160"],
                engine="tls_cipher_scan",
            ))
        
        return findings
```

---

## ENGINE 5 — DIRECTORY BRUTEFORCE

**O que faz:** descobre ficheiros e directorias ocultos
(painéis admin, backups, configs, ficheiros sensíveis).

**Modelo: Claude Sonnet 4.6 (Thinking)**

```python
# apps/api/scans/strategies/dir_bruteforce.py
# Usa gobuster ou fallback próprio em Python

import subprocess
import shutil
import requests
from pathlib import Path
from .base import BaseScanStrategy, FindingResult

SENSITIVE_PATHS = [
    # Admin panels
    "/admin", "/admin/", "/wp-admin", "/administrator",
    "/phpmyadmin", "/cpanel", "/plesk", "/webmail",
    # Configs e backups
    "/.env", "/.env.local", "/.env.production",
    "/config.php", "/config.yml", "/config.json",
    "/backup.zip", "/backup.sql", "/db.sql",
    "/database.sql", "/.git/config", "/.git/HEAD",
    # APIs e docs
    "/api", "/api/v1", "/swagger", "/swagger-ui.html",
    "/api-docs", "/openapi.json", "/graphql",
    # Ficheiros comuns
    "/robots.txt", "/sitemap.xml", "/.htaccess",
    "/web.config", "/crossdomain.xml",
    # Logs e debug
    "/logs", "/error.log", "/access.log",
    "/debug", "/test", "/staging",
    # Wordpress
    "/wp-config.php", "/wp-login.php", "/xmlrpc.php",
    # Laravel
    "/.env", "/storage/logs/laravel.log",
    # Django
    "/django-admin", "/static/admin",
]

SENSITIVE_EXTENSIONS = [".php~", ".bak", ".old", ".backup", ".orig", ".swp"]

class DirBruteforceStrategy(BaseScanStrategy):
    name = "dir_bruteforce"
    
    def execute(self, target: str, config: dict, scan_id: str) -> list[FindingResult]:
        self.log(scan_id, f"[dir_scan] Procurando ficheiros e directorias ocultas em {target}...", "info")
        self.log(scan_id, f"[dir_scan] Verificando {len(SENSITIVE_PATHS)} paths sensíveis...", "info")
        
        findings = []
        
        if shutil.which("gobuster"):
            findings = self._run_gobuster(target, scan_id)
        else:
            findings = self._run_python_scan(target, scan_id)
        
        self.log(
            scan_id,
            f"[dir_scan] Scan concluído. {len(findings)} recursos encontrados.",
            "success"
        )
        return findings
    
    def _run_python_scan(self, target: str, scan_id: str) -> list[FindingResult]:
        """Scan Python nativo sem gobuster."""
        findings = []
        target = target.rstrip("/")
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": "HackerScan-Security-Scanner/1.0"
        })
        
        for path in SENSITIVE_PATHS:
            url = f"{target}{path}"
            try:
                resp = session.get(url, timeout=5, allow_redirects=False)
                
                if resp.status_code in (200, 201, 204, 301, 302, 401, 403):
                    severity = self._classify_severity(path, resp.status_code)
                    self.log(
                        scan_id,
                        f"[dir_scan] [{resp.status_code}] {url}",
                        "finding" if severity in ("high", "critical") else "info"
                    )
                    findings.append(FindingResult(
                        title=f"Recurso sensível exposto: {path}",
                        type="exposed_resource",
                        severity=severity,
                        endpoint=url,
                        method="GET",
                        description=(
                            f"O recurso '{path}' respondeu com HTTP {resp.status_code}. "
                            + self._get_path_description(path)
                        ),
                        evidence=f"HTTP {resp.status_code} — {len(resp.content)} bytes",
                        remediation=self._get_remediation(path),
                        engine="dir_bruteforce",
                        metadata={
                            "status_code": resp.status_code,
                            "content_length": len(resp.content),
                        },
                    ))
            except requests.RequestException:
                continue
        
        return findings
    
    def _classify_severity(self, path: str, status_code: int) -> str:
        critical_paths = {"/.env", "/.git/config", "/config.php", "/db.sql", "/backup.sql"}
        high_paths = {"/admin", "/phpmyadmin", "/wp-admin", "/administrator"}
        
        if path in critical_paths and status_code == 200:
            return "critical"
        if path in high_paths and status_code in (200, 401):
            return "high"
        if status_code == 200:
            return "medium"
        return "info"
    
    def _get_path_description(self, path: str) -> str:
        descriptions = {
            "/.env": "Ficheiro de variáveis de ambiente pode conter credenciais, API keys e segredos.",
            "/.git/config": "Repositório Git exposto — código fonte pode ser descarregado.",
            "/phpmyadmin": "Interface de administração de base de dados exposta.",
            "/admin": "Painel de administração acessível publicamente.",
            "/backup.sql": "Backup da base de dados exposto — pode conter dados sensíveis.",
        }
        return descriptions.get(path, "Recurso potencialmente sensível encontrado.")
    
    def _get_remediation(self, path: str) -> str:
        remediations = {
            "/.env": "Remova o ficheiro .env do directório público e adicione ao .gitignore.",
            "/.git": "Bloqueie o acesso ao directório .git via configuração do servidor.",
            "/phpmyadmin": "Restrinja o acesso ao phpMyAdmin por IP ou remova-o de produção.",
            "/admin": "Proteja o painel admin com autenticação forte e restrição por IP.",
        }
        for key, remediation in remediations.items():
            if key in path:
                return remediation
        return "Restrinja o acesso a este recurso ou remova-o se não for necessário."
```

---

## ENGINE 6 — WEB SPIDERING

**O que faz:** crawl de todos os endpoints da aplicação,
descobre forms, parâmetros, endpoints de API não documentados.

**Modelo: Claude Sonnet 4.6 (Thinking)**

```python
# apps/api/scans/strategies/web_spider.py
# Usa requests + BeautifulSoup — sem playwright (mais leve)

import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from collections import deque
from .base import BaseScanStrategy, FindingResult

class WebSpiderStrategy(BaseScanStrategy):
    name = "web_spider"
    MAX_PAGES = 50  # limite para não sobrecarregar o target
    
    def execute(self, target: str, config: dict, scan_id: str) -> list[FindingResult]:
        self.log(scan_id, f"[spider] Iniciando crawl em {target}...", "info")
        self.log(scan_id, f"[spider] Máximo de {self.MAX_PAGES} páginas por scan.", "info")
        
        visited = set()
        queue = deque([target])
        findings = []
        base_domain = urlparse(target).netloc
        forms_found = []
        endpoints_found = []
        
        session = requests.Session()
        session.headers.update({"User-Agent": "HackerScan-Spider/1.0"})
        
        # Adicionar auth se configurada
        auth = config.get("auth", {})
        if auth.get("type") == "cookie":
            session.headers["Cookie"] = auth["cookie"]
        elif auth.get("type") == "bearer":
            session.headers["Authorization"] = f"Bearer {auth['token']}"
        
        while queue and len(visited) < self.MAX_PAGES:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)
            
            try:
                resp = session.get(url, timeout=10, allow_redirects=True)
                self.log(scan_id, f"[spider] Crawling: {url}", "info")
                
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Encontrar forms
                for form in soup.find_all("form"):
                    action = form.get("action", url)
                    method = form.get("method", "GET").upper()
                    inputs = [i.get("name") for i in form.find_all("input") if i.get("name")]
                    forms_found.append({
                        "url": urljoin(url, action),
                        "method": method,
                        "inputs": inputs,
                    })
                    self.log(
                        scan_id,
                        f"[spider] FORM encontrado: {method} {action} — inputs: {inputs}",
                        "info"
                    )
                
                # Encontrar links internos
                for link in soup.find_all("a", href=True):
                    href = urljoin(url, link["href"])
                    parsed = urlparse(href)
                    if parsed.netloc == base_domain and href not in visited:
                        queue.append(href)
                
                # Detectar endpoints de API em scripts
                for script in soup.find_all("script"):
                    if script.string:
                        import re
                        api_endpoints = re.findall(
                            r'["\'](/api/[^"\']+)["\']', script.string
                        )
                        for endpoint in api_endpoints:
                            endpoints_found.append(urljoin(target, endpoint))
                            self.log(
                                scan_id,
                                f"[spider] API endpoint detectado: {endpoint}",
                                "info"
                            )
            
            except requests.RequestException as e:
                self.log(scan_id, f"[spider] Erro em {url}: {e}", "error")
                continue
        
        # Criar findings
        if forms_found:
            findings.append(FindingResult(
                title=f"{len(forms_found)} formulários descobertos",
                type="forms_discovered",
                severity="info",
                endpoint=target,
                description=f"O spider encontrou {len(forms_found)} formulários HTML "
                            f"em {len(visited)} páginas crawladas.",
                remediation="Verifique se todos os formulários têm protecção CSRF "
                            "e validação adequada de inputs.",
                engine="web_spider",
                metadata={
                    "forms": forms_found[:20],
                    "pages_crawled": len(visited),
                },
            ))
        
        if endpoints_found:
            findings.append(FindingResult(
                title=f"{len(endpoints_found)} endpoints de API descobertos",
                type="api_endpoints_discovered",
                severity="info",
                endpoint=target,
                description=f"Endpoints de API encontrados em código JavaScript: "
                            f"{', '.join(endpoints_found[:10])}",
                remediation="Verifique se todos os endpoints de API têm autenticação "
                            "e autorização adequadas.",
                engine="web_spider",
                metadata={"endpoints": endpoints_found},
            ))
        
        self.log(
            scan_id,
            f"[spider] Crawl concluído. {len(visited)} páginas, "
            f"{len(forms_found)} forms, {len(endpoints_found)} API endpoints.",
            "success"
        )
        return findings
```

---

## ENGINE 7 — AUTHENTICATED SCANNING

**O que faz:** permite fazer scan com sessão autenticada,
testando endpoints que exigem login.

**Modelo: Claude Opus 4.6 (Thinking)**
Autenticação tem edge cases de segurança.

```python
# apps/api/scans/strategies/auth_scan.py

import requests
from .base import BaseScanStrategy, FindingResult

class AuthScanStrategy(BaseScanStrategy):
    name = "auth_scan"
    
    def execute(self, target: str, config: dict, scan_id: str) -> list[FindingResult]:
        auth = config.get("auth", {})
        if not auth:
            self.log(scan_id, "[auth_scan] Nenhuma configuração de auth fornecida.", "info")
            return []
        
        self.log(scan_id, f"[auth_scan] Iniciando scan autenticado em {target}...", "info")
        
        findings = []
        session = requests.Session()
        
        # Configurar autenticação
        auth_type = auth.get("type")
        if auth_type == "bearer":
            session.headers["Authorization"] = f"Bearer {auth['token']}"
            self.log(scan_id, "[auth_scan] Auth: Bearer token configurado.", "info")
        elif auth_type == "cookie":
            session.headers["Cookie"] = auth["cookie"]
            self.log(scan_id, "[auth_scan] Auth: Cookie de sessão configurado.", "info")
        elif auth_type == "basic":
            session.auth = (auth["username"], auth["password"])
            self.log(scan_id, "[auth_scan] Auth: HTTP Basic configurado.", "info")
        elif auth_type == "form_login":
            # Login via form HTML
            success = self._do_form_login(session, auth, scan_id)
            if not success:
                self.log(scan_id, "[auth_scan] ERRO: Login via form falhou.", "error")
                return []
        
        # Testar IDOR (Insecure Direct Object Reference)
        findings.extend(self._test_idor(session, target, scan_id))
        
        # Testar privilege escalation
        findings.extend(self._test_privilege_escalation(session, target, scan_id))
        
        # Testar session management
        findings.extend(self._test_session_management(session, target, auth, scan_id))
        
        self.log(
            scan_id,
            f"[auth_scan] Scan autenticado concluído. {len(findings)} problemas encontrados.",
            "success"
        )
        return findings
    
    def _do_form_login(self, session, auth: dict, scan_id: str) -> bool:
        try:
            resp = session.post(
                auth["login_url"],
                data={
                    auth.get("username_field", "username"): auth["username"],
                    auth.get("password_field", "password"): auth["password"],
                },
                timeout=10,
                allow_redirects=True,
            )
            # Verificar se login foi bem sucedido
            success_indicator = auth.get("success_indicator", "")
            if success_indicator and success_indicator in resp.text:
                self.log(scan_id, "[auth_scan] Login bem sucedido.", "success")
                return True
            if resp.status_code in (200, 302):
                self.log(scan_id, "[auth_scan] Login aparentemente bem sucedido.", "info")
                return True
            return False
        except Exception as e:
            self.log(scan_id, f"[auth_scan] Erro no login: {e}", "error")
            return False
    
    def _test_idor(self, session, target: str, scan_id: str) -> list[FindingResult]:
        """Testa IDOR em IDs sequenciais."""
        self.log(scan_id, "[auth_scan] Testando IDOR em endpoints comuns...", "info")
        findings = []
        
        idor_patterns = [
            "/api/users/1", "/api/users/2",
            "/api/profile/1", "/api/orders/1",
            "/api/documents/1", "/api/files/1",
        ]
        
        for pattern in idor_patterns:
            url = f"{target.rstrip('/')}{pattern}"
            try:
                resp = session.get(url, timeout=5)
                if resp.status_code == 200 and len(resp.content) > 10:
                    self.log(scan_id, f"[auth_scan] Possível IDOR: {url}", "finding")
                    findings.append(FindingResult(
                        title=f"Possível IDOR em {pattern}",
                        type="idor",
                        severity="high",
                        endpoint=url,
                        method="GET",
                        description=f"O endpoint {pattern} retornou dados sem verificar "
                                    "se o utilizador tem permissão para aceder a este recurso.",
                        remediation="Implemente verificação de autorização em todos os endpoints "
                                    "que acedem a recursos por ID. Use UUIDs em vez de IDs sequenciais.",
                        cvss_score=7.5,
                        cwe_id="CWE-639",
                        engine="auth_scan",
                    ))
            except Exception:
                continue
        
        return findings
    
    def _test_privilege_escalation(self, session, target: str, scan_id: str) -> list[FindingResult]:
        """Testa acesso a endpoints de admin sem permissão."""
        findings = []
        admin_endpoints = [
            "/api/admin", "/api/v1/admin", "/api/users",
            "/api/admin/users", "/api/management",
        ]
        for endpoint in admin_endpoints:
            url = f"{target.rstrip('/')}{endpoint}"
            try:
                resp = session.get(url, timeout=5)
                if resp.status_code == 200:
                    self.log(scan_id, f"[auth_scan] Endpoint admin acessível: {url}", "finding")
                    findings.append(FindingResult(
                        title=f"Endpoint administrativo acessível",
                        type="privilege_escalation",
                        severity="critical",
                        endpoint=url,
                        description=f"O endpoint {endpoint} está acessível sem privilégios admin.",
                        remediation="Adicione verificação de role admin em todos os endpoints administrativos.",
                        cvss_score=9.1,
                        cwe_id="CWE-269",
                        engine="auth_scan",
                    ))
            except Exception:
                continue
        return findings
    
    def _test_session_management(
        self, session, target: str, auth: dict, scan_id: str
    ) -> list[FindingResult]:
        """Testa gestão de sessão — token expiry, logout efectivo."""
        findings = []
        self.log(scan_id, "[auth_scan] Testando gestão de sessão...", "info")
        # Verificar se o token JWT tem expiração adequada
        token = auth.get("token", "")
        if token and "." in token:
            try:
                import base64, json as _json
                payload = token.split(".")[1]
                payload += "=" * (4 - len(payload) % 4)  # padding
                decoded = _json.loads(base64.b64decode(payload))
                exp = decoded.get("exp")
                iat = decoded.get("iat")
                if exp and iat:
                    lifetime = exp - iat
                    if lifetime > 86400 * 30:  # mais de 30 dias
                        findings.append(FindingResult(
                            title="Token JWT com expiração excessiva",
                            type="weak_session_management",
                            severity="medium",
                            endpoint=target,
                            description=f"O token JWT tem uma vida útil de {lifetime // 86400} dias, "
                                        "o que aumenta o risco em caso de comprometimento.",
                            remediation="Configure tokens JWT com expiração máxima de 15 minutos "
                                        "para access tokens e 7 dias para refresh tokens.",
                            cvss_score=5.4,
                            cwe_id="CWE-613",
                            engine="auth_scan",
                        ))
            except Exception:
                pass
        return findings
```

---

## MODIFICAÇÕES NECESSÁRIAS

### 1. requirements/base.txt — adicionar

```
sslyze>=5.0.0
beautifulsoup4>=4.12.0
```

### 2. docker-compose.yml — instalar tools no container

```yaml
# No serviço api, adicionar ao Dockerfile ou entrypoint:
# RUN apt-get install -y nmap gobuster
# RUN go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
# RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
```

### 3. scans/strategies/\_\_init\_\_.py — registar engines

```python
from .nuclei_scan import NucleiScanStrategy
from .subfinder_scan import SubfinderScanStrategy
from .full_port_scan import FullPortScanStrategy
from .tls_cipher_scan import TLSCipherScanStrategy
from .dir_bruteforce import DirBruteforceStrategy
from .web_spider import WebSpiderStrategy
from .auth_scan import AuthScanStrategy

ALL_STRATEGIES = [
    NucleiScanStrategy,
    SubfinderScanStrategy,
    FullPortScanStrategy,
    TLSCipherScanStrategy,
    DirBruteforceStrategy,
    WebSpiderStrategy,
    AuthScanStrategy,
]
```

### 4. scan_types — adicionar ao modelo Scan

```python
class ScanType(models.TextChoices):
    QUICK = "quick", "Quick Scan (headers + SSL)"
    FULL = "full", "Full Scan (todos os engines)"
    VULN = "vuln", "Vulnerability Scan (Nuclei)"
    RECON = "recon", "Reconnaissance (subfinder + spider)"
    AUTHENTICATED = "auth", "Authenticated Scan"
```

---

## FRONTEND — ACTUALIZAR UI DO SCAN

### Selector de scan type no dashboard

```typescript
// Adicionar ao form de criação de scan
const SCAN_TYPES = [
  { value: "quick", label: "Quick Scan", time: "~30s",
    description: "Headers, SSL, portas comuns" },
  { value: "full",  label: "Full Scan",  time: "~5min",
    description: "Todos os engines activos" },
  { value: "vuln",  label: "Vuln Scan",  time: "~3min",
    description: "CVEs e vulnerabilidades com Nuclei" },
  { value: "recon", label: "Recon",      time: "~2min",
    description: "Subdomínios, endpoints, spidering" },
  { value: "auth",  label: "Auth Scan",  time: "~4min",
    description: "Scan com credenciais autenticadas" },
]
```

---

## TESTES OBRIGATÓRIOS

```python
# tests/test_strategies.py

def test_nuclei_engine_is_available_or_graceful_fallback():
    """Se Nuclei não está instalado, retorna [] sem crash."""

def test_full_port_scan_blocks_private_ips():
    """Nunca faz scan de 192.168.x.x ou 10.x.x.x."""

def test_dir_bruteforce_classifies_env_file_as_critical():
    """/.env com HTTP 200 deve retornar severity=critical."""

def test_web_spider_stays_in_same_domain():
    """Spider não segue links externos ao domínio do target."""

def test_auth_scan_decodes_jwt_expiry():
    """Token com >30 dias retorna finding medium."""

def test_tls_scan_detects_weak_protocols():
    """SSLv3 detectado retorna severity=critical."""
```

---

## ORDEM DE IMPLEMENTAÇÃO

```
1. Full Port Scan (substitui port_scan.py actual)    → Sonnet
2. Nuclei integration                                → Opus
3. TLS Cipher Scan (sslyze)                          → Sonnet
4. Subfinder + crt.sh fallback                       → Sonnet
5. Directory Bruteforce                              → Sonnet
6. Web Spider                                        → Sonnet
7. Authenticated Scanning                            → Opus
8. Actualizar __init__.py com todos os engines       → Flash
9. Actualizar docker-compose.yml                     → GPT-OSS 120B
10. Actualizar frontend — scan type selector         → Gemini Pro Low
11. Testes de todos os engines                       → Sonnet
```

---

## VERIFICAÇÃO FINAL — SCORE ESPERADO

```
Antes (v1):  Ports ✅  Headers ✅  SSL ✅  Vulns ❌  Web ❌  Subdoms ❌
             Score: 6.5

Depois (v2): Ports ✅  Headers ✅  SSL ✅  Vulns ✅  Web ✅  Subdoms ✅
             Score: 9.0+  (competitivo com Intruder.io e Detectify)
```

Lista os ficheiros antes de criar qualquer código.
Aguarda confirmação. Depois implementa por ordem.
