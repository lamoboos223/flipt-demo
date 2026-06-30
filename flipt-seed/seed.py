import os
import sys
import time

import httpx

FLIPT_URL = os.getenv("FLIPT_URL", "http://flipt:8080")

NAMESPACES = ["dev", "qa", "prod"]

FLAGS = {
    "dev": {
        "theme-v2": True,
        "payment-paypal": True,
        "payment-apple-pay": True,
        "payment-bnpl": True,
        "express-checkout": True,
    },
    "qa": {
        "theme-v2": True,
        "payment-paypal": True,
        "payment-apple-pay": False,
        "payment-bnpl": True,
        "express-checkout": True,
    },
    "prod": {
        "theme-v2": False,
        "payment-paypal": False,
        "payment-apple-pay": False,
        "payment-bnpl": False,
        "express-checkout": False,
    },
}

FLAG_DESCRIPTIONS = {
    "theme-v2": "Enable the modern dark marketplace theme (v2)",
    "payment-paypal": "Show PayPal as a checkout payment option",
    "payment-apple-pay": "Show Apple Pay as a checkout payment option",
    "payment-bnpl": "Show Buy Now Pay Later payment option",
    "payment-crypto": "Show cryptocurrency payment option for users in Makkah",
    "express-checkout": "Enable express checkout banner on product pages",
}

MAKKAH_SEGMENT = {
    "key": "makkah-residents",
    "name": "Makkah Residents",
    "description": "Users whose city property equals makkah",
    "constraint": {
        "type": "STRING_COMPARISON_TYPE",
        "property": "city",
        "operator": "eq",
        "value": "makkah",
    },
}


def wait_for_flipt(client: httpx.Client):
    for _ in range(30):
        try:
            response = client.get(f"{FLIPT_URL}/health")
            if response.status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(2)
    raise RuntimeError("Flipt did not become healthy in time")


def namespace_exists(client: httpx.Client, key: str) -> bool:
    response = client.get(f"{FLIPT_URL}/api/v1/namespaces/{key}")
    return response.status_code == 200


def create_namespace(client: httpx.Client, key: str):
    if namespace_exists(client, key):
        print(f"Namespace '{key}' already exists")
        return
    response = client.post(
        f"{FLIPT_URL}/api/v1/namespaces",
        json={"key": key, "name": key.upper(), "description": f"{key.upper()} environment"},
    )
    response.raise_for_status()
    print(f"Created namespace '{key}'")


def flag_exists(client: httpx.Client, namespace: str, flag_key: str) -> bool:
    response = client.get(f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}")
    return response.status_code == 200


def create_boolean_flag(client: httpx.Client, namespace: str, flag_key: str, enabled: bool):
    payload = {
        "key": flag_key,
        "name": flag_key.replace("-", " ").title(),
        "description": FLAG_DESCRIPTIONS.get(flag_key, ""),
        "enabled": enabled,
        "type": "BOOLEAN_FLAG_TYPE",
    }
    if flag_exists(client, namespace, flag_key):
        response = client.put(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}",
            json=payload,
        )
    else:
        response = client.post(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags",
            json=payload,
        )
    response.raise_for_status()
    print(f"  flag '{flag_key}' = {enabled}")


def segment_exists(client: httpx.Client, namespace: str, segment_key: str) -> bool:
    response = client.get(f"{FLIPT_URL}/api/v1/namespaces/{namespace}/segments/{segment_key}")
    return response.status_code == 200


def create_makkah_segment(client: httpx.Client, namespace: str):
    segment_key = MAKKAH_SEGMENT["key"]
    if not segment_exists(client, namespace, segment_key):
        response = client.post(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/segments",
            json={
                "key": segment_key,
                "name": MAKKAH_SEGMENT["name"],
                "description": MAKKAH_SEGMENT["description"],
                "matchType": "ALL_MATCH_TYPE",
            },
        )
        response.raise_for_status()
        print(f"  segment '{segment_key}' created")

    response = client.post(
        f"{FLIPT_URL}/api/v1/namespaces/{namespace}/segments/{segment_key}/constraints",
        json=MAKKAH_SEGMENT["constraint"],
    )
    if response.status_code not in (200, 409) and not constraint_exists(
        client, namespace, segment_key
    ):
        response.raise_for_status()
    print(f"  segment '{segment_key}' constraint city=makkah")


def get_rollouts(client: httpx.Client, namespace: str, flag_key: str) -> list:
    response = client.get(
        f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}/rollouts"
    )
    response.raise_for_status()
    return response.json().get("rules", [])


def constraint_exists(client: httpx.Client, namespace: str, segment_key: str) -> bool:
    response = client.get(
        f"{FLIPT_URL}/api/v1/namespaces/{namespace}/segments/{segment_key}"
    )
    if response.status_code != 200:
        return False
    constraints = response.json().get("constraints", [])
    target = MAKKAH_SEGMENT["constraint"]
    return any(
        c.get("property") == target["property"]
        and c.get("operator") == target["operator"]
        and c.get("value") == target["value"]
        for c in constraints
    )


def configure_crypto_segment_rollout(client: httpx.Client, namespace: str):
    flag_key = "payment-crypto"
    create_boolean_flag(client, namespace, flag_key, enabled=False)

    rollouts = get_rollouts(client, namespace, flag_key)
    has_target_rollout = any(
        rollout.get("segment", {}).get("segmentKey") == MAKKAH_SEGMENT["key"]
        and rollout.get("segment", {}).get("value") is True
        for rollout in rollouts
    )
    if has_target_rollout:
        print(f"  flag '{flag_key}' rollout already configured")
        return

    for rollout in rollouts:
        client.delete(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}/rollouts/{rollout['id']}"
        )

    response = client.post(
        f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}/rollouts",
        json={
            "rank": 1,
            "description": "Enable crypto payments for Makkah residents",
            "segment": {
                "segmentKey": MAKKAH_SEGMENT["key"],
                "value": True,
            },
        },
    )
    response.raise_for_status()
    print(f"  flag '{flag_key}' rollout: makkah-residents -> true")


def main():
    with httpx.Client(timeout=30.0) as client:
        wait_for_flipt(client)
        for namespace in NAMESPACES:
            create_namespace(client, namespace)
            create_makkah_segment(client, namespace)
            for flag_key, enabled in FLAGS[namespace].items():
                create_boolean_flag(client, namespace, flag_key, enabled)
            configure_crypto_segment_rollout(client, namespace)
    print("Seed complete")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
