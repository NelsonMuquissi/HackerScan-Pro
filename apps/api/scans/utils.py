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
    
    # Sanitize URL: remove control characters and newlines
    url = "".join(char for char in url if ord(char) >= 32).strip()
    
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

async def make_evidence_request_async(
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
    Asynchronous version of make_evidence_request.
    Makes a request and returns (response, request_dump, response_dump, curl_command).
    """
    if headers is None:
        headers = {"User-Agent": "HackerScan-Pro/1.0 (Security Audit)"}
    
    # Sanitize URL: remove control characters and newlines
    url = "".join(char for char in url if ord(char) >= 32).strip()
    
    req_dump = ""
    res_dump = ""
    poc = ""
    response = None

    try:
        async with httpx.AsyncClient(verify=verify, timeout=timeout, follow_redirects=follow_redirects) as client:
            request = client.build_request(method, url, params=params, headers=headers, content=content)
            req_dump = dump_httpx_request(request)
            poc = generate_curl_command(request)
            
            response = await client.send(request)
            res_dump = dump_httpx_response(response)
            
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        # Handle DNS/Connection errors specifically to avoid long hangs or noisy logs
        error_msg = str(e)
        if "gaierror" in error_msg or "Name or service not known" in error_msg:
            res_dump = "Connection failed: DNS resolution error (gaierror). The host does not exist or DNS is unreachable."
        else:
            res_dump = f"Connection failed: {error_msg}"
    except Exception as e:
        res_dump = f"Request failed: {str(e)}"
    
    return response, req_dump, res_dump, poc

async def check_dns_resolution_async(hostname: str) -> bool:
    """
    Checks if a hostname resolves to an IP address asynchronously.
    Helps prevent massive connection timeouts for non-existent bucket domains.
    """
    import socket
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        await loop.getaddrinfo(hostname, None)
        return True
    except socket.gaierror:
        return False
    except Exception:
        return False

async def take_screenshot_async(url: str, wait_for: Optional[str] = None) -> Optional[bytes]:
    """
    Takes a screenshot of the given URL using Playwright.
    Wait for a specific selector if provided.
    Returns the screenshot as bytes.
    """
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1280, "height": 720})
            
            # Use a realistic User-Agent
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            })
            
            await page.goto(url, timeout=30000, wait_until="networkidle")
            
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=5000)
                except:
                    pass
            
            screenshot = await page.screenshot(type="jpeg", quality=80)
            await browser.close()
            return screenshot
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Screenshot failed for {url}: {e}")
    return None
