"""Sensor platform for ChickenCartel Order Tracker."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ChickenCartelCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChickenCartel sensor from a config entry."""
    coordinator: ChickenCartelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ChickenCartelOrderSensor(coordinator, entry)])


class ChickenCartelOrderSensor(CoordinatorEntity[ChickenCartelCoordinator], SensorEntity):
    """Sensor representing ChickenCartel order status."""

    _attr_has_entity_name = True
    _attr_name = "Order Status"
    _attr_icon = "mdi:food"

    def __init__(
        self,
        coordinator: ChickenCartelCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_order_status"
        self._update_device_info()

    def _update_device_info(self) -> None:
        """Update device info with current order ID."""
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": f"ChickenCartel Order {self.coordinator.order_id[:8]}",
            "manufacturer": "ChickenCartel",
            "model": "Order Tracker",
        }

    @property
    def native_value(self) -> str | None:
        """Return the current order status."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("status", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if self.coordinator.data is None:
            return {}

        attrs = {
            "order_id": self.coordinator.data.get("order_id"),
            "order_harmony_status": self.coordinator.data.get("order_harmony_status"),
            "polling_active": self.coordinator.is_polling_active,
        }

        # Include error info if present
        if "error" in self.coordinator.data:
            attrs["error"] = self.coordinator.data["error"]

        return attrs

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Entity is available even if API returns error (shows as 'unknown')
        return self.coordinator.data is not None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Store original order ID to detect changes
        self._last_order_id = self.coordinator.order_id
        # Add listener for order ID changes
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update to refresh device info if order ID changed."""
        # Check if order ID changed and update device info
        if hasattr(self, '_last_order_id') and self.coordinator.order_id != self._last_order_id:
            self._last_order_id = self.coordinator.order_id
            self._update_device_info()
        # Always write state (CoordinatorEntity handles this, but we override to add device info update)
        self.async_write_ha_state()
