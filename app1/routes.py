import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from catalog import PRODUCTS, get_product
from config import DEFAULT_NAMESPACE, ENV_PATTERN, PROMO_BANNER_MESSAGES
from flipt import build_payment_methods, evaluate_all, get_evaluation_context

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def build_flag_response(namespace: str, entity_id: str, context: dict, evaluated: dict):
    booleans = evaluated["booleans"]
    variants = evaluated["variants"]
    promo = variants.get("promo-banner", "none")
    return {
        "namespace": namespace,
        "entity_id": entity_id,
        "context": context,
        "flags": booleans,
        "variants": variants,
        "payment_methods": build_payment_methods(booleans),
        "theme_v2": booleans.get("theme-v2", False),
        "promo_banner": promo,
        "promo_message": PROMO_BANNER_MESSAGES.get(promo),
        "product_card_style": variants.get("product-card-style", "grid"),
        "checkout_layout": variants.get("checkout-layout", "classic"),
    }


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    env: str = Query(default=DEFAULT_NAMESPACE, pattern=ENV_PATTERN),
):
    entity_id = request.cookies.get("user_id", str(uuid.uuid4()))
    context = get_evaluation_context(request)
    evaluated = await evaluate_all(env, entity_id, context)
    data = build_flag_response(env, entity_id, context, evaluated)
    response = templates.TemplateResponse(
        request,
        "index.html",
        {
            "env": env,
            "city": context["city"],
            "theme_v2": data["theme_v2"],
            "express_checkout": data["flags"].get("express-checkout", False),
            "promo_message": data["promo_message"],
            "product_card_style": data["product_card_style"],
            "checkout_layout": data["checkout_layout"],
        },
    )
    if "user_id" not in request.cookies:
        response.set_cookie("user_id", entity_id, max_age=60 * 60 * 24 * 365)
    if request.query_params.get("city"):
        response.set_cookie("city", context["city"], max_age=60 * 60 * 24 * 365)
    return response


@router.get("/api/products")
async def list_products():
    return {"products": PRODUCTS}


@router.get("/api/flags")
async def get_flags(
    request: Request,
    env: str = Query(default=DEFAULT_NAMESPACE, pattern=ENV_PATTERN),
):
    entity_id = request.cookies.get("user_id", "anonymous")
    context = get_evaluation_context(request)
    evaluated = await evaluate_all(env, entity_id, context)
    return build_flag_response(env, entity_id, context, evaluated)


@router.post("/api/checkout")
async def checkout(
    request: Request,
    env: str = Query(default=DEFAULT_NAMESPACE, pattern=ENV_PATTERN),
):
    body = await request.json()
    entity_id = request.cookies.get("user_id", "anonymous")
    context = get_evaluation_context(request)
    if body.get("city"):
        context["city"] = str(body["city"]).lower()
    evaluated = await evaluate_all(env, entity_id, context)
    booleans = evaluated["booleans"]
    allowed_methods = {m["id"] for m in build_payment_methods(booleans)}
    payment_method = body.get("payment_method", "credit-card")
    product_id = body.get("product_id")

    if payment_method not in allowed_methods:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Payment method not available",
                "payment_method": payment_method,
                "allowed_methods": sorted(allowed_methods),
                "namespace": env,
                "message": f"'{payment_method}' is disabled by feature flags in {env}",
            },
        )

    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    variants = evaluated["variants"]
    return {
        "success": True,
        "order_id": order_id,
        "namespace": env,
        "product": {"id": product["id"], "name": product["name"], "price": product["price"]},
        "payment_method": payment_method,
        "context": context,
        "variants": variants,
        "checkout_layout": variants.get("checkout-layout", "classic"),
        "theme_v2": booleans.get("theme-v2", False),
        "message": f"Order placed via {payment_method} in {env} environment",
    }


@router.get("/health")
async def health():
    return {"status": "ok", "app": "app1"}
