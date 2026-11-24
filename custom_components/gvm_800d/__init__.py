"""GVM 800D RGB integration."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .ble import GvmBleClient, GvmBleError
from .const import CONF_MAC, DOMAIN, PLATFORMS


class GvmDeviceCoordinator:
    """Coordinate one light connection and its Home Assistant listeners."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: GvmBleClient | None = None,
    ) -> None:
        """Initialize the coordinator for a config entry."""
        self.hass = hass
        self.entry = entry
        self.mac = entry.data[CONF_MAC]
        self.client = client or GvmBleClient(
            self.mac,
            on_handshake=self._on_handshake,
            on_state=self._on_state,
        )
        self.handshake: dict[str, Any] | None = None
        self.state: dict[str, Any] = {}
        self._available = False
        self._handshake_event = asyncio.Event()
        self._listeners: list[Callable[[], None]] = []
        self._pending: dict[int, int] = {}
        self._write_task: asyncio.Task[None] | None = None
        self._reconnect_task: asyncio.Task[None] | None = None

    @property
    def available(self) -> bool:
        """Return whether the light is connected."""
        return self._available

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a state listener and return a remove callback."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _notify_listeners(self) -> None:
        """Notify registered listeners of new state."""
        for listener in list(self._listeners):
            listener()

    def _on_handshake(self, handshake: dict[str, Any]) -> None:
        """Store handshake data and unblock setup."""
        self.handshake = handshake
        self._handshake_event.set()

    def _on_state(self, state: dict[str, Any]) -> None:
        """Store state and notify entities."""
        self.state.update(state)
        self._available = True
        self._notify_listeners()

    async def async_connect(self) -> None:
        """Connect and wait for a valid handshake."""
        self._handshake_event.clear()
        await self.client.async_connect()
        try:
            await asyncio.wait_for(self._handshake_event.wait(), 10)
        except TimeoutError as err:
            raise GvmBleError("handshake timeout") from err
        self._available = True
        self._notify_listeners()

    async def async_request(self, cmd: int, value: int) -> None:
        """Queue the latest value for a command."""
        self._pending[cmd] = value
        if self._write_task is None or self._write_task.done():
            self._write_task = asyncio.create_task(self._drain_writes())
        await self._write_task

    async def _drain_writes(self) -> None:
        """Write the latest queued value for each command."""
        while self._pending:
            pending = dict(self._pending)
            self._pending.clear()
            for cmd, value in pending.items():
                try:
                    await self.client.send_command(cmd, value)
                except Exception:
                    self._available = False
                    self._notify_listeners()
                    self._schedule_reconnect()
                    return

    def _schedule_reconnect(self) -> None:
        """Start a reconnect loop if one is not already running."""
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Reconnect with capped exponential backoff."""
        delay = 5
        while True:
            await asyncio.sleep(delay)
            try:
                await self.async_connect()
                return
            except Exception:
                delay = min(delay * 2, 30)

    async def async_shutdown(self) -> None:
        """Cancel background work and disconnect."""
        for task in (self._write_task, self._reconnect_task):
            if task is not None and not task.done():
                task.cancel()
        await self.client.async_disconnect()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GVM 800D RGB from a config entry."""
    coordinator = GvmDeviceCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    try:
        await coordinator.async_connect()
    except Exception as err:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise ConfigEntryNotReady from err
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a GVM 800D RGB config entry."""
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
