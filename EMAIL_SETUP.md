# Email-Based Order ID Setup

This guide explains how to automatically extract order IDs from ChickenCartel order confirmation emails and update your tracker.

## Overview

The integration includes an email parser that can extract order IDs from incoming emails. When combined with Home Assistant's email integration, you can automatically update the order tracker whenever you receive a new order confirmation email.

## Setup Steps

### 1. Install IMAP Email Content Integration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **"IMAP Email Content"**
4. Configure your email account:
   - **IMAP Server**: Your email provider's IMAP server (e.g., `imap.gmail.com`)
   - **Port**: Usually `993` for SSL
   - **Username**: Your email address
   - **Password**: Your email password or app password
   - **Folder**: Usually `INBOX`

### 2. Configure Email Sensor

After installing IMAP Email Content, configure a sensor to monitor for ChickenCartel emails:

**Via YAML** (`configuration.yaml`):
```yaml
imap_email_content:
  - host: imap.gmail.com
    port: 993
    username: your_email@gmail.com
    password: your_app_password
    folder: INBOX
    senders:
      - noreply@chickencartel.nl
      - info@chickencartel.nl
    subjects:
      - "Order"
      - "Bestelling"
```

### 3. Create Automation

Create an automation that triggers when a new email is received and automatically extracts the order ID:

**Option A: Using the parse_email service (Recommended)**

```yaml
automation:
  - alias: "Auto-update Order ID from Email"
    description: "Automatically extract order ID from ChickenCartel emails"
    trigger:
      - platform: state
        entity_id: sensor.email_chickencartel
        # Trigger when email count changes (new email received)
    condition:
      - condition: template
        value_template: "{{ states('sensor.email_chickencartel') | int > 0 }}"
    action:
      - service: chickencartel.parse_email
        data:
          subject: "{{ state_attr('sensor.email_chickencartel', 'subject') }}"
          body: "{{ state_attr('sensor.email_chickencartel', 'body') }}"
          html_body: "{{ state_attr('sensor.email_chickencartel', 'html_body') | default('') }}"
          sender: "{{ state_attr('sensor.email_chickencartel', 'sender') }}"
          auto_update: true
```

**Option B: Using IMAP Email Content with Template Sensor**

```yaml
template:
  - sensor:
      - name: "ChickenCartel Order ID"
        state: >
          {% set email = states('sensor.email_chickencartel') %}
          {% if email | int > 0 %}
            {% set subject = state_attr('sensor.email_chickencartel', 'subject') | default('') %}
            {% set body = state_attr('sensor.email_chickencartel', 'body') | default('') %}
            {% set html = state_attr('sensor.email_chickencartel', 'html_body') | default('') %}
            {% set sender = state_attr('sensor.email_chickencartel', 'sender') | default('') %}
            {% set order_id = subject + ' ' + body + ' ' + html %}
            {{ order_id | regex_findall('([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', ignorecase=True) | first | default('') }}
          {% else %}
            unknown
          {% endif %}

automation:
  - alias: "Update Order ID from Email"
    trigger:
      - platform: state
        entity_id: sensor.chicken_cartel_order_id
        to: 
          - "unknown"
    condition:
      - condition: template
        value_template: "{{ states('sensor.chicken_cartel_order_id') != 'unknown' }}"
    action:
      - service: chickencartel.set_order_id
        data:
          order_id: "{{ states('sensor.chicken_cartel_order_id') }}"
```

**Option C: Using Webhook (for external email services)**

If you're using a service like Gmail API or a webhook service:

```yaml
automation:
  - alias: "Process Email Webhook"
    trigger:
      - platform: webhook
        webhook_id: chickencartel_email
    action:
      - service: chickencartel.parse_email
        data:
          subject: "{{ trigger.json.subject }}"
          body: "{{ trigger.json.body }}"
          html_body: "{{ trigger.json.html_body | default('') }}"
          sender: "{{ trigger.json.sender }}"
          auto_update: true
```

### 4. Manual Testing

You can test the email parser service manually:

**Via Developer Tools → Services:**
1. Go to **Developer Tools** → **Services**
2. Select `chickencartel.parse_email`
3. Fill in the service data:
   ```yaml
   subject: "Your Order Confirmation - Order 123e4567-e89b-12d3-a456-426614174000"
   body: "Thank you for your order. Order ID: 123e4567-e89b-12d3-a456-426614174000"
   sender: "noreply@chickencartel.nl"
   auto_update: true
   ```
4. Click **Call Service**

## Email Parser Features

The email parser can extract order IDs from:

- **Email subject lines**
- **Plain text email body**
- **HTML email body** (strips HTML tags automatically)
- **Email links/URLs**
- **Various formats**: "Order ID: <uuid>", "Order: <uuid>", "Bestelnummer: <uuid>", etc.

## Troubleshooting

### Order ID not being extracted

1. **Check email content**: Make sure the email actually contains a UUID
2. **Check sender**: The parser works better if the sender contains "chickencartel"
3. **Manual test**: Use the `chickencartel.parse_email` service to test with actual email content
4. **Check logs**: Look for warnings in Home Assistant logs about order ID extraction

### Automation not triggering

1. **Check sensor state**: Verify the email sensor is updating when emails arrive
2. **Check trigger**: Make sure the trigger entity ID matches your email sensor
3. **Check conditions**: Verify any conditions aren't blocking the automation

### Multiple order IDs found

If multiple UUIDs are found in an email, the parser will use the first valid one. To be more specific, you can:

1. Filter emails by subject line pattern
2. Use a template sensor to extract specific patterns
3. Manually call the service with specific email content

## Advanced: Custom Email Processing

For more control, you can create a custom automation that processes emails before calling the service:

```yaml
automation:
  - alias: "Smart Order ID Extraction"
    trigger:
      - platform: state
        entity_id: sensor.email_chickencartel
    action:
      - service: python_script.extract_order_id
        data:
          email_subject: "{{ state_attr('sensor.email_chickencartel', 'subject') }}"
          email_body: "{{ state_attr('sensor.email_chickencartel', 'body') }}"
      - service: chickencartel.set_order_id
        data:
          order_id: "{{ states('sensor.extracted_order_id') }}"
```

## Security Notes

- **Email credentials**: Store email passwords securely, consider using app passwords
- **IMAP access**: Ensure your email provider allows IMAP access
- **Rate limiting**: Be aware of email provider rate limits
- **Privacy**: Email content is processed locally in Home Assistant

## Example: Complete Setup

Here's a complete example configuration:

```yaml
# configuration.yaml
imap_email_content:
  - host: imap.gmail.com
    port: 993
    username: !secret email_username
    password: !secret email_password
    folder: INBOX
    senders:
      - noreply@chickencartel.nl

# automation.yaml
- id: auto_update_order_from_email
  alias: "Auto Update Order from Email"
  description: "Automatically update ChickenCartel order tracker when email received"
  trigger:
    - platform: state
      entity_id: sensor.email_chickencartel
  condition:
    - condition: template
      value_template: "{{ state_attr('sensor.email_chickencartel', 'sender') | lower | regex_search('chickencartel') }}"
  action:
    - service: chickencartel.parse_email
      data:
        subject: "{{ state_attr('sensor.email_chickencartel', 'subject') }}"
        body: "{{ state_attr('sensor.email_chickencartel', 'body') }}"
        html_body: "{{ state_attr('sensor.email_chickencartel', 'html_body') | default('') }}"
        sender: "{{ state_attr('sensor.email_chickencartel', 'sender') }}"
        auto_update: true
```
