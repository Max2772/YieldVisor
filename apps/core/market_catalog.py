from __future__ import annotations

import random
from typing import TypedDict

from apps.portfolio.types import AssetType

MARKET_SEARCH_SAMPLE_SIZE = 2
PORTFOLIO_CHART_DAYS = 30
PORTFOLIO_CHART_MAX_DAYS = 1825
# InvestAPI crypto history is capped at ~365 days.
PORTFOLIO_CHART_MAX_DAYS_CRYPTO = 365


class StockCatalogEntry(TypedDict):
    asset_name: str


class CryptoCatalogEntry(TypedDict):
    asset_name: str
    symbol: str


class SteamCatalogEntry(TypedDict):
    asset_name: str
    app_id: int


STOCK_MARKET_CATALOG: list[StockCatalogEntry] = [
    # Mega-cap US tech
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
    {"asset_name": "AVGO"},
    {"asset_name": "ADBE"},
    {"asset_name": "CRM"},
    {"asset_name": "ORCL"},
    {"asset_name": "LRCX"},
    {"asset_name": "SHOP"},
    # ETFs (broad market, sectors, themes)
    {"asset_name": "SPY"},
    {"asset_name": "QQQ"},
    {"asset_name": "VOO"},
    {"asset_name": "VTI"},
    {"asset_name": "DIA"},
    {"asset_name": "IWM"},
    {"asset_name": "XLK"},
    {"asset_name": "XLF"},
    {"asset_name": "XLE"},
    {"asset_name": "XLV"},
    {"asset_name": "SMH"},
    {"asset_name": "SOXX"},
    {"asset_name": "ARKK"},
    {"asset_name": "HYG"},
]

CRYPTO_MARKET_CATALOG: list[CryptoCatalogEntry] = [
    # Layer 1 / majors
    {"asset_name": "bitcoin", "symbol": "BTC"},
    {"asset_name": "ethereum", "symbol": "ETH"},
    {"asset_name": "solana", "symbol": "SOL"},
    {"asset_name": "bnb", "symbol": "BNB"},
    {"asset_name": "the-open-network", "symbol": "TON"},
    {"asset_name": "tron", "symbol": "TRX"},
    {"asset_name": "avalanche-2", "symbol": "AVAX"},
    {"asset_name": "polkadot", "symbol": "DOT"},
    {"asset_name": "cardano", "symbol": "ADA"},
    # Payments / large caps
    {"asset_name": "ripple", "symbol": "XRP"},
    {"asset_name": "dogecoin", "symbol": "DOGE"},
    {"asset_name": "litecoin", "symbol": "LTC"},
    {"asset_name": "bitcoin-cash", "symbol": "BCH"},
    {"asset_name": "chainlink", "symbol": "LINK"},
    {"asset_name": "tether", "symbol": "USDT"},
    {"asset_name": "usd-coin", "symbol": "USDC"},
]

STEAM_MARKET_CATALOG: list[SteamCatalogEntry] = [
    # CS2
    {"asset_name": "Glove Case", "app_id": 730},
    {"asset_name": "Fever Case", "app_id": 730},
    {"asset_name": "AK-47 | Redline (Field-Tested)", "app_id": 730},
    {"asset_name": "AWP | Asiimov (Field-Tested)", "app_id": 730},
    {"asset_name": "AK-47 | Slate (Factory New)", "app_id": 730},
    {
        "asset_name": "★ Falchion Knife | Autotronic (Minimal Wear)",
        "app_id": 730,
    },
    # Dota 2
    {"asset_name": "Treasure of the Crimson Witness 2024", "app_id": 570},
    {"asset_name": "Manifold Paradox", "app_id": 570},
    {"asset_name": "Dragonclaw Hook", "app_id": 570},
    # TF2
    {"asset_name": "Mann Co. Supply Crate Key", "app_id": 440},
    {"asset_name": "Earbuds", "app_id": 440},
    {"asset_name": "Unusual Team Captain", "app_id": 440},
    # Rust
    {"asset_name": "Tempered AK47", "app_id": 252490},
    {"asset_name": "Alien Red", "app_id": 252490},
    # PUBG
    {"asset_name": "Desert Digital - M416", "app_id": 578080},
    # Unturned
    {"asset_name": "Unturned Booster Pack", "app_id": 304930},
    {"asset_name": "Surplus Jacket", "app_id": 304930},
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
