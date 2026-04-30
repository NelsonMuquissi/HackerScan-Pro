import httpx
import re
from typing import Any, Dict, Optional, Tuple

def dump_httpx_request(request: httpx.Request) -> str:
    """Returns a string representation of the HTTP request."""
    lines = [f"{request.method} {request.url.raw_path.decode()} HTTP/1.1"]
    lines.append(f"Host: {request.url.host}")
    for name, value in request.headers.items():
        lines.append(f"{name}: {value}")
    
    lines.append("")
    if request.content:
        try:
            lines.append(request.content.decode())
        except UnicodeDecodeError:
            lines.append(f"<binary data: {len(request.content)} bytes>")
            
    return "\n".join(lines)

def dump_httpx_response(response: httpx.Response, max_body: int = 2000) -> str:
    """Returns a string representation of the HTTP response."""
    lines = [f"HTTP/1.1 {response.status_code} {response.reason_phrase}"]
    for name, value in response.headers.items():
        lines.append(f"{name}: {value}")
    
    lines.append("")
    if response.text:
        body = response.text
        if len(body) > max_body:
            body = body[:max_body] + f"\n\n[... truncated {len(body) - max_body} characters ...]"
        lines.append(body)
        
    return "\n".join(lines)

def generate_curl_command(request: httpx.Request) -> str:
    """Generates a curl command string from an httpx.Request object."""
    parts = ["curl -i -X", request.method]
    
    for name, value in request.headers.items():
        # Avoid redundant headers that curl adds automatically or are internal
        if name.lower() in ["content-length", "host"]:
            continue
        parts.append(f'-H "{name}: {value}"')
    
    if request.content:
        try:
            body = request.content.decode()
            # Escape double quotes for shell
            body = body.replace('"', '\\"')
            parts.append(f'--data "{body}"')
        except UnicodeDecodeError:
            parts.append("<binary content>")
            
    parts.append(f'"{request.url}"')
    return " ".join(parts)

def make_evidence_request(
    url: str, 
    method: str = "GET", 
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    content: Any = None,
    timeout: int = 10,
    follow_redirects: bool = True,
    verify: bool = False
) -> Tuple[Optional[httpx.Response], str, str, str]:
    """
    Makes a request and returns (response, request_dump, response_dump, curl_command).
    Used to standardize evidence collection across strategies.
    """
    if headers is None:
        headers = {"User-Agent": "HackerScan-Pro/1.0 (Security Audit)"}
    
    req_dump = ""
    res_dump = ""
    poc = ""
    response = None

    try:
        with httpx.Client(verify=verify, timeout=timeout, follow_redirects=follow_redirects) as client:
            request = client.build_request(method, url, params=params, headers=headers, content=content)
            req_dump = dump_httpx_request(request)
            poc = generate_curl_command(request)
            
            response = client.send(request)
            res_dump = dump_httpx_response(response)
            
    except Exception as e:
        res_dump = f"Request failed: {str(e)}"
    
    return response, req_dump, res_dump, poc
