"""Config flow for ChickenCartel Order Tracker integration."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import aioimaplib
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a manual order ID or opt into email auto-detection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            order_id = user_input.get(CONF_ORDER_ID, "").strip().lower()
            email_enabled = user_input.get(CONF_EMAIL_ENABLED, False)

            if order_id and not validate_order_id(order_id):
                errors[CONF_ORDER_ID] = "invalid_order_id"
            elif not order_id and not email_enabled:
                errors[CONF_ORDER_ID] = "order_id_or_email_required"
            else:
                normalized_order_id = order_id or "pending-email-detection"
                self._email_data = {
                    CONF_ORDER_ID: normalized_order_id,
                    CONF_POLLING_INTERVAL: user_input.get(
                        CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
                    ),
                }

                if email_enabled:
                    return await self.async_step_email()

                await self.async_set_unique_id(normalized_order_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Order {normalized_order_id[:8]}...",
                    data={
                        **self._email_data,
                        CONF_EMAIL_ENABLED: False,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_ORDER_ID, default=""): str,
                    vol.Optional(
                        CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                    vol.Optional(CONF_EMAIL_ENABLED, default=False): bool,
                }
            ),
            errors=errors,
        )

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
                test_client: aioimaplib.IMAP4_SSL | None = None
                try:
                    # Test connection with timeout
                    test_client = aioimaplib.IMAP4_SSL(
                        server, user_input.get(CONF_EMAIL_PORT, DEFAULT_EMAIL_PORT)
                    )

                    # Wait for server hello with timeout
                    await asyncio.wait_for(
                        test_client.wait_hello_from_server(), timeout=10.0
                    )

                    # Test login
                    login_response = await asyncio.wait_for(
                        test_client.login(username, password), timeout=10.0
                    )
                    if login_response.result != "OK":
                        raise aioimaplib.IMAP4.error("Authentication failed")

                    # Test folder access
                    folder = user_input.get(CONF_EMAIL_FOLDER, DEFAULT_EMAIL_FOLDER)
                    select_response = await asyncio.wait_for(
                        test_client.select(folder), timeout=5.0
                    )
                    if select_response.result != "OK":
                        raise aioimaplib.IMAP4.error(
                            f"Unable to select email folder: {folder}"
                        )

                    # Search for emails containing "chickencartel" in headers
                    # Search in subject, from, and body
                    try:
                        search_response = await asyncio.wait_for(
                            test_client.uid_search(
                                "OR",
                                "FROM",
                                '"dehamburgerij.nl"',
                                "SUBJECT",
                                '"Chicken Cartel"',
                            ),
                            timeout=5.0,
                        )
                        if search_response.result == "OK":
                            email_count = (
                                len(search_response.lines[0].split())
                                if search_response.lines
                                else 0
                            )
                            _LOGGER.info(
                                "Found %d ChickenCartel email(s) in %s",
                                email_count,
                                folder,
                            )
                            if email_count == 0:
                                # Don't fail, but log a warning - user might not have emails yet
                                _LOGGER.info(
                                    "No ChickenCartel emails found yet - this is OK if you haven't received any order confirmations"
                                )
                    except (
                        aioimaplib.IMAP4.error,
                        aioimaplib.Abort,
                        OSError,
                        TimeoutError,
                    ) as search_err:
                        _LOGGER.debug(
                            "Email search test failed (non-critical): %s", search_err
                        )
                        # Don't fail on search - connection is what matters

                    _LOGGER.info("Email connection test successful for %s", username)

                except TimeoutError:
                    errors["base"] = "email_connection_timeout"
                    _LOGGER.error("Email connection test timed out for %s", server)
                except aioimaplib.IMAP4.error as err:
                    error_msg = str(err)
                    if (
                        "authentication failed" in error_msg.lower()
                        or "invalid credentials" in error_msg.lower()
                    ):
                        errors["base"] = "email_authentication_failed"
                    elif "connection refused" in error_msg.lower():
                        errors["base"] = "email_connection_refused"
                    else:
                        errors["base"] = "email_connection_failed"
                    _LOGGER.error("Email connection test failed: %s", err)
                except (aioimaplib.Abort, OSError, ValueError) as err:
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
                    order_id = self._email_data.get(
                        CONF_ORDER_ID, "pending-email-detection"
                    )

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
                finally:
                    if test_client is not None:
                        try:
                            await test_client.logout()
                        except (aioimaplib.IMAP4.error, aioimaplib.Abort, OSError):
                            _LOGGER.debug("Unable to close the test IMAP connection")

        # Show email configuration form
        return self.async_show_form(
            step_id="email",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL_SERVER, default="imap.gmail.com"): str,
                    vol.Required(CONF_EMAIL_PORT, default=DEFAULT_EMAIL_PORT): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                    vol.Required(CONF_EMAIL_USERNAME): str,
                    vol.Required(CONF_EMAIL_PASSWORD): str,
                    vol.Optional(CONF_EMAIL_FOLDER, default=DEFAULT_EMAIL_FOLDER): str,
                    vol.Optional(
                        CONF_EMAIL_CHECK_INTERVAL, default=DEFAULT_EMAIL_CHECK_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
                }
            ),
            errors=errors,
        )
