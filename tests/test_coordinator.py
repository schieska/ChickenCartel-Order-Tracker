"""Tests for coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.chickencartel.coordinator import ChickenCartelCoordinator
from custom_components.chickencartel.const import FINAL_STATES, STATUS_MAP


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    return hass


@pytest.fixture
def coordinator(mock_hass):
    """Create a coordinator instance for testing."""
    return ChickenCartelCoordinator(
        hass=mock_hass,
        order_id="123e4567-e89b-12d3-a456-426614174000",
        polling_interval=15,
    )


class TestChickenCartelCoordinator:
    """Test coordinator functionality."""

    @pytest.mark.asyncio
    async def test_successful_api_call(self, coordinator, sample_api_response):
        """Test successful API call."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=sample_api_response)
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await coordinator._async_update_data()

            assert result["order_id"] == coordinator.order_id
            assert result["order_harmony_status"] == 4
            assert result["status"] == "preparing"
            assert "raw_data" in result

    @pytest.mark.asyncio
    async def test_api_404_response(self, coordinator):
        """Test handling of 404 response."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await coordinator._async_update_data()

            assert result["order_id"] == coordinator.order_id
            assert result["status"] == "unknown"
            assert result["error"] == "Order not found"
            assert result["order_harmony_status"] is None

    @pytest.mark.asyncio
    async def test_api_error_response(self, coordinator):
        """Test handling of API error response."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_network_error(self, coordinator):
        """Test handling of network errors."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Connection error")

            result = await coordinator._async_update_data()

            assert result["order_id"] == coordinator.order_id
            assert result["status"] == "unknown"
            assert "error" in result
            assert result["order_harmony_status"] is None

    @pytest.mark.asyncio
    async def test_status_mapping(self, coordinator):
        """Test all status mappings."""
        for harmony_status, expected_status in STATUS_MAP.items():
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(
                    return_value={"OrderHarmonyStatus": harmony_status}
                )
                mock_get.return_value.__aenter__.return_value = mock_response

                result = await coordinator._async_update_data()

                assert result["status"] == expected_status
                assert result["order_harmony_status"] == harmony_status

    @pytest.mark.asyncio
    async def test_unknown_status(self, coordinator):
        """Test handling of unknown status code."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"OrderHarmonyStatus": 999})
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await coordinator._async_update_data()

            assert result["status"] == "unknown"
            assert result["order_harmony_status"] == 999

    @pytest.mark.asyncio
    async def test_final_state_stops_polling(self, coordinator):
        """Test that final states stop polling."""
        for final_state in FINAL_STATES:
            # Reset coordinator
            coordinator._polling_active = True
            coordinator.update_interval = timedelta(seconds=coordinator._polling_interval)

            harmony_status = next(
                k for k, v in STATUS_MAP.items() if v == final_state
            )

            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(
                    return_value={"OrderHarmonyStatus": harmony_status}
                )
                mock_get.return_value.__aenter__.return_value = mock_response

                await coordinator._async_update_data()

                assert coordinator.is_polling_active is False
                assert coordinator.update_interval is None

    @pytest.mark.asyncio
    async def test_non_final_state_continues_polling(self, coordinator):
        """Test that non-final states continue polling."""
        non_final_statuses = [
            status for status in STATUS_MAP.values() if status not in FINAL_STATES
        ]

        for status in non_final_statuses:
            # Reset coordinator
            coordinator._polling_active = True
            coordinator.update_interval = timedelta(seconds=coordinator._polling_interval)

            harmony_status = next(
                k for k, v in STATUS_MAP.items() if v == status
            )

            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(
                    return_value={"OrderHarmonyStatus": harmony_status}
                )
                mock_get.return_value.__aenter__.return_value = mock_response

                await coordinator._async_update_data()

                assert coordinator.is_polling_active is True

    @pytest.mark.asyncio
    async def test_stopped_polling_returns_last_data(self, coordinator):
        """Test that stopped polling returns last known data."""
        # Set up initial data
        coordinator.data = {
            "order_id": coordinator.order_id,
            "status": "completed",
            "order_harmony_status": 7,
        }
        coordinator._polling_active = False

        result = await coordinator._async_update_data()

        assert result == coordinator.data

    def test_polling_active_property(self, coordinator):
        """Test polling_active property."""
        coordinator._polling_active = True
        assert coordinator.is_polling_active is True

        coordinator._polling_active = False
        assert coordinator.is_polling_active is False

    def test_stop_polling(self, coordinator):
        """Test stop polling method."""
        coordinator._polling_active = True
        coordinator.update_interval = timedelta(seconds=coordinator._polling_interval)

        coordinator._stop_polling()

        assert coordinator._polling_active is False
        assert coordinator.update_interval is None
