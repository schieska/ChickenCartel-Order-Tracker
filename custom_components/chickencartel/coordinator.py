"""DataUpdateCoordinator for ChickenCartel Order Tracker."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_BASE_URL, FINAL_STATES, STATUS_MAP

_LOGGER = logging.getLogger(__name__)


class ChickenCartelCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch ChickenCartel order status."""

    def __init__(
        self,
        hass: HomeAssistant,
        order_id: str,
        polling_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="ChickenCartel Order Status",
            update_interval=timedelta(seconds=polling_interval),
        )
        self.order_id = order_id
        self._polling_interval = polling_interval
        self._polling_active = True

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the ChickenCartel API."""
        # If polling has stopped, return last known data
        if not self._polling_active and self.data:
            return self.data

        url = f"{API_BASE_URL}/{self.order_id}/status"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 404:
                        _LOGGER.warning("Order %s not found", self.order_id)
                        return {
                            "order_id": self.order_id,
                            "order_harmony_status": None,
                            "status": "unknown",
                            "error": "Order not found",
                        }

                    if response.status != 200:
                        raise UpdateFailed(f"API returned status {response.status}")

                    data = await response.json()

        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching order status: %s", err)
            return {
                "order_id": self.order_id,
                "order_harmony_status": None,
                "status": "unknown",
                "error": str(err),
            }

        # Parse the OrderHarmonyStatus
        harmony_status = data.get("OrderHarmonyStatus")
        status = STATUS_MAP.get(harmony_status, "unknown")

        result = {
            "order_id": self.order_id,
            "order_harmony_status": harmony_status,
            "status": status,
            "raw_data": data,
        }

        # Stop polling if we've reached a final state
        if status in FINAL_STATES:
            _LOGGER.info(
                "Order %s reached final state '%s', stopping polling",
                self.order_id,
                status,
            )
            self._stop_polling()

        return result

    def _stop_polling(self) -> None:
        """Stop automatic polling."""
        self._polling_active = False
        self.update_interval = None

    @property
    def is_polling_active(self) -> bool:
        """Return whether polling is still active."""
        return self._polling_active

    async def update_order_id(self, new_order_id: str) -> None:
        """Update the order ID and restart polling."""
        if new_order_id.strip().lower() == self.order_id.lower():
            _LOGGER.debug("Order ID unchanged, skipping update")
            return

        old_order_id = self.order_id
        self.order_id = new_order_id.strip().lower()
        
        _LOGGER.info(
            "Order ID updated from %s to %s, restarting polling",
            old_order_id[:8],
            self.order_id[:8],
        )
        
        # Reset polling state
        self._polling_active = True
        self.update_interval = timedelta(seconds=self._polling_interval)
        
        # Clear existing data
        self.data = None
        
        # Force immediate update
        await self.async_request_refresh()