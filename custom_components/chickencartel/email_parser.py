"""Email parser for extracting ChickenCartel order IDs from emails."""

from __future__ import annotations

import re
from typing import Any

from .config_flow import UUID_PATTERN, validate_order_id

# Common patterns for finding order IDs in emails
ORDER_ID_PATTERNS = [
    # Direct UUID pattern
    UUID_PATTERN,
    # Order ID: <uuid>
    re.compile(r"order\s*id[:\s]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE),
    # Order: <uuid>
    re.compile(r"order[:\s]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE),
    # Bestelnummer: <uuid> (Dutch)
    re.compile(r"bestelnummer[:\s]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE),
    # UUID in URLs
    re.compile(r"chickencartel\.nl.*?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE),
    # UUID in links
    re.compile(r"href=[\"']?[^\"']*?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE),
]


def extract_order_id_from_text(text: str) -> str | None:
    """Extract order ID (UUID) from text content.
    
    Args:
        text: Text content to search for order ID
        
    Returns:
        Order ID if found, None otherwise
    """
    if not text:
        return None
    
    # Try each pattern
    for pattern in ORDER_ID_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            # Get the first match and validate it
            order_id = matches[0] if isinstance(matches[0], str) else str(matches[0])
            if validate_order_id(order_id):
                return order_id.strip().lower()
    
    return None


def extract_order_id_from_email(
    subject: str | None = None,
    body: str | None = None,
    html_body: str | None = None,
    sender: str | None = None,
) -> str | None:
    """Extract order ID from email content.
    
    Args:
        subject: Email subject line
        body: Plain text email body
        html_body: HTML email body
        sender: Email sender address
        
    Returns:
        Order ID if found, None otherwise
    """
    # Check if email is from ChickenCartel
    is_chickencartel_email = False
    if sender:
        sender_lower = sender.lower()
        is_chickencartel_email = (
            "chickencartel" in sender_lower or
            "noreply@chickencartel" in sender_lower or
            "@chickencartel.nl" in sender_lower or
            "dehamburgerij.nl" in sender_lower  # ChickenCartel uses this domain
        )
    
    # Combine all text sources
    text_sources = []
    
    if subject:
        text_sources.append(subject)
    
    if body:
        text_sources.append(body)
    
    if html_body:
        # First, search the raw HTML directly (for href attributes and URLs)
        order_id = extract_order_id_from_text(html_body)
        if order_id:
            return order_id
        
        # Extract URLs from href attributes
        href_urls = re.findall(r'href=["\']?([^"\'>\s]+)', html_body, re.IGNORECASE)
        for url in href_urls:
            text_sources.append(url)
        
        # Also extract text from HTML (simple approach)
        # Remove HTML tags and normalize whitespace
        html_text = re.sub(r"<[^>]+>", " ", html_body)
        html_text = re.sub(r"\s+", " ", html_text).strip()
        text_sources.append(html_text)
    
    # Search all text sources
    combined_text = " ".join(text_sources)
    
    order_id = extract_order_id_from_text(combined_text)
    
    if order_id:
        return order_id
    
    # If not found and it's a ChickenCartel email, try more aggressive search
    if is_chickencartel_email and combined_text:
        # Look for any UUID in the text
        uuid_matches = UUID_PATTERN.findall(combined_text)
        if uuid_matches:
            for match in uuid_matches:
                if validate_order_id(match):
                    return match.strip().lower()
    
    return None
