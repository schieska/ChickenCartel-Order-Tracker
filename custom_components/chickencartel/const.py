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

# Status mapping from the CashDesk OrderHarmonyStatus enum to stable,
# user-facing states. The Chicken Cartel status page groups the intermediate
# external-party/POS states into the same visible "sent to restaurant" step,
# so codes 2-4 and 10 intentionally share the existing ``pos`` state.
STATUS_MAP = {
    -3: "failed",  # ValidationFailed
    -2: "failed",  # ImportFailed
    -1: "cancelled",
    1: "received",
    2: "pos",  # RequestForExternalParty
    3: "pos",  # ReadyForPOS
    4: "pos",  # SentToPOS
    5: "accepted",  # ACKByPOS / ready for preparation
    6: "preparing",
    7: "waiting_for_driver",
    8: "en_route",
    9: "completed",
    10: "pos",  # WaitingForResponseExternalParty
    11: "failed",  # RequestForExternalPartyFailed
}

# Final states that stop polling
FINAL_STATES = {"completed", "cancelled", "failed"}
