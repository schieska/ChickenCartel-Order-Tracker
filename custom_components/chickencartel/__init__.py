"""ChickenCartel Order Tracker integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, entity_registry as er

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
from .coordinator import ChickenCartelCoordinator
from .config_flow import validate_order_id
from .email_monitor import EmailMonitor
from .email_parser import extract_order_id_from_email

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_SET_ORDER_ID = "set_order_id"

SERVICE_SET_ORDER_ID_SCHEMA = vol.Schema(
    {
        vol.Required("order_id"): cv.string,
        vol.Optional("entity_id"): cv.entity_ids,
    }
)

SERVICE_PARSE_EMAIL_SCHEMA = vol.Schema(
    {
        vol.Required("subject"): cv.string,
        vol.Optional("body"): cv.string,
        vol.Optional("html_body"): cv.string,
        vol.Optional("sender"): cv.string,
        vol.Optional("entity_id"): cv.entity_ids,
        vol.Optional("auto_update", default=True): cv.boolean,
    }
)

SERVICE_TEST_EMAIL_SCHEMA = vol.Schema(
    {
        vol.Required("subject"): cv.string,
        vol.Optional("body", default=""): cv.string,
        vol.Optional("html_body", default=""): cv.string,
        vol.Optional("sender", default="info@dehamburgerij.nl"): cv.string,
        vol.Optional("auto_update", default=False): cv.boolean,
    }
)

SERVICE_CHECK_EMAIL_NOW_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_id"): cv.entity_ids,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ChickenCartel Order Tracker from a config entry."""
    order_id = entry.data[CONF_ORDER_ID]
    polling_interval = entry.data.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)
    email_enabled = entry.data.get(CONF_EMAIL_ENABLED, False)

    coordinator = ChickenCartelCoordinator(
        hass,
        order_id=order_id,
        polling_interval=polling_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up email monitoring if enabled
    if email_enabled:
        async def on_order_id_found(new_order_id: str) -> None:
            """Callback when order ID is found in email."""
            _LOGGER.info("Email monitor found order ID: %s", new_order_id)
            # Update the coordinator with the new order ID
            await coordinator.update_order_id(new_order_id)
            # Update config entry
            hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, CONF_ORDER_ID: new_order_id},
                title=f"Order {new_order_id[:8]}... (Email Auto-Detect)",
            )

        email_monitor = EmailMonitor(
            hass=hass,
            server=entry.data[CONF_EMAIL_SERVER],
            port=entry.data.get(CONF_EMAIL_PORT, DEFAULT_EMAIL_PORT),
            username=entry.data[CONF_EMAIL_USERNAME],
            password=entry.data[CONF_EMAIL_PASSWORD],
            folder=entry.data.get(CONF_EMAIL_FOLDER, DEFAULT_EMAIL_FOLDER),
            check_interval=entry.data.get(CONF_EMAIL_CHECK_INTERVAL, DEFAULT_EMAIL_CHECK_INTERVAL),
            on_order_id_found=on_order_id_found,
        )
        
        # Store email monitor
        hass.data[DOMAIN][f"{entry.entry_id}_email"] = email_monitor
        
        # Start monitoring
        await email_monitor.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register service if not already registered
    if "_service_registered" not in hass.data[DOMAIN]:
        async def async_handle_set_order_id(call: ServiceCall) -> None:
            """Handle the set_order_id service call."""
            order_id = call.data["order_id"]
            entity_ids = call.data.get("entity_id")

            # Validate order ID format
            if not validate_order_id(order_id):
                _LOGGER.error("Invalid order ID format: %s", order_id)
                return

            order_id = order_id.strip().lower()

            # Find coordinators to update
            coordinators_to_update: list[tuple[str, ChickenCartelCoordinator]] = []

            if entity_ids:
                # Update specific entities
                entity_registry = er.async_get(hass)
                for entity_id in entity_ids:
                    # Find the entity and get its coordinator
                    entity = entity_registry.async_get(entity_id)
                    
                    if entity and entity.platform == DOMAIN:
                        # Find coordinator by matching unique_id pattern
                        # unique_id format: <entry_id>_order_status
                        if entity.unique_id and entity.unique_id.endswith("_order_status"):
                            entry_id = entity.unique_id.replace("_order_status", "")
                            if entry_id in hass.data[DOMAIN]:
                                coordinator = hass.data[DOMAIN][entry_id]
                                if isinstance(coordinator, ChickenCartelCoordinator):
                                    coordinators_to_update.append((entry_id, coordinator))
            else:
                # Update all coordinators
                for entry_id, coordinator in hass.data[DOMAIN].items():
                    if isinstance(coordinator, ChickenCartelCoordinator):
                        coordinators_to_update.append((entry_id, coordinator))

            # Update coordinators and config entries
            for entry_id, coordinator in coordinators_to_update:
                await coordinator.update_order_id(order_id)
                
                # Update config entry
                entry = hass.config_entries.async_get_entry(entry_id)
                if entry:
                    hass.config_entries.async_update_entry(
                        entry,
                        data={**entry.data, CONF_ORDER_ID: order_id},
                        title=f"Order {order_id[:8]}...",
                    )
                    _LOGGER.info("Updated order ID for entry %s", entry_id)

        async def async_handle_parse_email(call: ServiceCall) -> None:
            """Handle the parse_email service call to extract order ID from email."""
            subject = call.data.get("subject", "")
            body = call.data.get("body", "")
            html_body = call.data.get("html_body", "")
            sender = call.data.get("sender", "")
            entity_ids = call.data.get("entity_id")
            auto_update = call.data.get("auto_update", True)
            
            # Extract order ID from email
            order_id = extract_order_id_from_email(
                subject=subject,
                body=body,
                html_body=html_body,
                sender=sender,
            )
            
            if not order_id:
                _LOGGER.warning("No valid order ID found in email from %s", sender or "unknown")
                return
            
            _LOGGER.info("Extracted order ID %s from email", order_id[:8])
            
            # If auto_update is enabled, automatically update the order ID
            if auto_update:
                # Call the set_order_id service
                await async_handle_set_order_id(
                    ServiceCall(
                        DOMAIN,
                        SERVICE_SET_ORDER_ID,
                        {
                            "order_id": order_id,
                            "entity_id": entity_ids,
                        },
                    )
                )
            else:
                # Just return the order ID (could be used in automation)
                _LOGGER.info("Order ID extracted: %s (auto_update disabled)", order_id)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ORDER_ID,
            async_handle_set_order_id,
            schema=SERVICE_SET_ORDER_ID_SCHEMA,
        )
        async def async_handle_test_email(call: ServiceCall) -> None:
            """Handle the test_email service call to test email parsing."""
            subject = call.data.get("subject", "")
            body = call.data.get("body", "")
            html_body = call.data.get("html_body", "")
            sender = call.data.get("sender", "info@dehamburgerij.nl")
            auto_update = call.data.get("auto_update", False)
            
            _LOGGER.info("Testing email parsing with subject: %s", subject)
            
            # Extract order ID from email
            order_id = extract_order_id_from_email(
                subject=subject,
                body=body,
                html_body=html_body,
                sender=sender,
            )
            
            if not order_id:
                _LOGGER.warning("❌ Test failed: No valid order ID found in test email")
                # Store result for user feedback
                hass.bus.async_fire(
                    "chickencartel_test_email_result",
                    {
                        "success": False,
                        "message": "No order ID found in test email",
                        "subject": subject,
                    },
                )
                return
            
            _LOGGER.info("✅ Test successful: Found order ID %s", order_id)
            
            # Store result for user feedback
            hass.bus.async_fire(
                "chickencartel_test_email_result",
                {
                    "success": True,
                    "order_id": order_id,
                    "message": f"Successfully extracted order ID: {order_id}",
                    "subject": subject,
                },
            )
            
            # If auto_update is enabled, update the order ID
            if auto_update:
                await async_handle_set_order_id(
                    ServiceCall(
                        DOMAIN,
                        SERVICE_SET_ORDER_ID,
                        {"order_id": order_id},
                    )
                )

        async def async_handle_check_email_now(call: ServiceCall) -> None:
            """Handle the check_email_now service call to manually trigger email check."""
            entity_ids = call.data.get("entity_id")
            
            # Find email monitors to check
            monitors_to_check: list[EmailMonitor] = []
            
            if entity_ids:
                # Check specific entities
                entity_registry = er.async_get(hass)
                for entity_id in entity_ids:
                    entity = entity_registry.async_get(entity_id)
                    if entity and entity.platform == DOMAIN:
                        if entity.unique_id and entity.unique_id.endswith("_order_status"):
                            entry_id = entity.unique_id.replace("_order_status", "")
                            email_monitor_key = f"{entry_id}_email"
                            if email_monitor_key in hass.data[DOMAIN]:
                                monitor = hass.data[DOMAIN][email_monitor_key]
                                if isinstance(monitor, EmailMonitor):
                                    monitors_to_check.append(monitor)
            else:
                # Check all email monitors
                for key, value in hass.data[DOMAIN].items():
                    if key.endswith("_email") and isinstance(value, EmailMonitor):
                        monitors_to_check.append(value)
            
            if not monitors_to_check:
                _LOGGER.warning("No email monitors found to check")
                hass.bus.async_fire(
                    "chickencartel_check_email_result",
                    {
                        "success": False,
                        "message": "No email monitors configured",
                    },
                )
                return
            
            # Trigger check for each monitor
            for monitor in monitors_to_check:
                _LOGGER.info("Manually triggering email check")
                await monitor.async_request_refresh()
            
            hass.bus.async_fire(
                "chickencartel_check_email_result",
                {
                    "success": True,
                    "message": f"Checking {len(monitors_to_check)} email monitor(s)",
                    "count": len(monitors_to_check),
                },
            )

        hass.services.async_register(
            DOMAIN,
            "parse_email",
            async_handle_parse_email,
            schema=SERVICE_PARSE_EMAIL_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            "test_email",
            async_handle_test_email,
            schema=SERVICE_TEST_EMAIL_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            "check_email_now",
            async_handle_check_email_now,
            schema=SERVICE_CHECK_EMAIL_NOW_SCHEMA,
        )
        hass.data[DOMAIN]["_service_registered"] = True

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Clean up email monitor if it exists
        email_monitor_key = f"{entry.entry_id}_email"
        if email_monitor_key in hass.data[DOMAIN]:
            email_monitor = hass.data[DOMAIN][email_monitor_key]
            if isinstance(email_monitor, EmailMonitor):
                await email_monitor.async_shutdown()
            hass.data[DOMAIN].pop(email_monitor_key)
        
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
