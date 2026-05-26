from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

import httpx
from django.conf import settings
from django.core.cache import cache

from apps.portfolio.types import AssetType


class InvestAPIError(Exception):
    """Ошибка при обращении к InvestAPI."""


class PriceNotFoundError(InvestAPIError):
    """Актив не найден (HTTP 404)."""


@dataclass(frozen=True, slots=True)
class PriceQuote:
    asset_type: str
    name: str
    price: Decimal
    currency: str
    source: str | None = None
    full_name: str | None = None
    symbol: str | None = None
    app_id: int | None = None
    cached_at: str | None = None


@dataclass(frozen=True, slots=True)
class PriceHistoryPoint:
    timestamp: str
    price: Decimal
    volume: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PriceHistory:
    asset_type: str
    name: str
    points: tuple[PriceHistoryPoint, ...]
    interval: str | None = None
    full_name: str | None = None
    symbol: str | None = None
    app_id: int | None = None
    source: str | None = None
    cached_at: str | None = None


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise InvestAPIError(f"Invalid price value: {value!r}") from exc


def _parse_quote(data: dict[str, Any]) -> PriceQuote:
    return PriceQuote(
        asset_type=data.get("asset_type", ""),
        name=data.get("name", ""),
        price=_to_decimal(data["price"]),
        currency=data.get("currency", "USD"),
        source=data.get("source"),
        full_name=data.get("full_name"),
        symbol=data.get("symbol"),
        app_id=data.get("app_id"),
        cached_at=data.get("cached_at"),
    )


def _parse_history(data: dict[str, Any]) -> PriceHistory:
    raw_points = data.get("points") or []
    points: list[PriceHistoryPoint] = []
    for row in raw_points:
        if "price" not in row:
            continue
        volume = row.get("volume")
        points.append(
            PriceHistoryPoint(
                timestamp=str(row.get("timestamp", "")),
                price=_to_decimal(row["price"]),
                volume=_to_decimal(volume) if volume is not None else None,
            )
        )
    return PriceHistory(
        asset_type=data.get("asset_type", ""),
        name=data.get("name", ""),
        points=tuple(points),
        interval=data.get("interval"),
        full_name=data.get("full_name"),
        symbol=data.get("symbol"),
        app_id=data.get("app_id"),
        source=data.get("source"),
        cached_at=data.get("cached_at"),
    )


def period_change_pct(points: tuple[PriceHistoryPoint, ...]) -> Decimal | None:
    """Изменение в % от первой до последней точки ряда."""
    if len(points) < 2:
        return None
    first, last = points[0].price, points[-1].price
    if first == 0:
        return None
    return ((last - first) / first) * Decimal("100")


class InvestAPIClient:
    """Синхронный клиент InvestAPI (httpx) с кэшем Django."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        cache_ttl: int | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or settings.INVEST_API_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.INVEST_API_TIMEOUT
        self.cache_ttl = cache_ttl if cache_ttl is not None else settings.INVEST_API_CACHE_TTL
        self._client = client
        self._owns_client = client is None

    def __enter__(self) -> InvestAPIClient:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
            self._owns_client = True
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def _cache_key(self, path: str) -> str:
        return f"invest_api:{path}"

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
            self._owns_client = True
        return self._client

    def _fetch_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query = ""
        if params:
            query = "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cache_key = self._cache_key(f"{path}{query}")
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        url = f"{self.base_url}/{path}"
        http = self._get_client()
        try:
            response = http.get(url, params=params)
            if response.status_code == 404:
                raise PriceNotFoundError(f"Asset not found: {path}")
            if response.status_code >= 400:
                body = response.text
                raise InvestAPIError(
                    f"InvestAPI returned {response.status_code} for {path}: {body[:200]}"
                )
            try:
                data = response.json()
            except ValueError as exc:
                raise InvestAPIError(f"Invalid JSON from {url}") from exc
        except httpx.HTTPError as exc:
            raise InvestAPIError(f"Request failed: {url}") from exc

        cache.set(cache_key, data, self.cache_ttl)
        return data

    def get_stock(self, ticker: str) -> PriceQuote:
        ticker = ticker.strip().upper()
        return _parse_quote(self._fetch_json(f"stock/{ticker}"))

    def get_crypto(self, coin: str) -> PriceQuote:
        coin = coin.strip().lower()
        return _parse_quote(self._fetch_json(f"crypto/{coin}"))

    def get_steam(self, app_id: int, market_name: str) -> PriceQuote:
        name = market_name.strip()
        encoded = quote(name, safe="")
        return _parse_quote(self._fetch_json(f"steam/{app_id}/{encoded}"))

    def get_stock_history(self, ticker: str, *, days: int = 7) -> PriceHistory:
        ticker = ticker.strip().upper()
        return _parse_history(
            self._fetch_json(f"stock/{ticker}/history", params={"days": days})
        )

    def get_crypto_history(self, coin: str, *, days: int = 7) -> PriceHistory:
        coin = coin.strip().lower()
        return _parse_history(
            self._fetch_json(f"crypto/{coin}/history", params={"days": days})
        )

    def get_steam_history(
        self,
        app_id: int,
        market_name: str,
        *,
        days: int = 7,
    ) -> PriceHistory:
        name = market_name.strip()
        encoded = quote(name, safe="")
        return _parse_history(
            self._fetch_json(
                f"steam/{app_id}/{encoded}/history",
                params={"days": days},
            )
        )

    def fetch_history(
        self,
        asset_type: str,
        asset_name: str,
        app_id: int | None = None,
        *,
        days: int = 7,
    ) -> PriceHistory:
        if asset_type == AssetType.STOCK:
            return self.get_stock_history(asset_name, days=days)
        if asset_type == AssetType.CRYPTO:
            return self.get_crypto_history(asset_name, days=days)
        if asset_type == AssetType.STEAM:
            if app_id is None:
                raise InvestAPIError("app_id is required for Steam assets")
            return self.get_steam_history(app_id, asset_name, days=days)
        raise InvestAPIError(f"Unknown asset type: {asset_type!r}")

    def fetch(
        self,
        asset_type: str,
        asset_name: str,
        app_id: int | None = None,
    ) -> PriceQuote:
        if asset_type == AssetType.STOCK:
            return self.get_stock(asset_name)
        if asset_type == AssetType.CRYPTO:
            return self.get_crypto(asset_name)
        if asset_type == AssetType.STEAM:
            if app_id is None:
                raise InvestAPIError("app_id is required for Steam assets")
            return self.get_steam(app_id, asset_name)
        raise InvestAPIError(f"Unknown asset type: {asset_type!r}")


def get_quote(
    asset_type: str,
    asset_name: str,
    app_id: int | None = None,
    *,
    client: InvestAPIClient | None = None,
) -> PriceQuote | None:
    """Возвращает котировку или None, если актив не найден."""
    if client is not None:
        try:
            return client.fetch(asset_type, asset_name, app_id)
        except PriceNotFoundError:
            return None
        except InvestAPIError:
            raise

    with InvestAPIClient() as api:
        try:
            return api.fetch(asset_type, asset_name, app_id)
        except PriceNotFoundError:
            return None
        except InvestAPIError:
            raise


def get_price(
    asset_type: str,
    asset_name: str,
    app_id: int | None = None,
    *,
    client: InvestAPIClient | None = None,
) -> Decimal | None:
    """Текущая цена актива или None, если не найден."""
    quote = get_quote(asset_type, asset_name, app_id, client=client)
    return quote.price if quote else None


def get_history(
    asset_type: str,
    asset_name: str,
    app_id: int | None = None,
    *,
    days: int = 7,
    client: InvestAPIClient | None = None,
) -> PriceHistory | None:
    """История цен или None, если актив не найден."""
    if client is not None:
        try:
            return client.fetch_history(asset_type, asset_name, app_id, days=days)
        except PriceNotFoundError:
            return None
        except InvestAPIError:
            raise

    with InvestAPIClient() as api:
        try:
            return api.fetch_history(asset_type, asset_name, app_id, days=days)
        except PriceNotFoundError:
            return None
        except InvestAPIError:
            raise
