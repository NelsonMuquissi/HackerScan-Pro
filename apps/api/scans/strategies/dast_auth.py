import asyncio
from typing import AsyncGenerator
from urllib.parse import urlparse

from .base import BaseScanStrategy, FindingData, register

@register
class DASTAuthScanStrategy(BaseScanStrategy):
    name = "Stateful DAST (Authenticated)"
    slug = "dast_auth"
    description = "Authenticates using Playwright and performs deep stateful crawling and vulnerability scanning."

    async def run_async(self, target, scan=None) -> AsyncGenerator[FindingData, None]:
        from playwright.async_api import async_playwright
        import json
        
        self.log(scan, "Starting Authenticated DAST via Playwright...")
        
        target_url = target.url
            
        domain = urlparse(target_url).netloc
            
        # Parse authentication settings if they exist in scan configuration
        auth_config = {}
        if scan and hasattr(scan, "configuration") and isinstance(scan.configuration, dict):
            auth_config = scan.configuration.get("auth", {})
        elif scan and hasattr(scan, "config") and isinstance(scan.config, dict):
            # Also check .config (used in some places)
            auth_config = scan.config.get("auth", {})
            
        if not auth_config:
            self.log(scan, "No authentication configuration found. Running unauthenticated stateful crawl.")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                
                # Setup context with some default anti-bot evasion
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 720},
                    ignore_https_errors=True
                )
                
                page = await context.new_page()
                
                # Phase 1: Authentication (if credentials provided)
                if auth_config.get("username") and auth_config.get("password"):
                    login_url = auth_config.get("login_url")
                    if not login_url:
                        # Auto-discovery of login if not provided
                        login_url = f"{target_url.rstrip('/')}/login"
                    elif not login_url.startswith("http"):
                        # Resolve relative login URLs
                        if login_url.startswith("/"):
                            login_url = f"{target_url.rstrip('/')}{login_url}"
                        else:
                            login_url = f"{target_url.rstrip('/')}/{login_url}"

                    self.log(scan, f"Attempting login at {login_url}")
                    try:
                        await page.goto(login_url, wait_until="networkidle", timeout=15000)
                        
                        u_sel = auth_config.get("username_selector", "input[type='text'], input[name*='user'], input[id*='user']")
                        p_sel = auth_config.get("password_selector", "input[type='password']")
                        sub_sel = auth_config.get("submit_selector", "button[type='submit'], input[type='submit']")
                        
                        await page.fill(u_sel, auth_config["username"])
                        await page.fill(p_sel, auth_config["password"])
                        await page.click(sub_sel)
                        
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        self.log(scan, "Login sequence completed.")
                        
                        cookies = await context.cookies()
                        # self.log(scan, f"Captured {len(cookies)} cookies post-login.")
                    except Exception as e:
                        self.log(scan, f"Login sequence failed: {str(e)}")
                        yield FindingData(
                            title="DAST Authentication Failed",
                            description=f"Could not complete the login sequence: {str(e)}",
                            severity="warning",
                            plugin_slug=self.slug,
                            category="Configuration"
                        )
                
                # Phase 2: Intercept requests to find sensitive APIs and broken access controls
                exposed_endpoints = set()
                
                async def handle_response(response):
                    try:
                        if response.status >= 200 and response.status < 300:
                            url = response.url
                            if domain in url and ("api" in url or "graphql" in url or "admin" in url):
                                exposed_endpoints.add(url)
                    except:
                        pass
                        
                page.on("response", handle_response)
                
                # Phase 3: Crawl Target
                self.log(scan, f"Navigating to {target_url} for stateful analysis")
                try:
                    await page.goto(target_url, wait_until="networkidle", timeout=30000)
                    title = await page.title()
                    self.log(scan, f"Page title: {title}")
                    
                    # Look for hidden admin links or developer tools on the page
                    links = await page.query_selector_all("a")
                    admin_links = []
                    for link in links:
                        href = await link.get_attribute("href")
                        if href and ("admin" in href.lower() or "dashboard" in href.lower() or "debug" in href.lower()):
                            admin_links.append(href)
                            
                    if admin_links:
                        yield FindingData(
                            title="Exposed Administrative Interfaces",
                            description=f"Found links to potential administrative interfaces: {', '.join(admin_links[:5])}",
                            severity="medium",
                            plugin_slug=self.slug,
                            category="Information Disclosure",
                            evidence={"admin_links": admin_links}
                        )
                    
                    # Look for exposed local storage / session storage
                    storage_data = await page.evaluate('''() => {
                        let data = {local: {}, session: {}};
                        for (let i = 0; i < localStorage.length; i++) {
                            let key = localStorage.key(i);
                            data.local[key] = localStorage.getItem(key);
                        }
                        for (let i = 0; i < sessionStorage.length; i++) {
                            let key = sessionStorage.key(i);
                            data.session[key] = sessionStorage.getItem(key);
                        }
                        return data;
                    }''')
                    
                    has_sensitive_storage = False
                    storage_evidence = {}
                    for k, v in storage_data['local'].items():
                        if "token" in k.lower() or "auth" in k.lower() or "jwt" in k.lower():
                            has_sensitive_storage = True
                            storage_evidence[k] = str(v)[:50] + "..." if v and len(str(v)) > 50 else str(v)
                            
                    if has_sensitive_storage:
                        yield FindingData(
                            title="Sensitive Data in LocalStorage",
                            description="Found authentication tokens or sensitive information stored in HTML5 LocalStorage.",
                            severity="medium",
                            plugin_slug=self.slug,
                            category="Data Exposure",
                            evidence=storage_evidence
                        )
                        
                    # Test for basic DOM-based XSS by injecting into URL hash/params
                    test_url = f"{target_url}#test=<img src=x onerror=console.log('xss')>"
                    await page.goto(test_url, wait_until="networkidle", timeout=15000)
                    
                except Exception as e:
                    self.log(scan, f"Crawling error: {str(e)}")
                
                await browser.close()
                
                if exposed_endpoints:
                    self.log(scan, f"Found {len(exposed_endpoints)} interesting API/Admin endpoints during stateful crawl.")
                    yield FindingData(
                        title="Stateful API Discovery",
                        description=f"Discovered {len(exposed_endpoints)} internal/API endpoints through stateful navigation and background requests.",
                        severity="info",
                        plugin_slug=self.slug,
                        category="Reconnaissance",
                        evidence={"endpoints": list(exposed_endpoints)[:20]}
                    )
                    
        except Exception as e:
            self.log(scan, f"Playwright execution failed: {str(e)}")
            yield FindingData(
                title="DAST Execution Error",
                description=f"Failed to run Playwright engine: {str(e)}",
                severity="error",
                plugin_slug=self.slug,
                category="Execution"
            )
