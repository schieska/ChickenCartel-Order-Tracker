"""Tests for Chicken Cartel email monitoring."""

from unittest.mock import AsyncMock, MagicMock

import aioimaplib
import pytest

from custom_components.chickencartel.email_monitor import (
    EmailMonitor,
    _extract_message_bytes,
)

ORDER_ID = "68b9e014-3378-4bb3-b121-5a5200d1453b"


def _monitor(mock_hass, callback: AsyncMock | None = None) -> EmailMonitor:
    """Create an email monitor for tests."""
    return EmailMonitor(
        hass=mock_hass,
        server="imap.example.com",
        port=993,
        username="user@example.com",
        password="app-password",
        folder="INBOX",
        check_interval=60,
        on_order_id_found=callback or AsyncMock(),
    )


def test_extract_message_bytes_from_aioimaplib_response() -> None:
    """The FETCH literal, rather than response metadata, is returned."""
    message = b"Subject: test\r\n\r\nbody"
    lines = [
        f"1 FETCH (UID 10 BODY[] {{{len(message)}}}".encode(),
        bytearray(message),
        b")",
        b"FETCH completed.",
    ]

    assert _extract_message_bytes(lines) == message


@pytest.mark.asyncio
async def test_process_email_extracts_order_from_fetch_literal(mock_hass) -> None:
    """A real aioimaplib-style FETCH response is parsed correctly."""
    callback = AsyncMock()
    monitor = _monitor(mock_hass, callback)
    message = (
        "From: The Chicken Cartel <info@dehamburgerij.nl>\r\n"
        "Subject: Uw bestelling bij The Chicken Cartel\r\n"
        "MIME-Version: 1.0\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "\r\n"
        f'<a href="https://www.chickencartel.nl/orders/{ORDER_ID}/status">'
        "Volg mijn bestelling</a>"
    ).encode()
    response = aioimaplib.Response(
        "OK",
        [
            f"1 FETCH (UID 10 BODY.PEEK[] {{{len(message)}}}".encode(),
            bytearray(message),
            b")",
            b"FETCH completed.",
        ],
    )
    monitor._imap_client = MagicMock()
    monitor._imap_client.uid = AsyncMock(return_value=response)

    assert await monitor._process_email("10") == ORDER_ID
    callback.assert_awaited_once_with(ORDER_ID)
    monitor._imap_client.uid.assert_awaited_once_with("FETCH", "10", "(BODY.PEEK[])")


@pytest.mark.asyncio
async def test_check_emails_uses_latest_matching_order(mock_hass) -> None:
    """Read emails are searched and the newest valid order wins."""
    monitor = _monitor(mock_hass)
    monitor._imap_client = MagicMock()
    monitor._imap_client.select = AsyncMock(
        return_value=aioimaplib.Response("OK", [b"1"])
    )
    monitor._imap_client.uid_search = AsyncMock(
        return_value=aioimaplib.Response("OK", [b"10 20"])
    )
    monitor._process_email = AsyncMock(side_effect=[None, ORDER_ID])

    await monitor._check_emails()

    assert monitor._process_email.await_args_list[0].args == ("20",)
    assert monitor._process_email.await_args_list[1].args == ("10",)
    assert monitor._last_uid == 20
