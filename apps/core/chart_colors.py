from __future__ import annotations

from apps.portfolio.types import AssetType

_CHART_STYLES: dict[str, dict[str, str]] = {
    AssetType.STOCK: {
        "chart_line_color": "#00e676",
        "chart_fill_start": "rgba(0,230,118,0.18)",
        "chart_fill_end": "rgba(0,230,118,0)",
    },
    AssetType.CRYPTO: {
        "chart_line_color": "#7c83ff",
        "chart_fill_start": "rgba(124,131,255,0.18)",
        "chart_fill_end": "rgba(124,131,255,0)",
    },
    AssetType.STEAM: {
        "chart_line_color": "#4fc3f7",
        "chart_fill_start": "rgba(79,195,247,0.18)",
        "chart_fill_end": "rgba(79,195,247,0)",
    },
}

_DEFAULT = _CHART_STYLES[AssetType.STOCK]

_PORTFOLIO_CHART = {
    "chart_line_color": "#ff9800",
    "chart_fill_start": "rgba(255,152,0,0.18)",
    "chart_fill_end": "rgba(255,152,0,0)",
}

_HERO_CHART = {
    "chart_line_color": "#4fc3f7",
    "chart_fill_start": "rgba(79,195,247,0.18)",
    "chart_fill_end": "rgba(79,195,247,0)",
}


def asset_chart_colors(asset_type: str) -> dict[str, str]:
    """Line-chart colors for a market category (list + detail pages)."""
    return dict(_CHART_STYLES.get(asset_type, _DEFAULT))


def portfolio_chart_colors() -> dict[str, str]:
    """Line-chart colors for the aggregate portfolio overview page."""
    return dict(_PORTFOLIO_CHART)


def hero_chart_colors() -> dict[str, str]:
    """Line-chart colors for the public homepage hero mockup."""
    return dict(_HERO_CHART)
