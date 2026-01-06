# ChickenCartel Order Tracker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Track your ChickenCartel food delivery orders directly in Home Assistant. Get real-time status updates and trigger automations based on order state changes.

## Features

- **Real-time tracking** — Automatically polls for order status updates
- **Smart polling** — Stops automatically when order is completed, cancelled, or failed
- **UI configuration** — No YAML required, configure entirely through the Home Assistant UI
- **Automation ready** — Trigger notifications, lights, or any automation based on order state
- **HACS compatible** — Easy installation through the Home Assistant Community Store

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add this repository URL and select **Integration** as the category
4. Click **Add**
5. Search for "ChickenCartel Order Tracker" and install
6. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/chickencartel` folder from this repository
2. Copy it to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "ChickenCartel Order Tracker"
4. Enter your order ID (UUID from your order confirmation)
5. Optionally adjust the polling interval (default: 15 seconds)

### Automatic Order ID from Email (Built-in)

The integration includes **built-in email monitoring** - no need to install separate integrations or create automations!

**Setup:**
1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration** → **ChickenCartel Order Tracker**
3. Enter any order ID (or leave a placeholder)
4. **Enable "Email Auto-Detect"**
5. Configure your email settings:
   - **Email Server**: `imap.gmail.com` (or your provider)
   - **Port**: `993` (SSL)
   - **Username**: Your email address
   - **Password**: Your email password or app password
   - **Folder**: `INBOX` (default)
   - **Check Interval**: How often to check for emails (default: 60 seconds)

That's it! The integration will automatically:
- Monitor your inbox for ChickenCartel order confirmation emails
- Extract order IDs from incoming emails
- Update the tracker automatically when a new order is detected

**Note:** For Gmail, you'll need to use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

**Forwarded Emails:** The integration also works with forwarded emails! If you forward ChickenCartel order emails to yourself, or if emails come from your own address, the integration will detect them as long as they contain ChickenCartel-related content (subject, URLs, or keywords).

### Testing Email Parsing

You can test the email parser with a test email using the `chickencartel.test_email` service:

**Via Developer Tools → Services:**
1. Go to **Developer Tools** → **Services**
2. Select `chickencartel.test_email`
3. Fill in test data:
   ```yaml
   subject: "Uw bestelling bij The Chicken Cartel"
   html_body: "<a href='https://www.chickencartel.nl/orders/68b9e014-3378-4bb3-b121-5a5200d1453b/status'>View order</a>"
   sender: "info@dehamburgerij.nl"
   auto_update: false
   ```
4. Click **Call Service**

The service will:
- Extract the order ID from your test email
- Log the result (check logs for success/failure)
- Fire an event `chickencartel_test_email_result` with the result
- Optionally update the tracker if `auto_update: true`

You can also manually trigger email checking with `chickencartel.check_email_now` to force an immediate check of your inbox.

**Alternative:** If you prefer to use the IMAP Email Content integration or handle emails manually, you can still use the `chickencartel.parse_email` service. See [EMAIL_SETUP.md](EMAIL_SETUP.md) for advanced options.

## Entity

The integration creates one sensor entity:

### `sensor.chickencartel_order_status`

| Attribute | Description |
|-----------|-------------|
| **State** | Human-readable order status |
| `order_id` | The order UUID |
| `order_harmony_status` | Raw status integer from API |
| `polling_active` | Whether automatic updates are active |

### Possible States

| State | Description |
|-------|-------------|
| `received` | Order received by system |
| `pos` | Order sent to point of sale |
| `accepted` | Order accepted by restaurant |
| `preparing` | Food is being prepared |
| `waiting_for_driver` | Ready, waiting for delivery driver |
| `en_route` | Driver is on the way |
| `completed` | Order delivered ✓ |
| `cancelled` | Order was cancelled |
| `failed` | Order failed |
| `unknown` | Status unknown or API error |

## Automation Examples

### Notify when food is on the way

```yaml
automation:
  - alias: "Food delivery en route"
    trigger:
      - platform: state
        entity_id: sensor.chickencartel_order_status
        to: "en_route"
    action:
      - service: notify.mobile_app
        data:
          title: "🍗 Food Update"
          message: "Your ChickenCartel order is on the way!"
```

### Flash lights when order is ready for pickup

```yaml
automation:
  - alias: "Order waiting for driver"
    trigger:
      - platform: state
        entity_id: sensor.chickencartel_order_status
        to: "waiting_for_driver"
    action:
      - service: light.turn_on
        target:
          entity_id: light.kitchen
        data:
          flash: short
```

### Announce on speakers when delivered

```yaml
automation:
  - alias: "Food delivered announcement"
    trigger:
      - platform: state
        entity_id: sensor.chickencartel_order_status
        to: "completed"
    action:
      - service: tts.speak
        target:
          entity_id: tts.google_en
        data:
          media_player_entity_id: media_player.living_room
          message: "Your chicken has arrived!"
```

## Dashboard Card Example

```yaml
type: entities
title: Food Delivery
entities:
  - entity: sensor.chickencartel_order_status
    name: Order Status
    icon: mdi:food-drumstick
```

Or with a Mushroom chip:

```yaml
type: custom:mushroom-chips-card
chips:
  - type: entity
    entity: sensor.chickencartel_order_status
    icon: mdi:moped
    content_info: state
```

## FAQ

**Q: Where do I find my order ID?**  
A: The order ID is the UUID in your order confirmation email or the URL when viewing your order status. You can also set up automatic extraction from emails (see [EMAIL_SETUP.md](EMAIL_SETUP.md)).

**Q: Can I automatically update the order ID from emails?**  
A: Yes! The integration includes an email parser service. Set up the IMAP Email Content integration and create an automation that calls `chickencartel.parse_email` when emails arrive. See [EMAIL_SETUP.md](EMAIL_SETUP.md) for details.

**Q: Does polling continue forever?**  
A: No, polling automatically stops when the order reaches a final state (completed, cancelled, or failed).

**Q: Can I track multiple orders?**  
A: Currently, the integration supports one order at a time. Add multiple integration instances to track multiple orders.

**Q: What happens if the API is unreachable?**  
A: The sensor will show "unknown" state and retry on the next polling interval.

## Privacy

- No authentication required
- No personal data is stored outside Home Assistant
- Order ID is stored locally in your Home Assistant config only

## License

MIT License - See [LICENSE](LICENSE) for details.

## Testing

The integration includes a comprehensive test suite. To run the tests:

1. Install test dependencies:
   ```bash
   pip install -r requirements_test.txt
   ```

2. Run all tests:
   ```bash
   pytest
   ```

3. Run specific test files:
   ```bash
   pytest tests/test_config_flow.py
   pytest tests/test_coordinator.py
   pytest tests/test_sensor.py
   ```

4. Run with coverage:
   ```bash
   pytest --cov=custom_components.chickencartel --cov-report=html
   ```

See `tests/README.md` for more detailed testing information.

## Contributing

Contributions are welcome! Please open an issue or pull request.
