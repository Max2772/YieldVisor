from typing import TypedDict

from apps.portfolio.types import AssetType


class TickerSpec(TypedDict):
    asset_type: str
    asset_name: str
    symbol: str
    app_id: int | None


HOMEPAGE_TICKERS: list[TickerSpec] = [
    {"asset_type": AssetType.STOCK, "asset_name": "NVDA", "symbol": "NVDA"},
    {"asset_type": AssetType.CRYPTO, "asset_name": "bitcoin", "symbol": "BTC"},
    {"asset_type": AssetType.STEAM, "asset_name": "Glove Case", "symbol": "Glove Case", "app_id": 730},
    {"asset_type": AssetType.STOCK, "asset_name": "TSLA", "symbol": "TSLA"},
    {"asset_type": AssetType.CRYPTO, "asset_name": "ethereum", "symbol": "ETH"},
    {
        "asset_type": AssetType.STEAM,
        "asset_name": "AK-47 | Slate (Factory New)",
        "symbol": "AK-47 | Slate",
        "app_id": 730,
    },
    {"asset_type": AssetType.STOCK, "asset_name": "AMD", "symbol": "AMD"},
    {"asset_type": AssetType.CRYPTO, "asset_name": "solana", "symbol": "SOL"},
    {"asset_type": AssetType.STEAM, "asset_name": "Fever Case", "symbol": "Fever Case", "app_id": 730},
    {"asset_type": AssetType.STOCK, "asset_name": "AAPL", "symbol": "AAPL"},
    {"asset_type": AssetType.CRYPTO, "asset_name": "the-open-network", "symbol": "TON"},
    {
        "asset_type": AssetType.STEAM,
        "asset_name": "★ Falchion Knife | Autotronic (Minimal Wear)",
        "symbol": "★ Falchion Knife | Autotronic",
        "app_id": 730,
    },
]