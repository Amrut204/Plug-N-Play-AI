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
