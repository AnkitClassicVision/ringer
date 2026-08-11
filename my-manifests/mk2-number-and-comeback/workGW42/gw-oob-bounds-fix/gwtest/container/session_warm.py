#!/usr/bin/env python3
"""Keep an EyeCloud session warm with the Stack 2 Playwright login pattern."""

from __future__ import annotations

import asyncio
import logging
import os

LOGIN_USERNAME_SELECTOR = "#p_username"
LOGIN_PASSWORD_SELECTOR = "#p_password"
LOGIN_SUBMIT_SELECTOR = "#submitbutton"
DEFAULT_NAVIGATION_TIMEOUT_MS = 30_000

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cvc-session-warm")


async def login_to_eyecloud(page, *, login_url: str, username: str, password: str, timeout_ms: int) -> None:
    log.info("login_navigate")
    await page.goto(login_url, timeout=timeout_ms)
    for selector in (LOGIN_USERNAME_SELECTOR, LOGIN_PASSWORD_SELECTOR, LOGIN_SUBMIT_SELECTOR):
        await page.wait_for_selector(selector, timeout=timeout_ms)
    await page.fill(LOGIN_USERNAME_SELECTOR, username)
    await page.fill(LOGIN_PASSWORD_SELECTOR, password)
    log.info("login_submit")
    await page.click(LOGIN_SUBMIT_SELECTOR)
    await page.wait_for_load_state("networkidle", timeout=timeout_ms)
    if "/login" in (getattr(page, "url", "") or "").lower():
        raise RuntimeError("login submitted but page is still on the login URL")


async def select_store(page, *, store_id: int, timeout_ms: int) -> None:
    log.info("store_select_navigate")
    await page.wait_for_function("() => typeof window.ss === 'function'", timeout=timeout_ms)
    await page.evaluate(f"() => {{ window.ss({int(store_id)}); }}")
    log.info("store_select_submit")
    await page.wait_for_load_state("networkidle", timeout=timeout_ms)


async def warm_forever() -> None:
    login_url = os.environ["ECP_LOGIN_URL"]
    username = os.environ["ECP_LOGIN_USERNAME"]
    password = os.environ["ECP_LOGIN_PASSWORD"]
    store_id = int(os.environ["ECP_STORE_ID"])
    refresh_s = int(os.environ.get("ECP_SESSION_REFRESH_S", "1800"))
    timeout_ms = int(os.environ.get("ECP_NAVIGATION_TIMEOUT_MS", str(DEFAULT_NAVIGATION_TIMEOUT_MS)))

    from playwright.async_api import async_playwright  # type: ignore[import-not-found]

    while True:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                try:
                    await login_to_eyecloud(
                        page,
                        login_url=login_url,
                        username=username,
                        password=password,
                        timeout_ms=timeout_ms,
                    )
                    await select_store(page, store_id=store_id, timeout_ms=timeout_ms)
                    log.info("session_warm_ready")
                    while True:
                        await asyncio.sleep(refresh_s)
                        try:
                            await page.reload(wait_until="networkidle", timeout=timeout_ms)
                            if "/login" in (getattr(page, "url", "") or "").lower():
                                raise RuntimeError("session stale")
                            log.info("session_warm_ok")
                        except Exception as exc:
                            log.info("session_warm_stale: %s", type(exc).__name__)
                            break
                finally:
                    await browser.close()
        except Exception as exc:
            log.info("session_warm_login_failed: %s", type(exc).__name__)
            await asyncio.sleep(min(refresh_s, 300))


if __name__ == "__main__":
    required = ("ECP_LOGIN_URL", "ECP_LOGIN_USERNAME", "ECP_LOGIN_PASSWORD", "ECP_STORE_ID")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit("missing session warm env: " + ",".join(missing))
    asyncio.run(warm_forever())
