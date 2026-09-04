import pytest
from app.services.router.intent_router import IntentRouter


@pytest.mark.asyncio
async def test_route_sql_intent():
    intent, reason = await IntentRouter.route_query("What is my attendance percentage in Database Systems?")
    assert intent == "SQL"


@pytest.mark.asyncio
async def test_route_rag_intent():
    intent, reason = await IntentRouter.route_query("What is the institutional policy regarding examination attendance?")
    assert intent == "RAG"


@pytest.mark.asyncio
async def test_route_hybrid_intent():
    intent, reason = await IntentRouter.route_query("Can I sit for the exam considering my current attendance?")
    assert intent == "HYBRID"


@pytest.mark.asyncio
async def test_route_direct_intent():
    intent, reason = await IntentRouter.route_query("Hello, good morning!")
    assert intent == "DIRECT"
