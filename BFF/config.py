import os

FLIPT_URL = os.getenv("FLIPT_URL", "http://flipt:8080")
DEFAULT_NAMESPACE = os.getenv("FLIPT_NAMESPACE", "dev")
DEFAULT_ENTITY_ID = os.getenv("DEFAULT_ENTITY_ID", "anonymous")
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "riyadh")
ENV_PATTERN = "^(dev|qa|prod)$"

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))
FLAG_LIST_TTL_SECONDS = int(os.getenv("FLAG_LIST_TTL_SECONDS", "60"))
