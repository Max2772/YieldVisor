from __future__ import annotations

from apps.core.services.invest_api import PriceHistory, PriceQuote
from apps.portfolio.types import AssetType
from apps.steam.constants import steam_app_label


def asset_subtitle(
    quote: PriceQuote | None,
    history: PriceHistory | None,
    *,
    symbol: str,
    asset_type: str = "",
    app_id: int | None = None,
) -> str:
    """Подзаголовок актива (полное имя компании и т.п.) — как в Market Search."""
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
