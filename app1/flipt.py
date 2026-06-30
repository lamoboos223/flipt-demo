import httpx
from fastapi import HTTPException, Request

from config import (
    BOOLEAN_FLAGS,
    BFF_URL,
    DEFAULT_CITY,
    FLIPT_URL,
    PAYMENT_FLAG_MAP,
    VARIANT_FLAGS,
    VARIANT_FALLBACKS,
)


def get_evaluation_context(request: Request) -> dict[str, str]:
    city = (
        request.query_params.get("city")
        or request.cookies.get("city")
        or DEFAULT_CITY
    )
    return {"city": city.lower()}


async def evaluate_boolean_flag(
    client: httpx.AsyncClient,
    namespace: str,
    flag_key: str,
    entity_id: str,
    context: dict[str, str],
) -> bool:
    response = await client.post(
        f"{FLIPT_URL}/evaluate/v1/boolean",
        json={
            "namespaceKey": namespace,
            "flagKey": flag_key,
            "entityId": entity_id,
            "context": context,
        },
        timeout=10.0,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Flipt evaluation failed for {flag_key}: {response.text}",
        )
    return response.json().get("enabled", False)


async def evaluate_variant_flag(
    client: httpx.AsyncClient,
    namespace: str,
    flag_key: str,
    entity_id: str,
    context: dict[str, str],
) -> str:
    response = await client.post(
        f"{FLIPT_URL}/evaluate/v1/variant",
        json={
            "namespaceKey": namespace,
            "flagKey": flag_key,
            "entityId": entity_id,
            "context": context,
        },
        timeout=10.0,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Flipt evaluation failed for {flag_key}: {response.text}",
        )
    return response.json().get("variantKey") or VARIANT_FALLBACKS[flag_key]


async def evaluate_via_bff(
    namespace: str, entity_id: str, context: dict[str, str]
) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BFF_URL}/api/v1/flags/evaluate",
            json={
                "namespace": namespace,
                "entity_id": entity_id,
                "context": context,
            },
            timeout=15.0,
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"BFF evaluation failed: {response.text}",
        )
    data = response.json()
    return {"booleans": data["flags"], "variants": data["variants"]}


async def evaluate_direct(
    namespace: str, entity_id: str, context: dict[str, str]
) -> dict:
    booleans: dict[str, bool] = {}
    variants: dict[str, str] = {}
    async with httpx.AsyncClient() as client:
        for flag_key in BOOLEAN_FLAGS:
            booleans[flag_key] = await evaluate_boolean_flag(
                client, namespace, flag_key, entity_id, context
            )
        for flag_key in VARIANT_FLAGS:
            variants[flag_key] = await evaluate_variant_flag(
                client, namespace, flag_key, entity_id, context
            )
    return {"booleans": booleans, "variants": variants}


async def evaluate_all(
    namespace: str, entity_id: str, context: dict[str, str]
) -> dict:
    if BFF_URL:
        return await evaluate_via_bff(namespace, entity_id, context)
    return await evaluate_direct(namespace, entity_id, context)


def build_payment_methods(flags: dict[str, bool]) -> list[dict[str, str]]:
    methods = [{"id": "credit-card", "name": "Credit / Debit Card", "icon": "💳"}]
    optional = [
        ("paypal", "PayPal", "🅿️"),
        ("apple-pay", "Apple Pay", ""),
        ("bnpl", "Buy Now, Pay Later", "📅"),
        ("crypto", "Cryptocurrency", "₿"),
    ]
    for method_id, name, icon in optional:
        flag_key = PAYMENT_FLAG_MAP[method_id]
        if flag_key and flags.get(flag_key, False):
            methods.append({"id": method_id, "name": name, "icon": icon})
    return methods
