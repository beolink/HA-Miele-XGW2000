"""DataUpdateCoordinator for Miele XGW 2000."""
from __future__ import annotations

import asyncio
import logging
import socket
import struct
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MieleApi, MieleAppliance, MieleApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MCAST_GRP, MCAST_PORT

_LOGGER = logging.getLogger(__name__)


class MieleCoordinator(DataUpdateCoordinator[dict[str, MieleAppliance]]):
    """Polls the gateway and optionally listens for multicast push notifications."""

    def __init__(self, hass: HomeAssistant, api: MieleApi, scan_interval: int = DEFAULT_SCAN_INTERVAL) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self._mcast_task: asyncio.Task | None = None

    async def _async_update_data(self) -> dict[str, MieleAppliance]:
        try:
            appliances = await self.api.get_appliances()
        except MieleApiError as exc:
            raise UpdateFailed(str(exc)) from exc

        # Enrich each appliance with detail data (actions available depend on state)
        for appliance in appliances:
            detail_action = next(
                (a for a in appliance.actions if a.name == "details"), None
            )
            if detail_action:
                try:
                    detail_info, detail_actions = await self.api.get_appliance_detail(
                        detail_action.url
                    )
                    appliance.info.update(detail_info)
                    appliance.actions = detail_actions
                except MieleApiError:
                    pass  # keep what we have from the base list

        return {a.uid: a for a in appliances}

    def start_multicast_listener(self) -> None:
        """Start listening for UDP push notifications from the gateway."""
        if self._mcast_task is None:
            self._mcast_task = self.hass.loop.create_task(self._mcast_loop())

    def stop_multicast_listener(self) -> None:
        if self._mcast_task:
            self._mcast_task.cancel()
            self._mcast_task = None

    async def _mcast_loop(self) -> None:
        """Listen on the multicast group and trigger a refresh on any notification."""
        loop = asyncio.get_event_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", MCAST_PORT))
            mreq = struct.pack("4sL", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            sock.setblocking(False)
            _LOGGER.debug("Miele multicast listener started on %s:%s", MCAST_GRP, MCAST_PORT)
            while True:
                await loop.sock_recv(sock, 1024)
                _LOGGER.debug("Miele push notification received, refreshing")
                await self.async_refresh()
        except asyncio.CancelledError:
            pass
        except OSError as exc:
            _LOGGER.warning("Miele multicast listener failed: %s", exc)
        finally:
            sock.close()
