"""Tests for constants."""

from custom_components.chickencartel.const import (
    API_BASE_URL,
    CONF_ORDER_ID,
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    FINAL_STATES,
    STATUS_MAP,
)


class TestConstants:
    """Test constants values."""

    def test_domain(self):
        """Test domain constant."""
        assert DOMAIN == "chickencartel"

    def test_config_keys(self):
        """Test config key constants."""
        assert CONF_ORDER_ID == "order_id"
        assert CONF_POLLING_INTERVAL == "polling_interval"

    def test_default_polling_interval(self):
        """Test default polling interval."""
        assert DEFAULT_POLLING_INTERVAL == 15

    def test_api_base_url(self):
        """Test API base URL."""
        assert API_BASE_URL == "https://www.chickencartel.nl/ordersjson"

    def test_status_map(self):
        """Test status mapping."""
        assert STATUS_MAP[-1] == "failed"
        assert STATUS_MAP[0] == "cancelled"
        assert STATUS_MAP[1] == "received"
        assert STATUS_MAP[2] == "pos"
        assert STATUS_MAP[3] == "accepted"
        assert STATUS_MAP[4] == "preparing"
        assert STATUS_MAP[5] == "waiting_for_driver"
        assert STATUS_MAP[6] == "en_route"
        assert STATUS_MAP[7] == "completed"

    def test_final_states(self):
        """Test final states."""
        assert "completed" in FINAL_STATES
        assert "cancelled" in FINAL_STATES
        assert "failed" in FINAL_STATES
        assert len(FINAL_STATES) == 3

    def test_final_states_match_status_map(self):
        """Test that final states exist in status map."""
        for final_state in FINAL_STATES:
            assert final_state in STATUS_MAP.values()
