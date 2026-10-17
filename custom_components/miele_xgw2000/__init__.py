"""Miele XGW 2000 integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.loader import async_get_integration

from .api import MieleApi
from .const import CONF_HOST, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import STORAGE_VERSION, MieleCoordinator, storage_key
from .stats import async_setup_stats, async_stop_stats
from .stats_extra import build_extra

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Before the first call that can raise ConfigEntryNotReady, so the daily
    # report keeps going out (saying setup_retry) while the gateway is away.
    integration = await async_get_integration(hass, DOMAIN)
    await async_setup_stats(
        hass, entry, DOMAIN, str(integration.version),
        extra=lambda: _stats_extra(hass, entry),
        name="Miele XGW 2000",
    )

    host = entry.data[CONF_HOST]
    username = entry.data.get(CONF_USERNAME) or None
    password = entry.data.get(CONF_PASSWORD) or None
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    api = MieleApi(host, username, password)
    coordinator = MieleCoordinator(hass, api, entry.entry_id, scan_interval)
    await coordinator.async_restore()
    await coordinator.async_config_entry_first_refresh()
    coordinator.start_multicast_listener()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Reload when the options change, so switching statistics back on takes
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _stats_extra(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    """Looked up when the report is built; set-up may not have finished."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    return build_extra((coordinator.data or {}).values() if coordinator else [])


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: MieleCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.stop_multicast_listener()
    await coordinator.api.close()

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Only here, never via entry.async_on_unload: those also run when a
        # set-up attempt fails, and the report must survive that.
        await async_stop_stats(hass, entry, DOMAIN)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the stored appliance data along with the entry."""
    await Store(hass, STORAGE_VERSION, storage_key(entry.entry_id)).async_remove()
