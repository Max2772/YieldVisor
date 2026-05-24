from __future__ import annotations

import random
from typing import TypedDict

from apps.portfolio.types import AssetType

MARKET_SEARCH_SAMPLE_SIZE = 2
PORTFOLIO_CHART_DAYS = 30


class StockCatalogEntry(TypedDict):
    asset_name: str


class CryptoCatalogEntry(TypedDict):
    asset_name: str
    symbol: str


class SteamCatalogEntry(TypedDict):
    asset_name: str
    app_id: int


STOCK_MARKET_CATALOG: list[StockCatalogEntry] = [
    {"asset_name": "NVDA"},
    {"asset_name": "AAPL"},
    {"asset_name": "AMD"},
    {"asset_name": "MSFT"},
    {"asset_name": "GOOGL"},
    {"asset_name": "META"},
    {"asset_name": "TSLA"},
    {"asset_name": "AMZN"},
    {"asset_name": "NFLX"},
    {"asset_name": "INTC"},
]

CRYPTO_MARKET_CATALOG: list[CryptoCatalogEntry] = [
    {"asset_name": "bitcoin", "symbol": "BTC"},
    {"asset_name": "ethereum", "symbol": "ETH"},
    {"asset_name": "solana", "symbol": "SOL"},
    {"asset_name": "cardano", "symbol": "ADA"},
    {"asset_name": "polkadot", "symbol": "DOT"},
    {"asset_name": "the-open-network", "symbol": "TON"},
    {"asset_name": "ripple", "symbol": "XRP"},
    {"asset_name": "dogecoin", "symbol": "DOGE"},
]

STEAM_MARKET_CATALOG: list[SteamCatalogEntry] = [
    {"asset_name": "Glove Case", "app_id": 730},
    {"asset_name": "Fever Case", "app_id": 730},
    {"asset_name": "AK-47 | Redline (Field-Tested)", "app_id": 730},
    {"asset_name": "AWP | Asiimov (Field-Tested)", "app_id": 730},
    {"asset_name": "AK-47 | Slate (Factory New)", "app_id": 730},
    {
        "asset_name": "★ Falchion Knife | Autotronic (Minimal Wear)",
        "app_id": 730,
    },
    {"asset_name": "Mann Co. Supply Crate Key", "app_id": 440},
]


def pick_stock_catalog(count: int = MARKET_SEARCH_SAMPLE_SIZE) -> list[StockCatalogEntry]:
    pool = STOCK_MARKET_CATALOG.copy()
    random.shuffle(pool)
    return pool[: min(count, len(pool))]


def pick_crypto_catalog(count: int = MARKET_SEARCH_SAMPLE_SIZE) -> list[CryptoCatalogEntry]:
    pool = CRYPTO_MARKET_CATALOG.copy()
    random.shuffle(pool)
    return pool[: min(count, len(pool))]


def pick_steam_catalog(count: int = MARKET_SEARCH_SAMPLE_SIZE) -> list[SteamCatalogEntry]:
    pool = STEAM_MARKET_CATALOG.copy()
    random.shuffle(pool)
    return pool[: min(count, len(pool))]


def catalog_for_asset_type(asset_type: str) -> list:
    if asset_type == AssetType.STOCK:
        return pick_stock_catalog()
    if asset_type == AssetType.CRYPTO:
        return pick_crypto_catalog()
    if asset_type == AssetType.STEAM:
        return pick_steam_catalog()
    return []
