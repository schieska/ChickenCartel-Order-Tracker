"""Tests for sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.chickencartel.coordinator import ChickenCartelCoordinator
from custom_components.chickencartel.sensor import (
    ChickenCartelOrderSensor,
    async_setup_entry,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    return entry


@pytest.fixture
def coordinator(mock_hass):
    """Create a coordinator instance for testing."""
    return ChickenCartelCoordinator(
        hass=mock_hass,
        order_id="123e4567-e89b-12d3-a456-426614174000",
        polling_interval=15,
    )


@pytest.fixture
def sensor(coordinator, mock_entry):
    """Create a sensor instance for testing."""
    return ChickenCartelOrderSensor(coordinator, mock_entry)


class TestChickenCartelOrderSensor:
    """Test sensor functionality."""

    def test_sensor_initialization(self, sensor, coordinator, mock_entry):
        """Test sensor initialization."""
        assert sensor.coordinator == coordinator
        assert sensor._entry == mock_entry
        assert sensor._attr_name == "Order Status"
        assert sensor._attr_icon == "mdi:food"
        assert sensor._attr_unique_id == f"{mock_entry.entry_id}_order_status"
        assert sensor._attr_has_entity_name is True

    def test_device_info(self, sensor, coordinator, mock_entry):
        """Test device info."""
        device_info = sensor._attr_device_info
        assert device_info["identifiers"] == {("chickencartel", mock_entry.entry_id)}
        assert device_info["name"] == f"ChickenCartel Order {coordinator.order_id[:8]}"
        assert device_info["manufacturer"] == "ChickenCartel"
        assert device_info["model"] == "Order Tracker"

    def test_native_value_with_data(self, sensor, coordinator):
        """Test native_value property with data."""
        coordinator.data = {"status": "preparing"}
        assert sensor.native_value == "preparing"

    def test_native_value_no_data(self, sensor, coordinator):
        """Test native_value property without data."""
        coordinator.data = None
        assert sensor.native_value is None

    def test_native_value_unknown_status(self, sensor, coordinator):
        """Test native_value with unknown status."""
        coordinator.data = {"status": "unknown"}
        assert sensor.native_value == "unknown"

    def test_extra_state_attributes_with_data(self, sensor, coordinator):
        """Test extra_state_attributes with data."""
        coordinator.data = {
            "order_id": "123e4567-e89b-12d3-a456-426614174000",
            "order_harmony_status": 4,
            "status": "preparing",
        }
        coordinator._polling_active = True

        attrs = sensor.extra_state_attributes

        assert attrs["order_id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert attrs["order_harmony_status"] == 4
        assert attrs["polling_active"] is True

    def test_extra_state_attributes_with_error(self, sensor, coordinator):
        """Test extra_state_attributes with error."""
        coordinator.data = {
            "order_id": "123e4567-e89b-12d3-a456-426614174000",
            "status": "unknown",
            "error": "Order not found",
        }
        coordinator._polling_active = False

        attrs = sensor.extra_state_attributes

        assert attrs["error"] == "Order not found"
        assert attrs["polling_active"] is False

    def test_extra_state_attributes_no_data(self, sensor, coordinator):
        """Test extra_state_attributes without data."""
        coordinator.data = None

        attrs = sensor.extra_state_attributes

        assert attrs == {}

    def test_available_with_data(self, sensor, coordinator):
        """Test available property with data."""
        coordinator.data = {"status": "preparing"}
        assert sensor.available is True

    def test_available_no_data(self, sensor, coordinator):
        """Test available property without data."""
        coordinator.data = None
        assert sensor.available is False

    def test_available_with_error(self, sensor, coordinator):
        """Test available property with error data."""
        coordinator.data = {
            "status": "unknown",
            "error": "Order not found",
        }
        # Entity should still be available even with error
        assert sensor.available is True


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_entry(self, mock_hass, mock_entry, coordinator):
        """Test setting up sensor entry."""
        mock_hass.data["chickencartel"] = {mock_entry.entry_id: coordinator}
        mock_add_entities = MagicMock()

        await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

        mock_add_entities.assert_called_once()
        # Check that a sensor was added
        call_args = mock_add_entities.call_args[0][0]
        assert len(call_args) == 1
        assert isinstance(call_args[0], ChickenCartelOrderSensor)
