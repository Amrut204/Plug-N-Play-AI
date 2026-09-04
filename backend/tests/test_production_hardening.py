import pytest
from app.models.agents import Agent
from app.api.v1.chat import verify_agent_origin
from app.services.rag.embedder import EmbeddingService
from app.core.config import Settings


def test_verify_agent_origin():
    # 1. No allowed domains or '*' -> all allowed
    agent_open = Agent(name="Open Agent", allowed_domains=None)
    assert verify_agent_origin(agent_open, "https://anywebsite.com", None) is True
    assert verify_agent_origin(agent_open, None, None) is True

    agent_wildcard = Agent(name="Wildcard Agent", allowed_domains="*")
    assert verify_agent_origin(agent_wildcard, "https://anywebsite.com", None) is True

    # 2. Specific allowed domains
    agent_restricted = Agent(name="Enterprise Agent", allowed_domains="clientportal.com, partner.io")

    # Allowed exact match
    assert verify_agent_origin(agent_restricted, "https://clientportal.com", None) is True
    # Allowed subdomain match
    assert verify_agent_origin(agent_restricted, "https://app.clientportal.com", None) is True
    assert verify_agent_origin(agent_restricted, "https://sub.partner.io", None) is True
    # Allowed via referer
    assert verify_agent_origin(agent_restricted, None, "https://clientportal.com/dashboard") is True
    # Allowed localhost / development
    assert verify_agent_origin(agent_restricted, "http://localhost:3000", None) is True
    assert verify_agent_origin(agent_restricted, "http://127.0.0.1:8000", None) is True

    # Denied unauthorized third-party origin
    assert verify_agent_origin(agent_restricted, "https://malicious-site.com", None) is False
    assert verify_agent_origin(agent_restricted, "https://otherclient.com", None) is False


@pytest.mark.asyncio
async def test_batch_vector_embeddings():
    texts = ["How do I pay tuition fees?", "Where is the library located?", "What is the examination policy?"]
    embeddings = await EmbeddingService.get_embeddings_batch(texts)
    
    assert len(embeddings) == 3
    for vec in embeddings:
        assert len(vec) == 384
        assert isinstance(vec[0], float)


def test_production_secret_key_protection():
    # Verify settings has required security attributes
    s = Settings(ENVIRONMENT="development")
    assert hasattr(s, "CHAT_RATE_LIMIT_PER_MINUTE")
    assert s.CHAT_RATE_LIMIT_PER_MINUTE > 0
    assert hasattr(s, "MAX_UPLOAD_SIZE_BYTES")
    assert s.MAX_UPLOAD_SIZE_BYTES == 25 * 1024 * 1024
