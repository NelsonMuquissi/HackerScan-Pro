import pytest
import asyncio
from playwright.async_api import async_playwright
import os

BASE_URL = os.getenv('HACKERSCAN_BASE_URL', 'http://localhost:8000')

@pytest.fixture(scope='session')
async def browser_context():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        yield context
        await context.close()
        await browser.close()

@pytest.mark.asyncio
async def test_scan_ui(browser_context, tmp_path_factory):
    page = await browser_context.new_page()
    # Login
    await page.goto(f"{BASE_URL}/login/")
    await page.fill('input[name="email"]', os.getenv('TEST_USER_EMAIL', 'admin@example.com'))
    await page.fill('input[name="password"]', os.getenv('TEST_USER_PASSWORD', 'password123'))
    await page.click('text=Login')
    await page.wait_for_load_state('networkidle')

    # Start a scan via UI (example: web scan)
    await page.goto(f"{BASE_URL}/scans/")
    await page.click('text="Start New Scan"')
    await page.select_option('select[name="type"]', 'web')
    await page.fill('input[name="target"]', 'example.com')
    await page.click('text=Submit')

    # Wait for completion indicator
    await page.wait_for_selector('text=Completed', timeout=60000)

    # Capture screenshot
    artifacts_dir = tmp_path_factory.mktemp('artifacts')
    screenshot_path = artifacts_dir / 'web_scan_ui.png'
    await page.screenshot(path=str(screenshot_path))
    await page.close()
    # Ensure screenshot exists (pytest will fail if not)
    assert screenshot_path.exists()
