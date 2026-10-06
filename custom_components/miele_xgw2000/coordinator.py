"""DataUpdateCoordinator for Miele XGW 2000."""
from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MieleApi, MieleAppliance, MieleApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MCAST_GRP, MCAST_PORT

_LOGGER = logging.getLogger(__name__)

# Failed polls in a row before entities go unavailable
MAX_TOLERATED_FAILURES = 3
# How long an appliance that drops off mid-program keeps its last values
MISSING_GRACE_SECONDS = 600


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
        self._failures = 0
        self._last_seen: dict[str, float] = {}

    async def _async_update_data(self) -> dict[str, MieleAppliance]:
        try:
            appliances = await self.api.get_appliances()
        except MieleApiError as exc:
            # The gateway misses the odd request (timeout or refused
            # connection). Keep the last data through a few misses in a row
            # rather than flapping every entity to unavailable.
            self._failures += 1
            if self.data is not None and self._failures < MAX_TOLERATED_FAILURES:
                _LOGGER.debug(
                    "Gateway request failed (%s/%s), keeping last data: %s",
                    self._failures, MAX_TOLERATED_FAILURES, exc,
                )
                return self.data
            raise UpdateFailed(str(exc)) from exc
        self._failures = 0

        # Enrich each appliance with detail data (actions available depend on state)
        for appliance in appliances:
            # Real gateways name it "Details"; match case-insensitively
            detail_action = next(
                (a for a in appliance.actions if a.name.lower() == "details"), None
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

        now = time.monotonic()
        data = {a.uid: a for a in appliances}
        for uid in data:
            self._last_seen[uid] = now

        # Idle appliances drop off the powerline bus for minutes at a time and
        # the gateway stops listing them. One that was off when it left is
        # still off, so keep showing it; one that left mid-program gets a
        # grace period before its entities go unavailable.
        for uid, previous in (self.data or {}).items():
            if uid in data:
                continue
            was_off = (previous.info.get("State") or "").lower() == "off"
            if was_off or now - self._last_seen.get(uid, now) < MISSING_GRACE_SECONDS:
                previous.actions = []  # nothing can be triggered off the bus
                data[uid] = previous

        return data

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
