"""Miele XGW 2000 integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .api import MieleApi
from .const import CONF_HOST, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import STORAGE_VERSION, MieleCoordinator, storage_key

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: MieleCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.stop_multicast_listener()
    await coordinator.api.close()

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the stored appliance data along with the entry."""
    await Store(hass, STORAGE_VERSION, storage_key(entry.entry_id)).async_remove()
