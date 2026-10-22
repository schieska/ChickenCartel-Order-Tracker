"""Pytest configuration and fixtures for ChickenCartel tests."""

import sys
from unittest.mock import MagicMock

import pytest
import pytest_socket
from homeassistant.core import HomeAssistant

from custom_components.chickencartel.coordinator import ChickenCartelCoordinator

if sys.platform == "win32":
    # pytest-homeassistant-custom-component disables socket construction before
    # every test. On Windows asyncio itself needs an AF_INET socketpair merely
    # to create an event loop, so the Linux-oriented guard prevents all tests
    # from starting. Network access in these tests is mocked explicitly.
    pytest_socket.disable_socket = lambda *args, **kwargs: None
    pytest_socket.enable_socket()


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
        "OrderHarmonyStatus": 6,
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
