from __future__ import annotations

import asyncio
import random
import re
import shutil
import ssl
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger

from bot.config import get_settings
from bot.parser.http_client import USER_AGENTS, get_rate_limiter

# On some Python installs (notably macOS Python.org 3.14) the stdlib urllib
# lacks CA certs, which breaks undetected_chromedriver's chromedriver download.
# Force urllib/ssl to use certifi's CA bundle so the patcher can fetch chromedriver.
try:
    import certifi

    ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())
except Exception:  # pragma: no cover - certifi missing or ssl unavailable
    pass

_uc: Any = None
_driver: Any = None
_lock = asyncio.Lock()
_request_count = 0
_MAX_REQUESTS_BEFORE_RESTART = 50


def _import_uc() -> Any:
    global _uc
    if _uc is None:
        import undetected_chromedriver as uc  # type: ignore

        _uc = uc
    return _uc


def _detect_chrome_major() -> int | None:
    for cmd in (("chromium", "--version"), ("chromium-browser", "--version"), ("google-chrome", "--version")):
        try:
            out = subprocess.check_output(list(cmd), stderr=subprocess.DEVNULL, text=True)
            m = re.search(r"(\d+)\.", out)
            if m:
                return int(m.group(1))
        except Exception:
            continue
    return None


def _create_driver() -> Any:
    uc = _import_uc()
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    for path in ("/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if Path(path).exists():
            options.binary_location = path
            break

    kwargs: dict[str, Any] = {"options": options}
    major = _detect_chrome_major()
    if major is not None:
        kwargs["version_main"] = major
    # Prefer a system chromedriver if present (Linux package or macOS brew).
    cd_path = shutil.which("chromedriver")
    if cd_path:
        kwargs["driver_executable_path"] = cd_path
    elif Path("/usr/bin/chromedriver").exists():
        kwargs["driver_executable_path"] = "/usr/bin/chromedriver"

    driver = uc.Chrome(**kwargs)
    driver.set_page_load_timeout(int(get_settings().parser_timeout_seconds))
    return driver


def _get_driver_sync() -> Any:
    global _driver, _request_count
    if _driver is None or _request_count >= _MAX_REQUESTS_BEFORE_RESTART:
        if _driver is not None:
            try:
                _driver.quit()  # type: ignore[union-attr]
            except Exception:
                pass
            _driver = None
        logger.debug("Creating Selenium driver (requests={})", _request_count)
        _driver = _create_driver()
        _request_count = 0
    else:
        try:
            _driver.current_url  # type: ignore[union-attr]
        except Exception:
            logger.warning("Selenium driver dead, recreating")
            try:
                _driver.quit()  # type: ignore[union-attr]
            except Exception:
                pass
            _driver = _create_driver()
            _request_count = 0
    return _driver


def _looks_like_challenge(html: str) -> bool:
    return bool(html) and "<title>Verification</title>" in html


def _fetch_sync(url: str) -> str:
    global _request_count
    driver = _get_driver_sync()
    driver.get(url)
    from selenium.webdriver.common.by import By  # type: ignore

    try:
        driver.implicitly_wait(10)
        driver.find_element(
            By.CSS_SELECTOR,
            "tr.with-hover, h1[itemprop='name'], div.catalog__g1, div.catalog__g2_row, #itemlist",
        )
    except Exception:
        pass
    html = driver.page_source
    # The anti-bot JS reloads the page after ~200ms; if we still see the
    # challenge, give it a moment and reload explicitly once.
    if _looks_like_challenge(html):
        import time

        time.sleep(1.0)
        try:
            driver.get(url)
            driver.find_element(
                By.CSS_SELECTOR,
                "tr.with-hover, h1[itemprop='name'], div.catalog__g1, div.catalog__g2_row, #itemlist",
            )
        except Exception:
            pass
        html = driver.page_source
    _request_count += 1
    return html


async def fetch(url: str) -> str:
    if not get_settings().use_selenium_fallback:
        raise RuntimeError("selenium fallback disabled")
    async with _lock:
        await get_rate_limiter().acquire()
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, _fetch_sync, url)
        except Exception as exc:
            logger.error("Selenium fetch failed for {}: {}", url, exc)
            raise


async def shutdown() -> None:
    global _driver, _request_count
    _request_count = 0
    if _driver is not None:
        try:
            await asyncio.get_running_loop().run_in_executor(None, _driver.quit)
        except Exception:
            pass
        _driver = None
