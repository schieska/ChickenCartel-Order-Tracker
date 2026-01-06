"""Pytest configuration and fixtures for ChickenCartel tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.chickencartel.coordinator import ChickenCartelCoordinator


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    return hass


@pytest.fixture
def sample_order_id():
    """Sample valid order ID."""
    return "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def sample_api_response():
    """Sample API response data."""
    return {
        "OrderHarmonyStatus": 4,
        "OrderId": "123e4567-e89b-12d3-a456-426614174000",
        "OrderNumber": "12345",
    }


@pytest.fixture
def coordinator(mock_hass, sample_order_id):
    """Create a coordinator instance for testing."""
    return ChickenCartelCoordinator(
        hass=mock_hass,
        order_id=sample_order_id,
        polling_interval=15,
    )
