# Flipt Demo — Feature Flag Marketplace

A POC demo with **Flipt v1** + **PostgreSQL**, three namespaces (`dev`, `qa`, `prod`), and **app1** — a simple mobile-style marketplace whose UI and checkout are controlled by feature flags.

## Architecture

```
┌─────────────┐                    ┌──────────────┐
│   app1      │ ──► BFF (batch) ──►│  Flipt v1    │
│  (Python)   │                    │  :8080       │
└─────────────┘                    └──────┬───────┘
       ▲                                  │
       │                                  ▼
┌─────────────┐                    ┌──────────────┐
│ Mobile app  │ ──► BFF :5002      │  PostgreSQL  │
└─────────────┘   (one call)       │  (flipt only)│
                                   └──────────────┘
```

app1 has no database — products are hardcoded in memory. Both app1 and mobile clients should call **BFF** for flag evaluation (one request, all flags, cached).

## Quick Start

```bash
docker compose up --build
```

| Service   | URL                          |
|-----------|------------------------------|
| app1      | http://localhost:5001        |
| BFF       | http://localhost:5002        |
| Flipt UI  | http://localhost:8080        |
| Postgres  | localhost:5432               |

## Feature Flags

Flags are split into **boolean** (on/off) and **variant** (pick one of several options). All evaluation calls pass context:

```json
{ "city": "riyadh" }
```

Use the environment and city dropdowns in the UI to test different combinations.

### Boolean flags

| Flag | Controls |
|------|----------|
| `theme-v2` | Dark modern UI vs classic light theme |
| `payment-paypal` | PayPal checkout option |
| `payment-apple-pay` | Apple Pay option |
| `payment-bnpl` | Buy Now Pay Later option |
| `payment-crypto` | Crypto — segment rollout for `city=makkah` |
| `express-checkout` | Express checkout banner |

Default values per namespace:

| Flag | dev | qa | prod |
|------|-----|-----|------|
| `theme-v2` | on | on | off |
| `payment-paypal` | on | on | off |
| `payment-apple-pay` | on | off | off |
| `payment-bnpl` | on | on | off |
| `payment-crypto` | off* | off* | off* |
| `express-checkout` | on | on | off |

\* `payment-crypto` is off by default but enabled via segment rollout when `city=makkah`.

### Variant flags

Variant flags return a string key instead of true/false. app1 uses them to change UI layout and messaging.

| Flag | Variants | What it controls |
|------|----------|------------------|
| `promo-banner` | `none`, `sale`, `free-shipping`, `ramadan` | Home-screen promo banner message |
| `product-card-style` | `grid`, `list` | Product listing layout |
| `checkout-layout` | `classic`, `compact`, `one-page` | Checkout screen layout |

Default variant per namespace (Riyadh / any supported city):

| Flag | dev | qa | prod |
|------|-----|-----|------|
| `promo-banner` | `sale` | `free-shipping` | `none` |
| `product-card-style` | `grid` | `list` | `grid` |
| `checkout-layout` | `classic` | `compact` | `one-page` |

When `city=makkah`, `promo-banner` overrides to `ramadan` in all environments (segment rule takes priority).

### Segments

| Segment | Match rule |
|---------|------------|
| `makkah-residents` | `city` equals `makkah` |
| `all-users` | `city` is one of `riyadh`, `makkah`, `jeddah`, `dammam` |

## BFF (mobile / batch flags API)

The **BFF** service is the integration point for mobile clients. It:

1. **Auto-discovers** all enabled flags in a namespace from Flipt (no hardcoded flag list)
2. **Batch-evaluates** them in a single `POST /evaluate/v1/batch` call to Flipt
3. **Caches** results in memory (default 60s) keyed by namespace + entity + context

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/flags?ns=dev&entity_id=user-123&city=riyadh` | Evaluate all flags (GET, query params) |
| `POST /api/v1/flags/evaluate` | Evaluate all flags (POST, JSON body) |
| `GET /api/v1/flags/list?ns=dev` | List enabled flags in namespace |
| `GET /api/v1/cache/stats` | Cache hit/miss stats |
| `POST /api/v1/cache/invalidate` | Clear cache (optional `?namespace=dev`) |

Example mobile call:

```bash
curl -X POST http://localhost:5002/api/v1/flags/evaluate \
  -H "Content-Type: application/json" \
  -d '{"namespace":"dev","entity_id":"user-123","context":{"city":"makkah"}}'
```

Response:

```json
{
  "namespace": "dev",
  "entity_id": "user-123",
  "context": { "city": "makkah" },
  "flags": { "theme-v2": true, "payment-crypto": true },
  "variants": { "promo-banner": "ramadan", "product-card-style": "grid" },
  "flag_count": 9,
  "cached": false
}
```

Environment variables: `CACHE_TTL_SECONDS` (default 60), `FLAG_LIST_TTL_SECONDS` (default 60).

## app1 API

| Endpoint | Description |
|----------|-------------|
| `GET /` | Mobile marketplace UI |
| `GET /api/products` | Hardcoded product list |
| `GET /api/flags?env=dev&city=makkah` | Evaluated boolean flags, variants, and payment methods |
| `POST /api/checkout?env=dev` | Place order — rejects disabled payment methods |

Example `/api/flags` response:

```json
{
  "namespace": "dev",
  "context": { "city": "riyadh" },
  "flags": {
    "theme-v2": true,
    "payment-crypto": false
  },
  "variants": {
    "promo-banner": "sale",
    "product-card-style": "grid",
    "checkout-layout": "classic"
  },
  "promo_banner": "sale",
  "promo_message": "🔥 Mega Sale — Up to 50% off today!",
  "product_card_style": "grid",
  "checkout_layout": "classic"
}
```

## Project Layout

```
├── docker-compose.yml
├── postgres/init.sql           # Creates flipt database
├── flipt-seed/                 # Bootstrap namespaces/flags
├── BFF/                        # Batch flag evaluation + cache for mobile
└── app1/                       # Stateless POC demo app
```
