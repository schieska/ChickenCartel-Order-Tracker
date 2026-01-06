"""Tests for config flow."""

from unittest.mock import patch

import pytest
from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.chickencartel.config_flow import (
    ChickenCartelConfigFlow,
    validate_order_id,
)




class TestValidateOrderId:
    """Test order ID validation."""

    def test_valid_uuid(self):
        """Test valid UUID formats."""
        valid_ids = [
            "123e4567-e89b-12d3-a456-426614174000",
            "123E4567-E89B-12D3-A456-426614174000",
            "00000000-0000-0000-0000-000000000000",
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
        ]
        for order_id in valid_ids:
            assert validate_order_id(order_id) is True

    def test_invalid_uuid(self):
        """Test invalid UUID formats."""
        invalid_ids = [
            "not-a-uuid",
            "123e4567-e89b-12d3-a456",  # Too short
            "123e4567-e89b-12d3-a456-426614174000-extra",  # Too long
            "123e4567e89b12d3a456426614174000",  # Missing dashes
            "",
            "   ",
        ]
        for order_id in invalid_ids:
            assert validate_order_id(order_id) is False

    def test_uuid_with_whitespace(self):
        """Test UUID with leading/trailing whitespace."""
        assert validate_order_id("  123e4567-e89b-12d3-a456-426614174000  ") is True
        assert validate_order_id("  123e4567-e89b-12d3-a456-426614174000") is True
        assert validate_order_id("123e4567-e89b-12d3-a456-426614174000  ") is True


class TestConfigFlow:
    """Test config flow."""

    async def test_user_step_valid_input(self, hass: HomeAssistant):
        """Test successful config flow with valid input."""
        flow = ChickenCartelConfigFlow()
        flow.hass = hass
        flow.init_data = {}

        result = await flow.async_step_user(
            user_input={
                "order_id": "123e4567-e89b-12d3-a456-426614174000",
                "polling_interval": 20,
            }
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"]["order_id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert result["data"]["polling_interval"] == 20
        assert result["title"] == "Order 123e4567..."

    async def test_user_step_default_polling_interval(self, hass: HomeAssistant):
        """Test config flow with default polling interval."""
        flow = ChickenCartelConfigFlow()
        flow.hass = hass
        flow.init_data = {}

        result = await flow.async_step_user(
            user_input={
                "order_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"]["polling_interval"] == 15  # Default value

    async def test_user_step_invalid_order_id(self, hass: HomeAssistant):
        """Test config flow with invalid order ID."""
        flow = ChickenCartelConfigFlow()
        flow.hass = hass
        flow.init_data = {}

        result = await flow.async_step_user(
            user_input={
                "order_id": "invalid-uuid",
                "polling_interval": 15,
            }
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_order_id"

    async def test_user_step_duplicate_order(self, hass: HomeAssistant):
        """Test config flow with duplicate order ID."""
        flow = ChickenCartelConfigFlow()
        flow.hass = hass
        flow.init_data = {}

        order_id = "123e4567-e89b-12d3-a456-426614174000"

        # First entry
        result1 = await flow.async_step_user(
            user_input={
                "order_id": order_id,
                "polling_interval": 15,
            }
        )
        assert result1["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

        # Second entry with same order ID
        flow2 = ChickenCartelConfigFlow()
        flow2.hass = hass
        flow2.init_data = {}

        # Mock existing entries
        with patch.object(
            flow2, "async_set_unique_id", return_value=None
        ), patch.object(flow2, "_abort_if_unique_id_configured") as mock_abort:
            mock_abort.side_effect = data_entry_flow.AbortFlow("already_configured")

            result2 = await flow2.async_step_user(
                user_input={
                    "order_id": order_id,
                    "polling_interval": 15,
                }
            )

            # Should abort due to duplicate
            assert mock_abort.called

    async def test_user_step_order_id_normalization(self, hass: HomeAssistant):
        """Test that order ID is normalized to lowercase."""
        flow = ChickenCartelConfigFlow()
        flow.hass = hass
        flow.init_data = {}

        result = await flow.async_step_user(
            user_input={
                "order_id": "123E4567-E89B-12D3-A456-426614174000",
                "polling_interval": 15,
            }
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"]["order_id"] == "123e4567-e89b-12d3-a456-426614174000"

    async def test_user_step_form_display(self, hass: HomeAssistant):
        """Test that form is displayed correctly."""
        flow = ChickenCartelConfigFlow()
        flow.hass = hass
        flow.init_data = {}

        result = await flow.async_step_user(user_input=None)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert "data_schema" in result

    async def test_polling_interval_validation(self, hass: HomeAssistant):
        """Test polling interval validation."""
        flow = ChickenCartelConfigFlow()
        flow.hass = hass
        flow.init_data = {}

        # Test minimum value
        result = await flow.async_step_user(
            user_input={
                "order_id": "123e4567-e89b-12d3-a456-426614174000",
                "polling_interval": 5,
            }
        )
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

        # Test maximum value
        result = await flow.async_step_user(
            user_input={
                "order_id": "123e4567-e89b-12d3-a456-426614174001",
                "polling_interval": 300,
            }
        )
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
