"""What this integration adds to the anonymous daily report.

Free of Home Assistant imports on purpose, so the payload can be reviewed
without a Home Assistant installation. Everything here is a model
designation, an appliance type from a closed list, or a count. Never an appliance name, a room, a UID or when
anything ran.

See https://stats.rnet.se/integritet for the full list.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

#: At most this many models are sent; the server takes no more anyway.
MAX_MODELS = 8

#: The shape a model designation must have after cleaning.
_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,31}$")


def model_slug(device_type: Any) -> str | None:
    """The gateway's <type> ("H5681BP", padded with spaces) as a slug.

    Taken only from the type, never from <name> or <additionalName>: those
    are the user's own and can be anything. Whatever does not clean up into a
    plain model designation is dropped.
    """
    if device_type is None or isinstance(device_type, bool):
        return None
    text = re.sub(r"[^a-z0-9._-]+", "_", str(device_type).strip().lower()).strip("_")
    return text if _SLUG.match(text) else None


#: The gateway's "Appliance Type" (language=en) -> short slug. A closed list:
#: a type that is not in it is sent as "other", never by its text.
TYPE_SLUGS = {
    "washing machine": "washer",
    "tumble dryer": "dryer",
    "washer dryer": "washer_dryer",
    "dishwasher": "dishwasher",
    "oven": "oven",
    "oven with microwave": "oven_microwave",
    "steam oven": "steam_oven",
    "steam combination oven": "steam_combi",
    "microwave": "microwave",
    "hob": "hob",
    "hood": "hood",
    "coffee machine": "coffee",
    "fridge": "fridge",
    "freezer": "freezer",
    "fridge-freezer": "fridge_freezer",
    "wine conditioning unit": "wine_cabinet",
    "warming drawer": "dish_warmer",
}


def type_slug(appliance_type: Any) -> str:
    """The appliance type as a slug. An unknown type becomes "other"."""
    return TYPE_SLUGS.get(str(appliance_type or "").strip().lower(), "other")


def build_extra(appliances: Iterable[Any]) -> dict[str, Any]:
    """The integration's part of the report.

    ``appliances`` are the coordinator's MieleAppliance objects. Which models
    the integration runs against, once each and sorted: the model designation
    when the gateway gives one, otherwise the appliance type (some appliances
    report an empty <type>). And how many appliances the gateway has.
    """
    appliances = list(appliances or [])
    models = {
        model_slug(getattr(a, "device_type", None))
        or type_slug((getattr(a, "info", None) or {}).get("Appliance Type"))
        for a in appliances
    }
    return {
        "models": sorted(models)[:MAX_MODELS],
        "metrics": {"appliances": len(appliances)} if appliances else {},
    }
