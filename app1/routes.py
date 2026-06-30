import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from catalog import PRODUCTS, get_product
from config import DEFAULT_NAMESPACE, ENV_PATTERN
from flipt import build_payment_methods, evaluate_flags, get_evaluation_context

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    env: str = Query(default=DEFAULT_NAMESPACE, pattern=ENV_PATTERN),
):
    entity_id = request.cookies.get("user_id", str(uuid.uuid4()))
    context = get_evaluation_context(request)
    flags = await evaluate_flags(env, entity_id, context)
    response = templates.TemplateResponse(
        request,
        "index.html",
        {
            "env": env,
            "city": context["city"],
            "flags": flags,
            "theme_v2": flags.get("theme-v2", False),
            "express_checkout": flags.get("express-checkout", False),
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
    flags = await evaluate_flags(env, entity_id, context)
    return {
        "namespace": env,
        "entity_id": entity_id,
        "context": context,
        "flags": flags,
        "payment_methods": build_payment_methods(flags),
        "theme_v2": flags.get("theme-v2", False),
    }


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
    flags = await evaluate_flags(env, entity_id, context)
    allowed_methods = {m["id"] for m in build_payment_methods(flags)}
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
    return {
        "success": True,
        "order_id": order_id,
        "namespace": env,
        "product": {"id": product["id"], "name": product["name"], "price": product["price"]},
        "payment_method": payment_method,
        "context": context,
        "theme_v2": flags.get("theme-v2", False),
        "message": f"Order placed via {payment_method} in {env} environment",
    }


@router.get("/health")
async def health():
    return {"status": "ok", "app": "app1"}
