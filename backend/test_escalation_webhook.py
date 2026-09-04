import asyncio
import httpx
from app.services.escalation.webhook_service import WebhookService

def test_webhook_payload_formatting():
    print("--- 1. Testing Webhook Service Payload Formatting ---")
    
    # Test with no URL (skips gracefully)
    res_skip = asyncio.run(WebhookService.send_escalation_alert(
        webhook_url="",
        session_id="test-session-123",
        agent_name="Campus Bot",
        user_query="I need help with my admission status"
    ))
    assert res_skip["status"] == "skipped"
    print("[PASS] Handled empty webhook URL gracefully without throwing error!")

def test_escalation_api_endpoint():
    print("\n--- 2. Testing POST /api/v1/chat/escalate Endpoint ---")
    client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)
    
    # 1. Create a dummy agent via quickstart
    res_agent = client.post("/api/v1/quickstart/setup", json={
        "project_name": "Campus Support System",
        "agent_name": "Admissions Bot",
        "service_type": "sql",
        "connection_mode": "schema_only",
        "schema_ddl": "CREATE TABLE support_tickets (id INT PRIMARY KEY, subject TEXT);"
    })
    assert res_agent.status_code == 201
    agent_id = res_agent.json()["agent_id"]

    # 2. Create a session
    res_sess = client.post("/api/v1/chat/sessions/create", json={
        "agent_id": agent_id,
        "external_user_id": "student_999",
        "user_role": "student"
    })
    session_id = res_sess.json().get("session_id")
    print("Created Session ID:", session_id)

    # 3. Trigger escalation
    res_esc = client.post("/api/v1/chat/escalate", json={
        "session_id": session_id,
        "reason": "Student cannot find fee payment receipt",
        "user_contact": "student999@college.edu",
        "user_query": "My fee receipt is missing from the portal"
    })
    assert res_esc.status_code == 200, res_esc.text
    data = res_esc.json()
    print("Escalation Response:", data)
    assert data["status"] == "success"
    assert data["session_id"] == session_id
    print("[PASS] Escalation API endpoint processed successfully!")

if __name__ == "__main__":
    test_webhook_payload_formatting()
    test_escalation_api_endpoint()
