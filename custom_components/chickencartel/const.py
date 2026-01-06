"""Constants for the ChickenCartel Order Tracker integration."""

DOMAIN = "chickencartel"

CONF_ORDER_ID = "order_id"
CONF_POLLING_INTERVAL = "polling_interval"

# Email monitoring configuration
CONF_EMAIL_ENABLED = "email_enabled"
CONF_EMAIL_SERVER = "email_server"
CONF_EMAIL_PORT = "email_port"
CONF_EMAIL_USERNAME = "email_username"
CONF_EMAIL_PASSWORD = "email_password"
CONF_EMAIL_FOLDER = "email_folder"
CONF_EMAIL_CHECK_INTERVAL = "email_check_interval"

DEFAULT_POLLING_INTERVAL = 15  # seconds
DEFAULT_EMAIL_CHECK_INTERVAL = 60  # seconds
DEFAULT_EMAIL_PORT = 993
DEFAULT_EMAIL_FOLDER = "INBOX"

API_BASE_URL = "https://www.chickencartel.nl/ordersjson"

# Status mapping from OrderHarmonyStatus integer to human-readable state
STATUS_MAP = {
    -1: "failed",
    0: "cancelled",
    1: "received",
    2: "pos",
    3: "accepted",
    4: "preparing",
    5: "waiting_for_driver",
    6: "en_route",
    7: "completed",
}

# Final states that stop polling
FINAL_STATES = {"completed", "cancelled", "failed"}
