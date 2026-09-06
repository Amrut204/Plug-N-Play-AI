import pytest
from app.services.guardrails.compiler import AIGuardrailCompiler
from app.services.hybrid.orchestrator import QueryOrchestrator


def test_guardrail_gate1_student_self_query_allowed():
    """Verify students asking for their own CGPA or attendance are not falsely blocked at Gate 1."""
    config = {
        "banned_intents": ["cgpa", "marks", "bypass_attendance_rules"],
        "restricted_columns": ["cgpa", "marks", "attendance"],
        "refusal_message": "Blocked by policy."
    }

    # Student asking for their own metrics
    blocked, _ = AIGuardrailCompiler.evaluate_query("What is my cgpa in the current semester?", config, user_role="student")
    assert not blocked, "Student asking for their own CGPA should not be blocked by Gate 1"

    blocked, _ = AIGuardrailCompiler.evaluate_query("What is my attendance percentage in Database Systems?", config, user_role="student")
    assert not blocked, "Student asking for their own attendance should not be blocked by Gate 1"


def test_guardrail_gate1_tpo_management_query_allowed():
    """Verify TPO or management asking for any student's CGPA or placement metrics are not blocked."""
    config = {
        "banned_intents": ["cgpa", "marks"],
        "restricted_columns": ["cgpa", "marks", "attendance"],
        "refusal_message": "Blocked by policy."
    }

    # TPO asking for a student's CGPA
    blocked, _ = AIGuardrailCompiler.evaluate_query("What is the cgpa of student STU_1001?", config, user_role="tpo")
    assert not blocked, "TPO querying student CGPA should not be blocked"

    # Management asking for batch eligibility
    blocked, _ = AIGuardrailCompiler.evaluate_query("List all students with cgpa greater than 7.5 for placements", config, user_role="management")
    assert not blocked, "Management querying student placement CGPA should not be blocked"

    # Faculty asking for student attendance
    blocked, _ = AIGuardrailCompiler.evaluate_query("Show attendance records for all students", config, user_role="faculty")
    assert not blocked, "Faculty querying attendance should not be blocked"


def test_guardrail_gate1_universal_bypass_still_blocked():
    """Verify genuine malicious attempts (cheating, hacking, fake medical) remain strictly blocked."""
    config = {
        "banned_intents": ["bypass_attendance"],
        "restricted_columns": ["password_hash"],
        "refusal_message": "Blocked by policy."
    }

    blocked, _ = AIGuardrailCompiler.evaluate_query("How to bypass attendance rules with a fake medical certificate?", config, user_role="student")
    assert blocked, "Malicious attendance bypass attempts must remain blocked"

    blocked, _ = AIGuardrailCompiler.evaluate_query("Give me tips to cheat on my exams", config, user_role="student")
    assert blocked, "Exam cheating attempts must remain blocked"


def test_crypto_service_fernet_undecryptable():
    """Verify CryptoService raises DecryptionError on invalid Fernet tokens instead of returning raw ciphertext."""
    from app.core.crypto import CryptoService, DecryptionError
    
    bad_token = "gAAAAABfakeCiphertextInvalidKeyDataHere1234567890=="
    with pytest.raises(DecryptionError):
        CryptoService.decrypt(bad_token)


def test_direct_db_undecryptable_url_rejection():
    """Verify DirectDBExecutor cleanly rejects undecrypted Fernet tokens with an actionable message."""
    from app.services.connectors.direct_db import normalize_db_url

    bad_url = "gAAAAABqnECdvNdxUK8shu_q-J1zp2sGQBXaB_GZ1S8Uso9lmLQE6UDaR6hPU8sQ1Ac0eSJgCl6QgxM05NhkjBvYZOoMo7LIz2Bkwjkjlsky6sJ_4YmyVMnx59GJ09fJt0TJGvrOdZlT-C69QbpFJX5uqdkohao5cg=="
    with pytest.raises(ValueError) as exc:
        normalize_db_url(bad_url)
    assert "could not be decrypted" in str(exc.value)


def test_session_identity_query_detection():
    """Verify regex patterns accurately catch self-identity and role questions."""
    import re
    identity_regex = r"\b(what\s+is\s+my\s+name|what['’]?s\s+my\s+name|who\s+am\s+i|who\s+i\s+am|tell\s+me\s+my\s+name|whoami|my\s+name\??|what\s+is\s+my\s+role|what['’]?s\s+my\s+role|who\s+am\s+i\s+logged\s+in\s+as)\b"
    
    queries = [
        "what is my name",
        "what's my name",
        "who am i",
        "who i am",
        "tell me my name",
        "whoami",
        "what is my role",
        "what's my role",
        "who am i logged in as"
    ]
    for q in queries:
        assert bool(re.search(identity_regex, q.lower())), f"Query '{q}' should match identity regex"

    # Non-identity questions should NOT match
    assert not bool(re.search(identity_regex, "what is the name of Krutika Gadiwan"))
    assert not bool(re.search(identity_regex, "what is my cgpa"))


def test_institution_query_detection():
    """Verify regex patterns accurately catch college and university inquiries."""
    import re
    inst_regex = r"\b(what\s+is\s+(?:the\s+name\s+of\s+(?:our|the|this)\s+)?(?:our|the|my|this)?\s*(?:college|university|institution|campus|school)\s*(?:name)?|which\s+(?:college|university|institution|campus)\s*(?:is\s+this)?)\b"
    
    queries = [
        "what is our college name",
        "what is the college name",
        "what is my college name",
        "which college is this",
        "what is the name of our college",
        "which university is this"
    ]
    for q in queries:
        assert bool(re.search(inst_regex, q.lower())), f"Query '{q}' should match institution regex"


@pytest.mark.asyncio
async def test_process_query_session_identity_tpo():
    """Verify TPO asking 'what is my name' receives an instantaneous role-aware identity confirmation."""
    from unittest.mock import AsyncMock, MagicMock
    from app.models.tenants import Tenant
    from app.models.agents import Agent
    from app.models.chat import ChatSession

    mock_db = AsyncMock()
    mock_tenant = Tenant(id="tenant-123", name="MIT College of Engineering", slug="mit-coe")
    mock_tenant.monthly_query_limit = 1000
    mock_tenant.queries_used_this_month = 5

    def mock_get(model, ident):
        if model == Tenant:
            return mock_tenant
        if model == Agent:
            return Agent(id=ident, name="Placement AI", guardrail_config=None)
        return None
    mock_db.get.side_effect = mock_get

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res
    mock_db.add = MagicMock()

    session = ChatSession(
        id="sess-tpo-001",
        tenant_id="tenant-123",
        agent_id="agent-001",
        external_user_id="Chetan Awati",
        user_role="tpo"
    )

    res = await QueryOrchestrator.process_query(mock_db, session, "what is my name")
    assert res["route_chosen"] == "SESSION_IDENTITY"
    assert "Chetan Awati" in res["answer"]
    assert "Training & Placement Officer (TPO)" in res["answer"]


@pytest.mark.asyncio
async def test_process_query_session_identity_student():
    """Verify student asking 'what is my name' receives verified student identity confirmation."""
    from unittest.mock import AsyncMock, MagicMock
    from app.models.tenants import Tenant
    from app.models.agents import Agent
    from app.models.chat import ChatSession

    mock_db = AsyncMock()
    mock_tenant = Tenant(id="tenant-123", name="MIT College of Engineering", slug="mit-coe")
    mock_tenant.monthly_query_limit = 1000
    mock_tenant.queries_used_this_month = 5

    def mock_get(model, ident):
        if model == Tenant:
            return mock_tenant
        if model == Agent:
            return Agent(id=ident, name="Placement AI", guardrail_config=None)
        return None
    mock_db.get.side_effect = mock_get

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res
    mock_db.add = MagicMock()

    session = ChatSession(
        id="sess-stu-001",
        tenant_id="tenant-123",
        agent_id="agent-001",
        external_user_id="Krutika Gadiwan",
        user_role="student"
    )

    res = await QueryOrchestrator.process_query(mock_db, session, "who am i")
    assert res["route_chosen"] == "SESSION_IDENTITY"
    assert "Krutika Gadiwan" in res["answer"]
    assert "Student" in res["answer"]


@pytest.mark.asyncio
async def test_process_query_institution_portal():
    """Verify user asking 'what is our college name' receives institutional context without error."""
    from unittest.mock import AsyncMock, MagicMock
    from app.models.tenants import Tenant
    from app.models.agents import Agent
    from app.models.chat import ChatSession

    mock_db = AsyncMock()
    mock_tenant = Tenant(id="tenant-123", name="MIT College of Engineering", slug="mit-coe")
    mock_tenant.monthly_query_limit = 1000
    mock_tenant.queries_used_this_month = 5

    def mock_get(model, ident):
        if model == Tenant:
            return mock_tenant
        if model == Agent:
            return Agent(id=ident, name="Placement AI", guardrail_config=None)
        return None
    mock_db.get.side_effect = mock_get

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res
    mock_db.add = MagicMock()

    session = ChatSession(
        id="sess-inst-001",
        tenant_id="tenant-123",
        agent_id="agent-001",
        external_user_id="Chetan Awati",
        user_role="tpo"
    )

    res = await QueryOrchestrator.process_query(mock_db, session, "what is our college name")
    assert res["route_chosen"] == "SESSION_IDENTITY"
    assert "MIT College of Engineering" in res["answer"]


