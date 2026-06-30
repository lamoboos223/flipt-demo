# Flipt Demo — Feature Flag Marketplace

A POC demo with **Flipt v1** + **PostgreSQL**, three namespaces (`dev`, `qa`, `prod`), and **app1** — a simple mobile-style marketplace whose UI and checkout are controlled by feature flags.

## Architecture

```
┌─────────────┐     evaluate flags      ┌──────────────┐
│   app1      │ ──────────────────────► │  Flipt v1    │
│  (Python)   │   namespace = dev/qa/prod│  :8080       │
└─────────────┘                         └──────┬───────┘
                                               │
                                               ▼
                                      ┌──────────────┐
                                      │  PostgreSQL  │
                                      │  (flipt only)│
                                      └──────────────┘
```

app1 has no database — products are hardcoded in memory.

## Quick Start

```bash
docker compose up --build
```

| Service   | URL                          |
|-----------|------------------------------|
| app1      | http://localhost:5001        |
| Flipt UI  | http://localhost:8080        |
| Postgres  | localhost:5432               |

## Feature Flags

| Flag | Controls |
|------|----------|
| `theme-v2` | Dark modern UI vs classic light theme |
| `payment-paypal` | PayPal checkout option |
| `payment-apple-pay` | Apple Pay option |
| `payment-bnpl` | Buy Now Pay Later option |
| `payment-crypto` | Crypto — segment rollout for `city=makkah` |
| `express-checkout` | Express checkout banner |

`payment-crypto` uses a segment rollout. app1 passes evaluation context:

```json
{ "city": "makkah" }
```

Use the city dropdown in the UI to test (Makkah → crypto shown, Riyadh → hidden).

## app1 API

| Endpoint | Description |
|----------|-------------|
| `GET /` | Mobile marketplace UI |
| `GET /api/products` | Hardcoded product list |
| `GET /api/flags?env=dev&city=makkah` | Evaluated flags + payment methods |
| `POST /api/checkout?env=dev` | Place order — rejects disabled payment methods |

## Project Layout

```
├── docker-compose.yml
├── postgres/init.sql           # Creates flipt database
├── flipt-seed/                 # Bootstrap namespaces/flags
└── app1/                       # Stateless POC demo app
```
