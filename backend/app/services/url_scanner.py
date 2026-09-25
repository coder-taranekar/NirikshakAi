"""
E-commerce URL Scanner — fetch product listing pages and extract label images.

Supported platforms:
  - Amazon India (amazon.in)
  - Flipkart (flipkart.com)
  - Generic fallback: largest img tag by declared dimensions

Pipeline:
  1. Fetch HTML of the product listing page via httpx
  2. Parse with BeautifulSoup to locate the main product image
  3. Download the image bytes
  4. Return bytes to the inspection pipeline (Task 8)

Platform-specific selectors:
  Amazon: #landingImage, #imgBlkFront, .a-dynamic-image (data-old-hires attr)
  Flipkart: img._396cs4, img._2r_T1I, div._3kidJX img, .CXW8mj img

All network calls use httpx with a 30-second timeout and browser-like headers
to avoid bot detection blocks.
"""

import logging
import re
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Shared HTTP client settings
_TIMEOUT = 30.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

_MAX_IMAGE_BYTES = 15 * 1024 * 1024  # 15 MB cap for product images


# ── Platform Detectors ─────────────────────────────────────────────────────────

def _is_amazon(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return "amazon" in hostname


def _is_flipkart(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return "flipkart" in hostname


# ── Amazon Image Extractor ─────────────────────────────────────────────────────

def _extract_amazon_image_url(soup: BeautifulSoup, page_url: str) -> Optional[str]:
    """
    Extract the main product image URL from an Amazon listing page.

    Strategy (in priority order):
      1. #landingImage data-old-hires  (highest-res static image)
      2. #landingImage data-a-dynamic-image (JSON map of {url: [w,h]}, pick largest)
      3. #imgBlkFront src
      4. Any img with id containing 'main-image'
    """
    # Strategy 1: data-old-hires on #landingImage
    img = soup.find("img", id="landingImage")
    if img:
        hi_res = img.get("data-old-hires", "").strip()
        if hi_res and hi_res.startswith("http"):
            return hi_res

        # Strategy 2: data-a-dynamic-image JSON
        dynamic = img.get("data-a-dynamic-image", "")
        if dynamic:
            try:
                import json
                url_map: dict = json.loads(dynamic)
                # Pick the URL with the largest width
                best_url = max(url_map.keys(), key=lambda u: url_map[u][0])
                if best_url:
                    return best_url
            except Exception:
                pass

        # Fallback: src of #landingImage
        src = img.get("src", "").strip()
        if src and src.startswith("http"):
            return src

    # Strategy 3: #imgBlkFront
    img2 = soup.find("img", id="imgBlkFront")
    if img2:
        src = img2.get("src", "").strip()
        if src and src.startswith("http"):
            return src

    # Strategy 4: any img whose id contains 'main-image'
    img3 = soup.find("img", id=re.compile(r"main.?image", re.IGNORECASE))
    if img3:
        src = img3.get("src", "").strip()
        if src and src.startswith("http"):
            return src

    return None


# ── Flipkart Image Extractor ───────────────────────────────────────────────────

def _extract_flipkart_image_url(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract the main product image URL from a Flipkart listing page.

    Strategy (in priority order):
      1. img._396cs4 (primary product image class, current layout)
      2. img._2r_T1I (alternate class)
      3. div._3kidJX img, div.CXW8mj img (container-based selectors)
      4. Any img whose src contains 'rukminim' (Flipkart CDN)
    """
    # Strategy 1 & 2: class-based selectors
    for css_class in ("_396cs4", "_2r_T1I", "q6DClP"):
        img = soup.find("img", class_=css_class)
        if img:
            src = img.get("src", "").strip()
            if src and src.startswith("http"):
                return src

    # Strategy 3: container img
    for container_class in ("_3kidJX", "CXW8mj", "_2mOlnD"):
        container = soup.find("div", class_=container_class)
        if container:
            img = container.find("img")
            if img:
                src = img.get("src", "").strip()
                if src and src.startswith("http"):
                    return src

    # Strategy 4: Flipkart CDN pattern
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "rukminim" in src and src.startswith("http"):
            return src

    return None


# ── Generic Fallback Extractor ─────────────────────────────────────────────────

def _extract_generic_image_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """
    Generic fallback: find the largest img element by declared width×height.
    Also considers og:image meta tag.
    """
    # og:image
    og = soup.find("meta", property="og:image")
    if og and og.get("content", "").startswith("http"):
        return og["content"]

    # Largest img by width × height attributes
    best_url: Optional[str] = None
    best_area = 0
    for img in soup.find_all("img"):
        try:
            w = int(img.get("width", 0))
            h = int(img.get("height", 0))
        except (ValueError, TypeError):
            continue
        area = w * h
        if area > best_area:
            src = img.get("src", "").strip()
            if src:
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    parsed = urlparse(base_url)
                    src = f"{parsed.scheme}://{parsed.netloc}{src}"
                if src.startswith("http"):
                    best_url = src
                    best_area = area

    return best_url


# ── Image Downloader ───────────────────────────────────────────────────────────

async def _download_image(url: str) -> Optional[bytes]:
    """Download an image from a URL and return bytes, or None on failure."""
    try:
        async with httpx.AsyncClient(
            headers=_HEADERS,
            timeout=_TIMEOUT,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "image" not in content_type:
                logger.warning(
                    "url_scanner_non_image_content",
                    url=url,
                    content_type=content_type,
                )
                # Still return — some CDNs omit content-type

            data = response.content
            if len(data) > _MAX_IMAGE_BYTES:
                logger.warning("url_scanner_image_too_large", url=url, size=len(data))
                return None

            return data
    except Exception as exc:
        logger.error("url_scanner_image_download_failed", url=url, error=str(exc))
        return None


# ── Page Fetcher ───────────────────────────────────────────────────────────────

async def _fetch_page_html(url: str) -> Optional[str]:
    """Fetch the HTML of a product listing page."""
    try:
        async with httpx.AsyncClient(
            headers=_HEADERS,
            timeout=_TIMEOUT,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as exc:
        logger.error("url_scanner_page_fetch_failed", url=url, error=str(exc))
        return None


# ── Main Entry Point ───────────────────────────────────────────────────────────

async def fetch_product_image_from_url(product_url: str) -> Optional[bytes]:
    """
    Fetch the main product label image from an e-commerce listing URL.

    Returns:
        Image bytes if successful, None if the image could not be extracted.

    Supported: Amazon India, Flipkart, generic (og:image / largest img).
    """
    logger.info("url_scanner_start", url=product_url)

    html = await _fetch_page_html(product_url)
    if not html:
        logger.error("url_scanner_no_html", url=product_url)
        return None

    soup = BeautifulSoup(html, "lxml")
    image_url: Optional[str] = None

    if _is_amazon(product_url):
        image_url = _extract_amazon_image_url(soup, product_url)
        logger.info("url_scanner_amazon", extracted_url=image_url)

    elif _is_flipkart(product_url):
        image_url = _extract_flipkart_image_url(soup)
        logger.info("url_scanner_flipkart", extracted_url=image_url)

    if not image_url:
        # Generic fallback for any other retailer
        image_url = _extract_generic_image_url(soup, product_url)
        logger.info("url_scanner_generic_fallback", extracted_url=image_url)

    if not image_url:
        logger.error("url_scanner_no_image_found", url=product_url)
        return None

    image_bytes = await _download_image(image_url)
    if image_bytes:
        logger.info(
            "url_scanner_image_downloaded",
            image_url=image_url,
            size_bytes=len(image_bytes),
        )
    return image_bytes
