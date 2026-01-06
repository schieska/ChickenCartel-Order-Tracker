"""Email monitor for automatically detecting order confirmation emails."""

from __future__ import annotations

import asyncio
import email
import logging
from datetime import datetime, timedelta
from typing import Any, Callable

import aioimaplib
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_EMAIL_CHECK_INTERVAL, DEFAULT_EMAIL_FOLDER, DEFAULT_EMAIL_PORT
from .email_parser import extract_order_id_from_email

_LOGGER = logging.getLogger(__name__)


class EmailMonitor(DataUpdateCoordinator[dict[str, Any]]):
    """Monitor email inbox for ChickenCartel order confirmation emails."""

    def __init__(
        self,
        hass: HomeAssistant,
        server: str,
        port: int,
        username: str,
        password: str,
        folder: str,
        check_interval: int,
        on_order_id_found: Callable[[str], Any],
    ) -> None:
        """Initialize the email monitor."""
        super().__init__(
            hass,
            _LOGGER,
            name="ChickenCartel Email Monitor",
            update_interval=timedelta(seconds=check_interval),
        )
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.folder = folder
        self._on_order_id_found = on_order_id_found
        self._last_uid = None
        self._imap_client: aioimaplib.IMAP4_SSL | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Check for new emails and extract order IDs."""
        try:
            await self._check_emails()
            return {"status": "monitoring", "last_check": datetime.now().isoformat()}
        except Exception as err:
            _LOGGER.error("Error checking emails: %s", err)
            return {"status": "error", "error": str(err)}

    async def _check_emails(self) -> None:
        """Check for new emails and process them."""
        try:
            # Connect to IMAP server
            if not self._imap_client:
                self._imap_client = aioimaplib.IMAP4_SSL(self.server, self.port)
                await self._imap_client.wait_hello_from_server()
                await self._imap_client.login(self.username, self.password)

            # Select the folder
            await self._imap_client.select(self.folder)

            # Search for unread emails
            status, messages = await self._imap_client.search("UNSEEN")
            
            if status != "OK" or not messages[0]:
                return

            # Get list of email UIDs
            email_uids = messages[0].split()
            
            # Process new emails
            for uid in email_uids:
                uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
                
                # Skip if we've already processed this email
                if self._last_uid and int(uid_str) <= int(self._last_uid):
                    continue
                
                try:
                    await self._process_email(uid_str)
                    self._last_uid = uid_str
                except Exception as err:
                    _LOGGER.warning("Error processing email UID %s: %s", uid_str, err)

        except aioimaplib.IMAP4.error as err:
            _LOGGER.error("IMAP error: %s", err)
            # Reset connection on error
            self._imap_client = None
        except Exception as err:
            _LOGGER.error("Unexpected error checking emails: %s", err)
            self._imap_client = None

    async def _process_email(self, uid: str) -> None:
        """Process a single email and extract order ID."""
        try:
            # Fetch email
            status, msg_data = await self._imap_client.fetch(uid, "(RFC822)")
            
            if status != "OK" or not msg_data:
                return

            # Parse email
            email_body = msg_data[0][1]
            if isinstance(email_body, bytes):
                msg = email.message_from_bytes(email_body)
            else:
                msg = email.message_from_string(email_body)

            # Extract email parts
            subject = msg.get("Subject", "")
            sender = msg.get("From", "")
            
            # Check if email is from ChickenCartel or forwarded from yourself
            sender_lower = sender.lower()
            username_lower = self.username.lower()
            
            # Check if sender is ChickenCartel
            is_chickencartel_sender = (
                "chickencartel" in sender_lower or
                "dehamburgerij.nl" in sender_lower or
                "@chickencartel.nl" in sender_lower
            )
            
            # Check if email is from yourself (forwarded or sent to yourself)
            is_from_self = (
                username_lower in sender_lower or
                sender_lower in username_lower
            )
            
            # Check subject for ChickenCartel keywords (for forwarded emails)
            subject_lower = subject.lower()
            has_chickencartel_subject = (
                "chickencartel" in subject_lower or
                "bestelling" in subject_lower or
                "order" in subject_lower
            )
            
            # Process email if:
            # 1. It's from ChickenCartel directly, OR
            # 2. It's from yourself AND has ChickenCartel-related subject/content
            if not is_chickencartel_sender and not (is_from_self and has_chickencartel_subject):
                _LOGGER.debug("Skipping email from %s (not ChickenCartel and not forwarded from self)", sender)
                return
            
            if is_from_self and not is_chickencartel_sender:
                _LOGGER.debug("Processing forwarded email from %s (self)", sender)

            # Extract body content
            body = ""
            html_body = ""
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    # Skip attachments
                    if "attachment" in content_disposition:
                        continue
                    
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            content = payload.decode(charset, errors="ignore")
                            
                            if content_type == "text/plain":
                                body = content
                            elif content_type == "text/html":
                                html_body = content
                    except Exception as err:
                        _LOGGER.debug("Error decoding email part: %s", err)
            else:
                # Single part email
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or "utf-8"
                        content = payload.decode(charset, errors="ignore")
                        content_type = msg.get_content_type()
                        
                        if content_type == "text/plain":
                            body = content
                        elif content_type == "text/html":
                            html_body = content
                except Exception as err:
                    _LOGGER.debug("Error decoding email: %s", err)

            # For emails from self, also check content for ChickenCartel indicators
            if is_from_self and not is_chickencartel_sender:
                # Check if content contains ChickenCartel-related keywords
                combined_content = f"{subject} {body} {html_body}".lower()
                has_chickencartel_content = (
                    "chickencartel" in combined_content or
                    "chickencartel.nl" in combined_content or
                    "dehamburgerij" in combined_content or
                    "/orders/" in combined_content  # Order tracking URLs
                )
                
                if not has_chickencartel_content:
                    _LOGGER.debug("Skipping email from self - no ChickenCartel content found")
                    return

            # Extract order ID
            order_id = extract_order_id_from_email(
                subject=subject,
                body=body,
                html_body=html_body,
                sender=sender,
            )

            if order_id:
                _LOGGER.info("Found order ID %s in email from %s", order_id, sender)
                # Call the callback to update the order ID
                if self._on_order_id_found:
                    await self._on_order_id_found(order_id)
            else:
                _LOGGER.debug("No order ID found in email from %s", sender)

        except Exception as err:
            _LOGGER.error("Error processing email UID %s: %s", uid, err)

    async def async_shutdown(self) -> None:
        """Close IMAP connection."""
        if self._imap_client:
            try:
                await self._imap_client.logout()
            except Exception:
                pass
            self._imap_client = None
