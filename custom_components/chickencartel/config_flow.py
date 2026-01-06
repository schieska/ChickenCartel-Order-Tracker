"""Config flow for ChickenCartel Order Tracker integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant

from .const import (
    CONF_EMAIL_CHECK_INTERVAL,
    CONF_EMAIL_ENABLED,
    CONF_EMAIL_FOLDER,
    CONF_EMAIL_PASSWORD,
    CONF_EMAIL_PORT,
    CONF_EMAIL_SERVER,
    CONF_EMAIL_USERNAME,
    CONF_ORDER_ID,
    CONF_POLLING_INTERVAL,
    DEFAULT_EMAIL_CHECK_INTERVAL,
    DEFAULT_EMAIL_FOLDER,
    DEFAULT_EMAIL_PORT,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# UUID regex pattern for order ID validation
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def validate_order_id(order_id: str) -> bool:
    """Validate that the order ID is a valid UUID."""
    return bool(UUID_PATTERN.match(order_id.strip()))


class ChickenCartelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ChickenCartel Order Tracker."""

    VERSION = 2

    async def async_migrate_entry(self, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate old config entries to new format."""
        if self.VERSION == 2 and CONF_EMAIL_ENABLED not in data:
            # Add default email settings for old entries
            data[CONF_EMAIL_ENABLED] = False
        return data

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - always proceed to email configuration."""
        # Skip the initial step and go directly to email configuration
        # Store any optional order ID if provided
        self._email_data = {
            CONF_POLLING_INTERVAL: DEFAULT_POLLING_INTERVAL,
            CONF_ORDER_ID: "pending-email-detection",
        }
        return await self.async_step_email()

    async def async_step_email(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle email configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate email configuration
            server = user_input.get(CONF_EMAIL_SERVER, "").strip()
            username = user_input.get(CONF_EMAIL_USERNAME, "").strip()
            password = user_input.get(CONF_EMAIL_PASSWORD, "").strip()

            if not server:
                errors[CONF_EMAIL_SERVER] = "email_server_required"
            elif not username:
                errors[CONF_EMAIL_USERNAME] = "email_username_required"
            elif not password:
                errors[CONF_EMAIL_PASSWORD] = "email_password_required"
            else:
                # Test email connection and verify ChickenCartel emails can be found
                try:
                    import aioimaplib
                    import asyncio
                    
                    # Test connection with timeout
                    test_client = aioimaplib.IMAP4_SSL(
                        server, user_input.get(CONF_EMAIL_PORT, DEFAULT_EMAIL_PORT)
                    )
                    
                    # Wait for server hello with timeout
                    await asyncio.wait_for(
                        test_client.wait_hello_from_server(),
                        timeout=10.0
                    )
                    
                    # Test login
                    await asyncio.wait_for(
                        test_client.login(username, password),
                        timeout=10.0
                    )
                    
                    # Test folder access
                    folder = user_input.get(CONF_EMAIL_FOLDER, DEFAULT_EMAIL_FOLDER)
                    await asyncio.wait_for(
                        test_client.select(folder),
                        timeout=5.0
                    )
                    
                    # Search for emails containing "chickencartel" in headers
                    # Search in subject, from, and body
                    search_query = '(OR (SUBJECT "chickencartel") (FROM "chickencartel") (BODY "chickencartel"))'
                    try:
                        status, messages = await asyncio.wait_for(
                            test_client.search(search_query),
                            timeout=5.0
                        )
                        if status == "OK":
                            email_count = len(messages[0].split()) if messages[0] else 0
                            _LOGGER.info("Found %d ChickenCartel email(s) in %s", email_count, folder)
                            if email_count == 0:
                                # Don't fail, but log a warning - user might not have emails yet
                                _LOGGER.info("No ChickenCartel emails found yet - this is OK if you haven't received any order confirmations")
                    except Exception as search_err:
                        _LOGGER.debug("Email search test failed (non-critical): %s", search_err)
                        # Don't fail on search - connection is what matters
                    
                    # Clean logout
                    try:
                        await test_client.logout()
                    except Exception:
                        pass  # Ignore logout errors
                    
                    _LOGGER.info("Email connection test successful for %s", username)
                    
                except asyncio.TimeoutError:
                    errors["base"] = "email_connection_timeout"
                    _LOGGER.error("Email connection test timed out for %s", server)
                except aioimaplib.IMAP4.error as err:
                    error_msg = str(err)
                    if "authentication failed" in error_msg.lower() or "invalid credentials" in error_msg.lower():
                        errors["base"] = "email_authentication_failed"
                    elif "connection refused" in error_msg.lower():
                        errors["base"] = "email_connection_refused"
                    else:
                        errors["base"] = "email_connection_failed"
                    _LOGGER.error("Email connection test failed: %s", err)
                except Exception as err:
                    error_msg = str(err).lower()
                    if "timeout" in error_msg or "timed out" in error_msg:
                        errors["base"] = "email_connection_timeout"
                    elif "connection" in error_msg and "refused" in error_msg:
                        errors["base"] = "email_connection_refused"
                    elif "ssl" in error_msg or "certificate" in error_msg:
                        errors["base"] = "email_ssl_error"
                    else:
                        errors["base"] = "email_connection_failed"
                    _LOGGER.error("Email connection test failed: %s", err)
                else:
                    # Success - create entry
                    order_id = self._email_data.get(CONF_ORDER_ID, "pending-email-detection")
                    
                    # Use a unique ID based on email username if no order ID yet
                    if order_id == "pending-email-detection":
                        unique_id = f"email-{username.lower()}"
                    else:
                        unique_id = order_id.lower()
                    
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    title = "Email Auto-Detect"
                    if order_id != "pending-email-detection":
                        title = f"Order {order_id[:8]}... (Email Auto-Detect)"

                    return self.async_create_entry(
                        title=title,
                        data={
                            **self._email_data,
                            CONF_EMAIL_ENABLED: True,
                            CONF_EMAIL_SERVER: server,
                            CONF_EMAIL_PORT: user_input.get(
                                CONF_EMAIL_PORT, DEFAULT_EMAIL_PORT
                            ),
                            CONF_EMAIL_USERNAME: username,
                            CONF_EMAIL_PASSWORD: password,
                            CONF_EMAIL_FOLDER: user_input.get(
                                CONF_EMAIL_FOLDER, DEFAULT_EMAIL_FOLDER
                            ),
                            CONF_EMAIL_CHECK_INTERVAL: user_input.get(
                                CONF_EMAIL_CHECK_INTERVAL, DEFAULT_EMAIL_CHECK_INTERVAL
                            ),
                        },
                    )

        # Show email configuration form
        return self.async_show_form(
            step_id="email",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL_SERVER, default="imap.gmail.com"
                    ): str,
                    vol.Required(CONF_EMAIL_PORT, default=DEFAULT_EMAIL_PORT): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                    vol.Required(CONF_EMAIL_USERNAME): str,
                    vol.Required(CONF_EMAIL_PASSWORD): str,
                    vol.Optional(
                        CONF_EMAIL_FOLDER, default=DEFAULT_EMAIL_FOLDER
                    ): str,
                    vol.Optional(
                        CONF_EMAIL_CHECK_INTERVAL, default=DEFAULT_EMAIL_CHECK_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
                }
            ),
            errors=errors,
        )
