import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from cache import evaluation_cache, flag_list_cache
from config import DEFAULT_CITY, DEFAULT_ENTITY_ID, DEFAULT_NAMESPACE, ENV_PATTERN
from flipt import evaluate_namespace_flags, list_namespace_flags

router = APIRouter()


class EvaluateRequest(BaseModel):
    namespace: str = Field(default=DEFAULT_NAMESPACE, pattern=ENV_PATTERN)
    entity_id: str = DEFAULT_ENTITY_ID
    context: dict[str, str] = Field(default_factory=dict)


def build_context(
    city: str | None,
    extra_context: dict[str, str] | None = None,
) -> dict[str, str]:
    context = dict(extra_context or {})
    if city:
        context["city"] = city.lower()
    elif "city" not in context:
        context["city"] = DEFAULT_CITY
    return context


@router.get("/health")
async def health():
    return {"status": "ok", "service": "bff"}


@router.get("/api/v1/flags")
async def get_flags(
    ns: str = Query(default=DEFAULT_NAMESPACE, alias="ns", pattern=ENV_PATTERN),
    entity_id: str = Query(default=DEFAULT_ENTITY_ID),
    city: str | None = Query(default=None),
):
    context = build_context(city)
    return await evaluate_namespace_flags(ns, entity_id, context)


@router.post("/api/v1/flags/evaluate")
async def evaluate_flags(body: EvaluateRequest):
    context = build_context(body.context.get("city"), body.context)
    return await evaluate_namespace_flags(body.namespace, body.entity_id, context)


@router.get("/api/v1/flags/list")
async def list_flags(
    ns: str = Query(default=DEFAULT_NAMESPACE, alias="ns", pattern=ENV_PATTERN),
):
    async with httpx.AsyncClient() as client:
        flags = await list_namespace_flags(client, ns)
    return {
        "namespace": ns,
        "flags": [
            {"key": flag["key"], "type": flag["type"], "description": flag.get("description", "")}
            for flag in flags
        ],
    }


@router.post("/api/v1/cache/invalidate")
async def invalidate_cache(
    namespace: str | None = Query(default=None, pattern=ENV_PATTERN),
):
    eval_removed = evaluation_cache.invalidate()
    if namespace is None:
        flag_removed = flag_list_cache.invalidate()
    else:
        flag_removed = flag_list_cache.invalidate(f"flags:{namespace}")
    return {
        "evaluation_entries_removed": eval_removed,
        "flag_list_entries_removed": flag_removed,
    }


@router.get("/api/v1/cache/stats")
async def cache_stats():
    return {
        "evaluation": evaluation_cache.stats(),
        "flag_list": flag_list_cache.stats(),
    }
