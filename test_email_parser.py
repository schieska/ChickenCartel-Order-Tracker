"""Quick test script for email parser functionality."""

import sys
sys.path.insert(0, '.')

from custom_components.chickencartel.email_parser import extract_order_id_from_email

def test_direct_chickencartel_email():
    """Test parsing email directly from ChickenCartel."""
    result = extract_order_id_from_email(
        subject="Uw bestelling bij The Chicken Cartel",
        html_body='<a href="https://www.chickencartel.nl/orders/68b9e014-3378-4bb3-b121-5a5200d1453b/status">View order</a>',
        sender="info@dehamburgerij.nl"
    )
    expected = "68b9e014-3378-4bb3-b121-5a5200d1453b"
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"[PASS] Test 1 - Direct ChickenCartel email: {result}")
    return True

def test_forwarded_email():
    """Test parsing forwarded email from self."""
    result = extract_order_id_from_email(
        subject="Fwd: Uw bestelling bij The Chicken Cartel",
        html_body='<a href="https://www.chickencartel.nl/orders/123e4567-e89b-12d3-a456-426614174000/status">View order</a>',
        sender="your-email@gmail.com"
    )
    expected = "123e4567-e89b-12d3-a456-426614174000"
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"[PASS] Test 2 - Forwarded email (from self): {result}")
    return True

def test_non_chickencartel_email():
    """Test that non-ChickenCartel emails return None."""
    result = extract_order_id_from_email(
        subject="Random email",
        html_body="No order here",
        sender="spam@example.com"
    )
    assert result is None, f"Expected None, got {result}"
    print(f"[PASS] Test 3 - Non-ChickenCartel email: {result}")
    return True

def test_email_with_order_id_in_subject():
    """Test parsing order ID from subject line."""
    result = extract_order_id_from_email(
        subject="Your order 68b9e014-3378-4bb3-b121-5a5200d1453b",
        body="Thank you for your order",
        sender="info@dehamburgerij.nl"
    )
    expected = "68b9e014-3378-4bb3-b121-5a5200d1453b"
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"[PASS] Test 4 - Order ID in subject: {result}")
    return True

if __name__ == "__main__":
    print("Running email parser tests...\n")
    
    try:
        test_direct_chickencartel_email()
        test_forwarded_email()
        test_non_chickencartel_email()
        test_email_with_order_id_in_subject()
        
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
