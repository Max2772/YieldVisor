from __future__ import annotations

STEAM_APPS: dict[int, str] = {
    730: "CS2",
    570: "Dota 2",
    440: "TF2",
    252490: "Rust",
    578080: "PUBG",
    304930: "Unturned",
}

STEAM_APP_FULL_LABELS: dict[int, str] = {
    730: "Counter-Strike 2",
    570: "Dota 2",
    440: "Team Fortress 2",
    252490: "Rust",
    578080: "PUBG: Battlegrounds",
    304930: "Unturned",
}

def resolve_steam_app_filter(raw: str | None) -> int | None:
    """None — все игры; int — фильтр по app_id."""
    if raw is None or raw == "" or str(raw).lower() == "all":
        return None
    try:
        app_id = int(raw)
    except (TypeError, ValueError):
        return None
    if app_id not in STEAM_APPS:
        return None
    return app_id


def steam_app_label(app_id: int | None) -> str:
    if app_id is None:
        return "—"
    return STEAM_APP_FULL_LABELS.get(app_id, f"App {app_id}")


def enrich_steam_search_result(row: dict) -> dict:
    """Добавляет человекочитаемое имя игры для результатов Market Search."""
    if row.get("asset_type") != "steam":
        return row
    app_id = row.get("app_id")
    if app_id is None:
        return row
    try:
        app_id_int = int(app_id)
    except (TypeError, ValueError):
        return row
    enriched = dict(row)
    enriched["game"] = steam_app_label(app_id_int)
    return enriched
