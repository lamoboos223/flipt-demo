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

VARIANT_FLAGS = ["promo-banner", "product-card-style", "checkout-layout"]

VARIANT_FALLBACKS = {
    "promo-banner": "none",
    "product-card-style": "grid",
    "checkout-layout": "classic",
}

PROMO_BANNER_MESSAGES = {
    "none": None,
    "sale": "🔥 Mega Sale — Up to 50% off today!",
    "free-shipping": "🚚 Free shipping on orders over $50",
    "ramadan": "🌙 Ramadan specials — blessed savings in Makkah",
}
