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

ALL_USERS_SEGMENT = {
    "key": "all-users",
    "name": "All Users",
    "description": "Matches users in any supported city",
    "matchType": "ANY_MATCH_TYPE",
    "constraints": [
        {
            "type": "STRING_COMPARISON_TYPE",
            "property": "city",
            "operator": "eq",
            "value": "riyadh",
        },
        {
            "type": "STRING_COMPARISON_TYPE",
            "property": "city",
            "operator": "eq",
            "value": "makkah",
        },
        {
            "type": "STRING_COMPARISON_TYPE",
            "property": "city",
            "operator": "eq",
            "value": "jeddah",
        },
        {
            "type": "STRING_COMPARISON_TYPE",
            "property": "city",
            "operator": "eq",
            "value": "dammam",
        },
    ],
}

VARIANT_FLAG_DEFS = {
    "promo-banner": {
        "description": "Which promotional banner to show on the home screen",
        "variants": [
            ("none", "None"),
            ("sale", "Sale"),
            ("free-shipping", "Free Shipping"),
            ("ramadan", "Ramadan"),
        ],
        "rules": {
            "dev": [
                {"rank": 1, "segment": "makkah-residents", "variant": "ramadan"},
                {"rank": 2, "segment": "all-users", "variant": "sale"},
            ],
            "qa": [
                {"rank": 1, "segment": "makkah-residents", "variant": "ramadan"},
                {"rank": 2, "segment": "all-users", "variant": "free-shipping"},
            ],
            "prod": [
                {"rank": 1, "segment": "makkah-residents", "variant": "ramadan"},
                {"rank": 2, "segment": "all-users", "variant": "none"},
            ],
        },
    },
    "product-card-style": {
        "description": "Product listing layout style",
        "variants": [("grid", "Grid"), ("list", "List")],
        "rules": {
            "dev": [{"rank": 1, "segment": "all-users", "variant": "grid"}],
            "qa": [{"rank": 1, "segment": "all-users", "variant": "list"}],
            "prod": [{"rank": 1, "segment": "all-users", "variant": "grid"}],
        },
    },
    "checkout-layout": {
        "description": "Checkout screen layout",
        "variants": [
            ("classic", "Classic"),
            ("compact", "Compact"),
            ("one-page", "One Page"),
        ],
        "rules": {
            "dev": [{"rank": 1, "segment": "all-users", "variant": "classic"}],
            "qa": [{"rank": 1, "segment": "all-users", "variant": "compact"}],
            "prod": [{"rank": 1, "segment": "all-users", "variant": "one-page"}],
        },
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


def get_segment(client: httpx.Client, namespace: str, segment_key: str) -> dict | None:
    response = client.get(f"{FLIPT_URL}/api/v1/namespaces/{namespace}/segments/{segment_key}")
    if response.status_code != 200:
        return None
    return response.json()


def constraint_signature(constraint: dict) -> tuple:
    return (
        constraint.get("property"),
        constraint.get("operator"),
        constraint.get("value"),
    )


def create_segment(client: httpx.Client, namespace: str, segment: dict):
    segment_key = segment["key"]
    payload = {
        "key": segment_key,
        "name": segment["name"],
        "description": segment["description"],
        "matchType": segment.get("matchType", "ALL_MATCH_TYPE"),
    }
    if segment_exists(client, namespace, segment_key):
        client.put(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/segments/{segment_key}",
            json=payload,
        ).raise_for_status()
    else:
        client.post(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/segments",
            json=payload,
        ).raise_for_status()
        print(f"  segment '{segment_key}' created")

    existing = get_segment(client, namespace, segment_key) or {}
    existing_signatures = {
        constraint_signature(constraint)
        for constraint in existing.get("constraints", [])
    }

    constraints = segment.get("constraints")
    if constraints:
        for constraint in constraints:
            if constraint_signature(constraint) in existing_signatures:
                continue
            response = client.post(
                f"{FLIPT_URL}/api/v1/namespaces/{namespace}/segments/{segment_key}/constraints",
                json=constraint,
            )
            if response.status_code not in (200, 409):
                response.raise_for_status()
    else:
        constraint = segment["constraint"]
        if constraint_signature(constraint) not in existing_signatures:
            response = client.post(
                f"{FLIPT_URL}/api/v1/namespaces/{namespace}/segments/{segment_key}/constraints",
                json=constraint,
            )
            if response.status_code not in (200, 409):
                response.raise_for_status()
    print(f"  segment '{segment_key}' constraint configured")


def create_makkah_segment(client: httpx.Client, namespace: str):
    create_segment(client, namespace, MAKKAH_SEGMENT)


def create_all_users_segment(client: httpx.Client, namespace: str):
    create_segment(client, namespace, ALL_USERS_SEGMENT)


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


def get_flag(client: httpx.Client, namespace: str, flag_key: str) -> dict:
    response = client.get(f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}")
    response.raise_for_status()
    return response.json()


def get_variant_id(flag: dict, variant_key: str) -> str:
    for variant in flag.get("variants", []):
        if variant["key"] == variant_key:
            return variant["id"]
    raise ValueError(f"variant '{variant_key}' not found on flag '{flag['key']}'")


def get_rules(client: httpx.Client, namespace: str, flag_key: str) -> list:
    response = client.get(
        f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}/rules"
    )
    response.raise_for_status()
    return response.json().get("rules", [])


def ensure_variant_flag(client: httpx.Client, namespace: str, flag_key: str, definition: dict):
    payload = {
        "key": flag_key,
        "name": flag_key.replace("-", " ").title(),
        "description": definition["description"],
        "enabled": True,
        "type": "VARIANT_FLAG_TYPE",
    }
    if flag_exists(client, namespace, flag_key):
        client.put(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}",
            json=payload,
        ).raise_for_status()
    else:
        client.post(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags",
            json=payload,
        ).raise_for_status()

    flag = get_flag(client, namespace, flag_key)
    existing_variant_keys = {variant["key"] for variant in flag.get("variants", [])}
    for variant_key, variant_name in definition["variants"]:
        if variant_key in existing_variant_keys:
            continue
        client.post(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}/variants",
            json={"key": variant_key, "name": variant_name},
        ).raise_for_status()

    print(f"  variant flag '{flag_key}' ready")


def configure_variant_rules(
    client: httpx.Client, namespace: str, flag_key: str, rules: list[dict]
):
    existing_rules = get_rules(client, namespace, flag_key)
    if existing_rules and all(rule.get("distributions") for rule in existing_rules):
        if len(existing_rules) == len(rules):
            print(f"  variant flag '{flag_key}' rules already configured")
            return

    for rule in existing_rules:
        client.delete(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}/rules/{rule['id']}"
        )

    flag = get_flag(client, namespace, flag_key)
    for rule_def in rules:
        rule_payload = {"rank": rule_def["rank"], "segmentKey": rule_def["segment"]}
        rule_response = client.post(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}/rules",
            json=rule_payload,
        )
        rule_response.raise_for_status()
        rule_id = rule_response.json()["id"]
        variant_id = get_variant_id(flag, rule_def["variant"])
        client.post(
            f"{FLIPT_URL}/api/v1/namespaces/{namespace}/flags/{flag_key}/rules/{rule_id}/distributions",
            json={"variantId": variant_id, "rollout": 100},
        ).raise_for_status()

    print(f"  variant flag '{flag_key}' rules configured")


def seed_variant_flags(client: httpx.Client, namespace: str):
    for flag_key, definition in VARIANT_FLAG_DEFS.items():
        ensure_variant_flag(client, namespace, flag_key, definition)
        configure_variant_rules(client, namespace, flag_key, definition["rules"][namespace])


def main():
    with httpx.Client(timeout=30.0) as client:
        wait_for_flipt(client)
        for namespace in NAMESPACES:
            create_namespace(client, namespace)
            create_makkah_segment(client, namespace)
            create_all_users_segment(client, namespace)
            for flag_key, enabled in FLAGS[namespace].items():
                create_boolean_flag(client, namespace, flag_key, enabled)
            configure_crypto_segment_rollout(client, namespace)
            seed_variant_flags(client, namespace)
    print("Seed complete")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
