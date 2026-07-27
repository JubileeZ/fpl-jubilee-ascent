import os
import base64
import json
import time
import logging
from pathlib import Path
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Walk up from this file's directory clients/fpl_auth.py to project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOKEN_CACHE_PATH = PROJECT_ROOT / "data" / "session_token.json"


def is_jwt_expired(token: str) -> bool:
    """Check if the JWT token is expired or close to expiring (within a 5-minute window)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return True
        payload_b64 = parts[1]
        # Pad payload if necessary for base64 decoding
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload_json = base64.b64decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)
        exp = payload.get("exp", 0)
        # Check if expired (with a 5-minute safety buffer)
        return time.time() > (exp - 300)
    except Exception as e:
        logger.warning(f"Error checking token expiration: {e}")
        return True


async def async_login() -> str:
    """Automate login via Playwright to retrieve the x-api-authorization JWT token."""
    email = os.getenv("FPL_EMAIL")
    password = os.getenv("FPL_PASSWORD")

    if not email or not password:
        raise ValueError("FPL_EMAIL and FPL_PASSWORD environment variables must be set.")

    headless_env = os.getenv("FPL_HEADLESS", "true").lower() in ("true", "1", "yes")
    logger.info(f"Initializing browser login (headless={headless_env})...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless_env)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        found_auth = None
        async def handle_request(request):
            nonlocal found_auth
            if "/api/" in request.url:
                try:
                    headers = await request.all_headers()
                    auth = headers.get("x-api-authorization") or headers.get("X-Api-Authorization")
                    if auth:
                        logger.info("x-api-authorization header captured!")
                        found_auth = auth.replace("Bearer ", "").strip()
                except Exception:
                    pass

        page.on("request", handle_request)

        async def purge_onetrust():
            try:
                await page.evaluate("""() => {
                    const ids = ['onetrust-consent-sdk', 'onetrust-banner-sdk'];
                    ids.forEach(id => { const el = document.getElementById(id); if (el) el.remove(); });
                    document.querySelectorAll('.onetrust-pc-dark-filter').forEach(el => el.remove());
                }""")
            except Exception:
                pass

        logger.info("Navigating to fantasy.premierleague.com...")
        await page.goto("https://fantasy.premierleague.com/en/", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        await purge_onetrust()

        # Click 'Log in' button
        logger.info("Clicking Log in button...")
        login_btn = page.locator('button:has-text("Log in"), a:has-text("Log in")').first
        await login_btn.click(force=True)

        # Wait for redirect to account.premierleague.com
        logger.info("Waiting for account.premierleague.com authorization page...")
        await page.wait_for_url("**/account.premierleague.com/**", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)
        await purge_onetrust()

        # Fill credentials
        logger.info("Filling credentials...")
        await page.locator("#username").wait_for(state="visible", timeout=10000)
        await page.locator("#username").fill(email)
        await page.locator("#password").fill(password)

        # Submit form with force=True to prevent OneTrust overlay interception
        logger.info("Submitting login form...")
        signon_btn = page.locator('button[data-skbuttonvalue="SIGNON"], #btnSignIn').first
        await signon_btn.click(force=True)

        await page.wait_for_timeout(2000)
        # Check for credential errors on page
        body_text = await page.locator("body").inner_text()
        if "Invalid username and/or password" in body_text:
            await browser.close()
            raise ValueError("FPL login failed: Invalid username and/or password in environment configuration.")

        # Wait for redirect back to fantasy domain
        logger.info("Waiting for redirect back to fantasy.premierleague.com...")
        try:
            await page.wait_for_url("**/fantasy.premierleague.com/**", wait_until="domcontentloaded", timeout=15000)
        except Exception:
            logger.info("Direct wait_for_url completed or timed out, navigating explicitly to /transfers...")

        # Trigger API call by navigating to /transfers
        logger.info("Navigating to /transfers to trigger authenticated API call...")
        await page.goto("https://fantasy.premierleague.com/transfers", wait_until="domcontentloaded")

        for _ in range(15):
            if found_auth:
                break
            await page.wait_for_timeout(1000)

        await browser.close()

        if not found_auth:
            raise RuntimeError("Failed to capture 'x-api-authorization' bearer token during login flow.")

        logger.info("Successfully captured session token.")
        return found_auth


async def get_jwt_token(force_refresh: bool = False) -> str:
    """Get a valid FPL session token, retrieving from environment variable, local cache, or Playwright login."""
    # 1. Tier 1: Check FPL_TOKEN env var
    env_token = os.getenv("FPL_TOKEN")
    if env_token:
        # Strip Bearer if passed in with prefix
        if env_token.lower().startswith("bearer "):
            env_token = env_token[7:].strip()
        if not is_jwt_expired(env_token):
            logger.info("Using valid FPL_TOKEN from environment.")
            return env_token
        else:
            logger.warning("FPL_TOKEN from environment is expired.")

    # 2. Tier 2: Check cached token
    if not force_refresh and TOKEN_CACHE_PATH.exists():
        try:
            with open(TOKEN_CACHE_PATH, "r") as f:
                data = json.load(f)
                token = data.get("token")
                if token and not is_jwt_expired(token):
                    logger.info("Using cached FPL session token.")
                    return token
        except Exception as e:
            logger.warning(f"Failed to read cached token: {e}")

    # 3. Tier 3: Playwright Login via Email/Password
    email = os.getenv("FPL_EMAIL")
    password = os.getenv("FPL_PASSWORD")

    if not email or not password:
        raise ValueError(
            "FPL authentication missing. Please provide FPL_TOKEN (bearer token) OR "
            "both FPL_EMAIL and FPL_PASSWORD in environment variables."
        )

    # Fetch new token via Playwright login
    token = await async_login()

    # Cache token
    try:
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_CACHE_PATH, "w") as f:
            json.dump({"token": token, "cached_at": time.time()}, f)
        logger.info(f"Cached new FPL session token to {TOKEN_CACHE_PATH}")
    except Exception as e:
        logger.warning(f"Failed to cache token: {e}")

    return token
