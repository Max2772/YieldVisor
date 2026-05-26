from __future__ import annotations

from apps.core.services.asset_logos import (
    asset_logo_url,
    crypto_icon_slug,
    stock_logo_url,
)
from apps.core.services.invest_api import PriceHistory, PriceQuote
from apps.portfolio.types import AssetType
from apps.steam.constants import steam_app_label

__all__ = [
    "asset_icon_context",
    "asset_subtitle",
    "stock_logo_url",
]


_ICON_COLORS: dict[str, tuple[str, str]] = {
    AssetType.STOCK: ("#1a2e40", "#4fc3f7"),
    AssetType.CRYPTO: ("#1a2a1a", "#00e676"),
    AssetType.STEAM: ("#1a2040", "#7c83ff"),
}


def asset_icon_text(
    asset_type: str,
    display_label: str,
    *,
    app_id: int | None = None,
) -> str:
    """Генерирует текст для fallback-иконки."""
    if asset_type == AssetType.STEAM and app_id:
        label = steam_app_label(app_id)
        if label != "—":
            return label[:2]

    text = display_label.strip()
    if len(text) >= 2:
        return text[:2].upper()
    return (text[:1] or "?").upper()


def asset_icon_context(
    asset_type: str,
    *,
    display_label: str,
    asset_name: str = "",
    crypto_symbol: str | None = None,
    app_id: int | None = None,
) -> dict[str, str]:
    """Возвращает контекст для asset_icon.html (logo + fallback)."""
    name = asset_name or display_label

    icon_bg, icon_fg = _ICON_COLORS.get(
        asset_type, ("#1a2040", "#7c83ff")
    )

    if asset_type == AssetType.CRYPTO:
        resolved_crypto_symbol = (
            crypto_symbol.strip() if crypto_symbol else None
        )
        if not resolved_crypto_symbol:
            resolved_crypto_symbol = crypto_icon_slug(name)
    else:
        resolved_crypto_symbol = None

    return {
        "logo_url": asset_logo_url(
            asset_type,
            ticker=display_label,
            asset_name=name,
            app_id=app_id,
            crypto_symbol=resolved_crypto_symbol,
        ),
        "icon_text": asset_icon_text(asset_type, display_label, app_id=app_id),
        "icon_bg": icon_bg,
        "icon_fg": icon_fg,
    }


def asset_subtitle(
    quote: PriceQuote | None,
    history: PriceHistory | None,
    *,
    symbol: str,
    asset_type: str = "",
    app_id: int | None = None,
) -> str:
    """Формирует подзаголовок актива (полное имя)."""
    display_name = ""
    if quote and quote.full_name:
        display_name = quote.full_name
    elif quote and quote.name:
        display_name = quote.name
    elif history and history.full_name:
        display_name = history.full_name
    elif history and history.name:
        display_name = history.name

    subtitle = display_name if display_name and display_name != symbol else ""

    if asset_type == AssetType.STEAM and app_id:
        subtitle = subtitle or steam_app_label(app_id)

    return subtitle