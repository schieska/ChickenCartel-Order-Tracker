"""Tests for __init__.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.chickencartel import async_setup_entry, async_unload_entry
from custom_components.chickencartel.const import DOMAIN


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "order_id": "123e4567-e89b-12d3-a456-426614174000",
        "polling_interval": 15,
    }
    return entry


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_entry_success(self, mock_hass, mock_entry):
        """Test successful setup entry."""
        with patch(
            "custom_components.chickencartel.ChickenCartelCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            assert DOMAIN in mock_hass.data
            assert mock_entry.entry_id in mock_hass.data[DOMAIN]
            mock_coordinator.async_config_entry_first_refresh.assert_called_once()
            mock_hass.config_entries.async_forward_entry_setups.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_with_default_polling_interval(
        self, mock_hass, mock_entry
    ):
        """Test setup entry with default polling interval."""
        mock_entry.data = {"order_id": "123e4567-e89b-12d3-a456-426614174000"}

        with patch(
            "custom_components.chickencartel.ChickenCartelCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator

            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            # Verify coordinator was created with default polling interval
            call_args = mock_coordinator_class.call_args
            assert call_args[1]["polling_interval"] == 15


class TestAsyncUnloadEntry:
    """Test async_unload_entry function."""

    @pytest.mark.asyncio
    async def test_unload_entry_success(self, mock_hass, mock_entry):
        """Test successful unload entry."""
        mock_hass.data[DOMAIN] = {mock_entry.entry_id: MagicMock()}
        mock_hass.config_entries.async_unload_platforms.return_value = True

        result = await async_unload_entry(mock_hass, mock_entry)

        assert result is True
        assert mock_entry.entry_id not in mock_hass.data[DOMAIN]
        mock_hass.config_entries.async_unload_platforms.assert_called_once()

    @pytest.mark.asyncio
    async def test_unload_entry_failure(self, mock_hass, mock_entry):
        """Test unload entry failure."""
        mock_hass.data[DOMAIN] = {mock_entry.entry_id: MagicMock()}
        mock_hass.config_entries.async_unload_platforms.return_value = False

        result = await async_unload_entry(mock_hass, mock_entry)

        assert result is False
        # Entry should still be in data if unload failed
        assert mock_entry.entry_id in mock_hass.data[DOMAIN]
