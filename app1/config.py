import os

FLIPT_URL = os.getenv("FLIPT_URL", "http://flipt:8080")
DEFAULT_NAMESPACE = os.getenv("FLIPT_NAMESPACE", "dev")
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "riyadh")
ENV_PATTERN = "^(dev|qa|prod)$"

BOOLEAN_FLAGS = [
    "theme-v2",
    "payment-paypal",
    "payment-apple-pay",
    "payment-bnpl",
    "payment-crypto",
    "express-checkout",
]

PAYMENT_FLAG_MAP = {
    "credit-card": None,
    "paypal": "payment-paypal",
    "apple-pay": "payment-apple-pay",
    "bnpl": "payment-bnpl",
    "crypto": "payment-crypto",
}
