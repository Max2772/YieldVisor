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
    return STEAM_APPS.get(app_id, f"App {app_id}")
