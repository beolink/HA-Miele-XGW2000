"""HTTP client for the Miele XGW 2000 Hausbus XML API."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import HOMEBUS_PATH


@dataclass
class MieleAction:
    name: str
    url: str


@dataclass
class MieleAppliance:
    uid: str
    device_class: str
    device_type: str
    name: str
    state: str
    additional_name: str = ""
    room: str = ""
    info: dict[str, str] = field(default_factory=dict)
    actions: list[MieleAction] = field(default_factory=list)


class MieleApiError(Exception):
    pass


class MieleApi:
    def __init__(
        self,
        host: str,
        username: str | None = None,
        password: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._base = f"http://{host}"
        self._auth = aiohttp.BasicAuth(username, password) if username else None
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    async def _get_xml(self, url: str) -> ET.Element:
        session = await self._get_session()
        try:
            async with session.get(
                url, auth=self._auth, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    raise MieleApiError(f"HTTP {resp.status} for {url}")
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise MieleApiError(str(exc) or type(exc).__name__) from exc

        try:
            return ET.fromstring(text)
        except ET.ParseError as exc:
            raise MieleApiError(f"XML parse error: {exc}") from exc

    async def get_appliances(self) -> list[MieleAppliance]:
        root = await self._get_xml(self._base + HOMEBUS_PATH)
        appliances: list[MieleAppliance] = []

        for dev in root.findall("device"):
            uid = _text(dev, "UID")
            appliance = MieleAppliance(
                uid=uid,
                device_class=_text(dev, "class"),
                device_type=_text(dev, "type"),
                name=_text(dev, "name"),
                state=_text(dev, "state"),
                additional_name=_text(dev, "additionalName"),
                room=_text(dev, "room"),
                info=_parse_keys(dev.find("information")),
                actions=_parse_actions(dev.find("actions")),
            )
            appliances.append(appliance)

        return appliances

    async def get_appliance_detail(self, detail_url: str) -> tuple[dict[str, str], list[MieleAction]]:
        """Fetch detail XML for a single appliance. detail_url may be relative."""
        url = detail_url if detail_url.startswith("http") else self._base + detail_url
        root = await self._get_xml(url)
        info = _parse_keys(root.find("information"))
        actions = _parse_actions(root.find("actions"))
        return info, actions

    async def trigger_action(self, action_url: str) -> bool:
        """Trigger an action. Returns True on success."""
        url = action_url if action_url.startswith("http") else self._base + action_url
        session = await self._get_session()
        try:
            async with session.get(
                url, auth=self._auth, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise MieleApiError(str(exc) or type(exc).__name__) from exc

        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise MieleApiError(f"XML parse error: {exc}") from exc

        if root.tag == "ok":
            return True
        msg = _text(root, "message") or root.tag
        raise MieleApiError(f"Action failed: {msg}")


def _text(parent: ET.Element | None, tag: str) -> str:
    if parent is None:
        return ""
    el = parent.find(tag)
    if el is None:
        return ""
    return (el.text or "").strip()


def _parse_keys(el: ET.Element | None) -> dict[str, str]:
    if el is None:
        return {}
    return {k.get("name", ""): k.get("value", "") for k in el.findall("key")}


def _parse_actions(el: ET.Element | None) -> list[MieleAction]:
    if el is None:
        return []
    return [
        MieleAction(name=a.get("name", ""), url=a.get("URL", ""))
        for a in el.findall("action")
    ]
