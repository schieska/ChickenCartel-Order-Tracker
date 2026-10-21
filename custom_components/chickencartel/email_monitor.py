"""Email monitor for automatically detecting order confirmation emails."""

from __future__ import annotations

import email
import logging
import re
from collections.abc import Awaitable, Callable, Sequence
from datetime import timedelta
from email.header import decode_header, make_header
from typing import Any

import aioimaplib
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .email_parser import extract_order_id_from_email

_LOGGER = logging.getLogger(__name__)

_LITERAL_SIZE_PATTERN = re.compile(rb"\{(?P<size>\d+)\}$")


def _extract_message_bytes(response_lines: Sequence[bytes | bytearray]) -> bytes:
    """Extract the RFC822 literal from an aioimaplib FETCH response."""
    for index, line in enumerate(response_lines[:-1]):
        if not isinstance(line, (bytes, bytearray)):
            continue

        match = _LITERAL_SIZE_PATTERN.search(bytes(line))
        if not match:
            continue

        payload = response_lines[index + 1]
        if not isinstance(payload, (bytes, bytearray)):
            continue

        expected_size = int(match.group("size"))
        payload_bytes = bytes(payload)
        if len(payload_bytes) < expected_size:
            raise ValueError("Incomplete email returned by the IMAP server")
        return payload_bytes[:expected_size]

    raise ValueError("IMAP FETCH response did not contain an email body")


def _decode_header(value: str | None) -> str:
    """Decode an RFC 2047 email header."""
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (LookupError, UnicodeError):
        return value


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
        on_order_id_found: Callable[[str], Awaitable[None]],
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the email monitor."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="ChickenCartel Email Monitor",
            update_interval=timedelta(seconds=check_interval),
        )
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.folder = folder
        self._on_order_id_found = on_order_id_found
        self._last_uid: int | None = None
        self._imap_client: aioimaplib.IMAP4_SSL | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Check for new emails and extract order IDs."""
        try:
            await self._check_emails()
            return {"status": "monitoring", "last_check": dt_util.utcnow().isoformat()}
        except (
            aioimaplib.IMAP4.error,
            aioimaplib.Abort,
            OSError,
            TimeoutError,
            ValueError,
        ) as err:
            _LOGGER.error("Error checking emails: %s", err)
            return {"status": "error", "error": str(err)}

    async def _check_emails(self) -> None:
        """Check for new emails and process them."""
        try:
            # Connect to IMAP server
            if not self._imap_client:
                self._imap_client = aioimaplib.IMAP4_SSL(self.server, self.port)
                await self._imap_client.wait_hello_from_server()
                response = await self._imap_client.login(self.username, self.password)
                if response.result != "OK":
                    raise aioimaplib.IMAP4.error("Authentication failed")

            # Select the folder
            response = await self._imap_client.select(self.folder)
            if response.result != "OK":
                raise aioimaplib.IMAP4.error(
                    f"Unable to select email folder: {self.folder}"
                )

            # Search by stable UIDs and include read mail. Looking only for UNSEEN
            # messages misses an order whenever the user opens the email first.
            response = await self._imap_client.uid_search(
                "OR",
                "FROM",
                '"dehamburgerij.nl"',
                "SUBJECT",
                '"Chicken Cartel"',
            )

            if response.result != "OK" or not response.lines:
                return

            email_uids = sorted(
                int(token) for token in response.lines[0].split() if token.isdigit()
            )
            new_uids = [
                uid
                for uid in email_uids
                if self._last_uid is None or uid > self._last_uid
            ]
            if not new_uids:
                return

            # Work newest-first and stop after the newest valid order. Review
            # emails share the same sender but do not contain an order UUID.
            for uid in reversed(new_uids):
                order_id = await self._process_email(str(uid))
                if order_id:
                    break

            self._last_uid = max(new_uids)

        except aioimaplib.IMAP4.error as err:
            _LOGGER.error("IMAP error: %s", err)
            self._imap_client = None
            raise
        except (aioimaplib.Abort, OSError, TimeoutError, ValueError) as err:
            _LOGGER.error("Unexpected error checking emails: %s", err)
            self._imap_client = None
            raise

    async def _process_email(self, uid: str) -> str | None:
        """Process a single email and extract order ID."""
        if self._imap_client is None:
            return None

        response = await self._imap_client.uid("FETCH", uid, "(BODY.PEEK[])")
        if response.result != "OK" or not response.lines:
            return None

        email_body = _extract_message_bytes(response.lines)
        msg = email.message_from_bytes(email_body)

        # Extract email parts
        subject = _decode_header(msg.get("Subject"))
        sender = _decode_header(msg.get("From"))

        # Check if email is from ChickenCartel or forwarded from yourself
        sender_lower = sender.lower()
        username_lower = self.username.lower()

        is_chickencartel_sender = (
            "chickencartel" in sender_lower
            or "dehamburgerij.nl" in sender_lower
            or "@chickencartel.nl" in sender_lower
        )

        is_from_self = username_lower in sender_lower

        subject_lower = subject.lower()
        has_chickencartel_subject = (
            "chickencartel" in subject_lower
            or "chicken cartel" in subject_lower
            or "bestelling" in subject_lower
            or "order" in subject_lower
        )

        # Process email if:
        # 1. It's from ChickenCartel directly, OR
        # 2. It's from yourself AND has ChickenCartel-related subject/content
        if not is_chickencartel_sender and not (
            is_from_self and has_chickencartel_subject
        ):
            _LOGGER.debug(
                "Skipping email from %s (not ChickenCartel and not forwarded from self)",
                sender,
            )
            return None

        if is_from_self and not is_chickencartel_sender:
            _LOGGER.debug("Processing forwarded email from %s (self)", sender)

        body_parts: list[str] = []
        html_parts: list[str] = []

        if msg.is_multipart():
            parts = msg.walk()
        else:
            parts = (msg,)

        for part in parts:
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            charset = part.get_content_charset() or "utf-8"
            content = payload.decode(charset, errors="replace")
            if content_type == "text/plain":
                body_parts.append(content)
            elif content_type == "text/html":
                html_parts.append(content)

        body = "\n".join(body_parts)
        html_body = "\n".join(html_parts)

        if is_from_self and not is_chickencartel_sender:
            combined_content = f"{subject} {body} {html_body}".lower()
            has_chickencartel_content = (
                "chickencartel" in combined_content
                or "chicken cartel" in combined_content
                or "chickencartel.nl" in combined_content
                or "dehamburgerij" in combined_content
                or "/orders/" in combined_content
            )

            if not has_chickencartel_content:
                _LOGGER.debug(
                    "Skipping email from self - no ChickenCartel content found"
                )
                return None

        order_id = extract_order_id_from_email(
            subject=subject,
            body=body,
            html_body=html_body,
            sender=sender,
        )

        if not order_id:
            _LOGGER.debug("No order ID found in email from %s", sender)
            return None

        _LOGGER.info("Found order ID %s in email from %s", order_id, sender)
        await self._on_order_id_found(order_id)
        return order_id

    async def async_shutdown(self) -> None:
        """Close IMAP connection."""
        if self._imap_client:
            try:
                await self._imap_client.logout()
            except (aioimaplib.IMAP4.error, aioimaplib.Abort, OSError):
                _LOGGER.debug("Unable to close the IMAP connection")
            self._imap_client = None
