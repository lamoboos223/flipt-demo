import hashlib
import json

import httpx
from fastapi import HTTPException

from cache import evaluation_cache, flag_list_cache
from config import CACHE_TTL_SECONDS, FLAG_LIST_TTL_SECONDS, FLIPT_URL

BOOLEAN_TYPE = "BOOLEAN_FLAG_TYPE"
VARIANT_TYPE = "VARIANT_FLAG_TYPE"


def context_cache_key(namespace: str, entity_id: str, context: dict[str, str]) -> str:
    payload = json.dumps(
        {"namespace": namespace, "entity_id": entity_id, "context": context},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


async def list_namespace_flags(
    client: httpx.AsyncClient, namespace: str
) -> list[dict]:
    cache_key = f"flags:{namespace}"
    cached = flag_list_cache.get(cache_key)
    if cached is not None:
        return cached

    response = await client.get(
        f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags",
        timeout=10.0,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to list flags for namespace '{namespace}': {response.text}",
        )

    flags = [
        flag
        for flag in response.json().get("flags", [])
        if flag.get("type") in (BOOLEAN_TYPE, VARIANT_TYPE)
    ]
    flag_list_cache.set(cache_key, flags, FLAG_LIST_TTL_SECONDS)
    return flags


def parse_batch_response(flags: list[dict], batch_response: dict) -> dict:
    booleans: dict[str, bool] = {}
    variants: dict[str, str] = {}
    flag_types = {flag["key"]: flag["type"] for flag in flags}

    for item in batch_response.get("responses", []):
        if item.get("type") == "BOOLEAN_EVALUATION_RESPONSE_TYPE":
            body = item.get("booleanResponse", {})
            flag_key = body.get("flagKey")
            if flag_key:
                booleans[flag_key] = body.get("enabled", False)
        elif item.get("type") == "VARIANT_EVALUATION_RESPONSE_TYPE":
            body = item.get("variantResponse", {})
            flag_key = body.get("flagKey")
            if flag_key:
                variants[flag_key] = body.get("variantKey") or ""

    for flag_key, flag_type in flag_types.items():
        if flag_type == BOOLEAN_TYPE and flag_key not in booleans:
            booleans[flag_key] = False
        if flag_type == VARIANT_TYPE and flag_key not in variants:
            variants[flag_key] = ""

    return {"booleans": booleans, "variants": variants}


async def evaluate_namespace_flags(
    namespace: str,
    entity_id: str,
    context: dict[str, str],
    *,
    use_cache: bool = True,
) -> dict:
    cache_key = context_cache_key(namespace, entity_id, context)
    if use_cache:
        cached = evaluation_cache.get(cache_key)
        if cached is not None:
            return {**cached, "cached": True}

    async with httpx.AsyncClient() as client:
        flags = await list_namespace_flags(client, namespace)
        if not flags:
            result = {
                "namespace": namespace,
                "entity_id": entity_id,
                "context": context,
                "flags": {},
                "variants": {},
                "flag_count": 0,
                "cached": False,
            }
            evaluation_cache.set(cache_key, result, CACHE_TTL_SECONDS)
            return result

        requests = [
            {
                "namespaceKey": namespace,
                "flagKey": flag["key"],
                "entityId": entity_id,
                "context": context,
            }
            for flag in flags
        ]
        response = await client.post(
            f"{FLIPT_URL}/evaluate/v1/batch",
            json={"requests": requests},
            timeout=15.0,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Flipt batch evaluation failed: {response.text}",
            )

        evaluated = parse_batch_response(flags, response.json())

    result = {
        "namespace": namespace,
        "entity_id": entity_id,
        "context": context,
        "flags": evaluated["booleans"],
        "variants": evaluated["variants"],
        "flag_count": len(flags),
        "cached": False,
    }
    evaluation_cache.set(cache_key, result, CACHE_TTL_SECONDS)
    return result
