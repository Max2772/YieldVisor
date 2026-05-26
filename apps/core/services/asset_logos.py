from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from urllib.parse import quote

import httpx
from django.conf import settings
from django.core.cache import cache

from apps.core.market_catalog import CRYPTO_MARKET_CATALOG
from apps.portfolio.types import AssetType

PARQET_STOCK_LOGO_URL = "https://assets.parqet.com/logos/symbol/{symbol}?format=png"
CRYPTO_ICON_URL = (
    "https://cdn.jsdelivr.net/gh/madenix/Crypto-logo-cdn@main/Logos/{symbol}.svg"
)
FALLBACK_CRYPTO_ICON_URL = (
    "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/{symbol}.svg"
)
STEAM_LISTING_URL = "https://steamcommunity.com/market/listings/{app_id}/{name}"
STEAM_ECONOMY_IMAGE_RE = re.compile(
    r"(https://community\.steamstatic\.com/economy/image/[^\"'\s>]+)",
    re.IGNORECASE,
)

LOGO_CACHE_PREFIX = "asset_logo"
LOGO_CACHE_TTL = int(
    getattr(settings, "ASSET_LOGO_CACHE_TTL", 60 * 60 * 24 * 365)
)
STEAM_FETCH_TIMEOUT = float(getattr(settings, "STEAM_LOGO_FETCH_TIMEOUT", "12"))
_CACHE_MISS = object()
# Memcached / Redis: only safe ASCII in key segments (no spaces, |, :, etc.)
_SAFE_CACHE_KEY_PART = re.compile(r"^[\w.-]+$", re.ASCII)


def _cache_key(kind: str, *parts: str) -> str:
    """Ключ без пробелов и спецсимволов — иначе CacheKeyWarning и сбой на memcached."""
    segments: list[str] = []
    for part in parts:
        text = str(part)
        if _SAFE_CACHE_KEY_PART.fullmatch(text):
            segments.append(text)
        else:
            segments.append(hashlib.sha256(text.encode("utf-8")).hexdigest())
    return ".".join((LOGO_CACHE_PREFIX, kind, *segments))


def _get_cached(key: str) -> str | None:
    """None — в кеше нет записи; '' — искали, не нашли; иначе URL."""
    value = cache.get(key, _CACHE_MISS)
    if value is _CACHE_MISS:
        return None
    return value or ""


def _set_cached(key: str, url: str) -> str:
    cache.set(key, url, LOGO_CACHE_TTL)
    return url


def stock_logo_url(ticker: str) -> str:
    symbol = ticker.strip().upper()
    if not symbol:
        return ""
    key = _cache_key("stock", symbol)
    cached = _get_cached(key)
    if cached is not None:
        return cached
    return _set_cached(key, PARQET_STOCK_LOGO_URL.format(symbol=symbol))


@lru_cache(maxsize=1)
def _crypto_catalog_by_name() -> dict[str, str]:
    return {
        entry["asset_name"].lower(): entry["symbol"].lower()
        for entry in CRYPTO_MARKET_CATALOG
    }


def crypto_icon_slug(asset_name: str, *, symbol: str | None = None) -> str:
    if symbol:
        return symbol.strip().lower()
    normalized = asset_name.strip().lower()
    return _crypto_catalog_by_name().get(normalized, normalized)


def crypto_logo_url(asset_name: str, *, symbol: str | None = None) -> str:
    slug = crypto_icon_slug(asset_name, symbol=symbol)
    if not slug:
        return ""
    key = _cache_key("crypto", slug)
    cached = _get_cached(key)
    if cached is not None:
        return cached
    symbol_upper = slug.upper()
    if symbol_upper in ("ETH", "TRX"):
        return _set_cached(key, FALLBACK_CRYPTO_ICON_URL.format(symbol=symbol_upper.lower()))
    return _set_cached(key, CRYPTO_ICON_URL.format(symbol=symbol_upper))


def _parse_steam_logo_from_html(html: str) -> str:
    match = STEAM_ECONOMY_IMAGE_RE.search(html)
    if not match:
        return ""
    url = match.group(1)
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _fetch_steam_logo_from_market(app_id: int, market_hash_name: str) -> str:
    listing_url = STEAM_LISTING_URL.format(
        app_id=app_id,
        name=quote(market_hash_name, safe=""),
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; YieldVisor/1.0; +https://github.com/yieldvisor)"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        with httpx.Client(
            timeout=STEAM_FETCH_TIMEOUT,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = client.get(listing_url)
            if response.status_code >= 400:
                return ""
            return _parse_steam_logo_from_html(response.text)
    except httpx.HTTPError:
        return ""


def steam_logo_url(app_id: int, market_hash_name: str) -> str:
    name = market_hash_name.strip()
    if not name or not app_id:
        return ""
    key = _cache_key("steam", str(app_id), name)
    cached = _get_cached(key)
    if cached is not None:
        return cached
    return _set_cached(key, _fetch_steam_logo_from_market(app_id, name))


def asset_logo_url(
    asset_type: str,
    *,
    ticker: str = "",
    asset_name: str = "",
    app_id: int | None = None,
    crypto_symbol: str | None = None,
) -> str:
    if asset_type == AssetType.STOCK:
        return stock_logo_url(ticker or asset_name)
    if asset_type == AssetType.CRYPTO:
        return crypto_logo_url(asset_name, symbol=crypto_symbol)
    if asset_type == AssetType.STEAM and app_id and asset_name:
        return steam_logo_url(app_id, asset_name)
    return ""
