"""Dependency-free request dispatcher; no listener or network side effects."""
from collections.abc import Mapping


def dispatch(method: str, path: str, body: Mapping, config: Mapping) -> tuple[int, dict]:
    if method != "POST" or path != "/v2/offers":
        return 404, {"error": "not found"}
    settings = config.get("offers_v2")
    if not isinstance(settings, Mapping):
        return 503, {"error": "offers_v2 configuration unavailable"}
    nights = body.get("nights", settings.get("default_nights"))
    if isinstance(nights, bool) or not isinstance(nights, int) or nights < 1:
        return 400, {"error": "nights must be a positive integer"}
    return 200, {"nights": nights, "search_type": settings.get("search_type", "standard")}
