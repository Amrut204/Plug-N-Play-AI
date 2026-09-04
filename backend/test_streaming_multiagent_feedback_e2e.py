import httpx
import json

BASE_URL = "http://127.0.0.1:8000"

def test_full_features():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    print("--- 1. Testing Registration ---")
    reg_res = client.post("/api/v1/auth/register", json={"org_name": "Acme Innovations", "email": "admin@acme.io"})
    assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"
    auth_data = reg_res.json()
    tenant_id = auth_data["tenant"]["id"]
    print(f"Tenant created: {tenant_id}")

    print("\n--- 2. Testing Multi-Agent Provisioning ---")
    # Agent 1: Support Bot
    ag1_res = client.post(f"/api/v1/agents/{tenant_id}", json={
        "name": "Customer Support Bot",
        "description": "Handles return and refund questions",
        "system_prompt": "You are a customer support agent."
    })
    assert ag1_res.status_code == 201
    ag1_id = ag1_res.json()["id"]

    # Agent 2: Internal HR Bot
    ag2_res = client.post(f"/api/v1/agents/{tenant_id}", json={
        "name": "HR Policy Assistant",
        "description": "Answers leave and payroll queries",
        "system_prompt": "You are an HR assistant."
    })
    assert ag2_res.status_code == 201
    ag2_id = ag2_res.json()["id"]

    # Check detailed agent list
    list_res = client.get(f"/api/v1/agents/tenant/{tenant_id}/detailed")
    assert list_res.status_code == 200
    agents_list = list_res.json()
    assert len(agents_list) >= 2
    print(f"Verified {len(agents_list)} workspace agents.")

    print("\n--- 3. Testing Tenant API Keys ---")
    keys_res = client.get(f"/api/v1/auth/tenants/{tenant_id}/api-keys")
    assert keys_res.status_code == 200
    keys = keys_res.json()
    assert len(keys) >= 1
    print(f"Retrieved active API key: {keys[0]['api_key']}")

    print("\n--- 4. Testing Real-Time Token Streaming (SSE) ---")
    sess_res = client.post("/api/v1/chat/sessions/create", json={
        "agent_id": ag1_id,
        "external_user_id": "test_user_42",
        "user_role": "user"
    })
    assert sess_res.status_code == 201
    session_token = sess_res.json()["session_token"]
    session_id = sess_res.json()["session_id"]

    # Stream query
    with client.stream("POST", "/api/v1/chat/stream", headers={"Authorization": f"Bearer {session_token}"}, json={"query": "Hello! What services do you offer?", "stream": True}) as stream_res:
        assert stream_res.status_code == 200
        events_received = []
        tokens = []
        message_id = None
        for line in stream_res.iter_lines():
            if line.startswith("data: "):
                payload_str = line[6:].strip()
                if payload_str:
                    try:
                        ev = json.loads(payload_str)
                        events_received.append(ev.get("event"))
                        if ev.get("event") == "token":
                            tokens.append(ev.get("token", ""))
                        elif ev.get("event") == "done":
                            message_id = ev.get("message_id")
                    except Exception:
                        pass
        
        assert "meta" in events_received, f"Missing meta event: {events_received}"
        assert "token" in events_received, f"Missing token event: {events_received}"
        assert "done" in events_received, f"Missing done event: {events_received}"
        full_streamed_text = "".join(tokens)
        print(f"Streamed {len(tokens)} token chunks ({len(full_streamed_text)} chars). Msg ID: {message_id}")

    print("\n--- 5. Testing Message Feedback (Thumbs Up/Down Ratings) ---")
    fb_res = client.post("/api/v1/chat/feedback", json={
        "message_id": message_id,
        "session_id": session_id,
        "rating": 1,
        "comment": "Great instant response!"
    })
    assert fb_res.status_code == 200
    assert fb_res.json()["status"] == "success"
    print("Recorded positive message feedback (Thumbs Up).")

    print("\n--- 6. Testing Analytics & CSAT Overview ---")
    an_res = client.get(f"/api/v1/analytics/{tenant_id}/overview")
    assert an_res.status_code == 200
    overview = an_res.json()
    assert overview["total_queries"] >= 1
    assert overview["csat_score"] == 100.0
    assert overview["feedback_breakdown"]["thumbs_up"] >= 1
    print(f"Analytics Verified: Total Queries = {overview['total_queries']}, CSAT = {overview['csat_score']}%")

    print("\n=======================================================")
    print("ALL 3 PLATFORM FEATURES (STREAMING, MULTI-AGENT, FEEDBACK/ANALYTICS) VERIFIED 100% SUCCESS!")
    print("=======================================================")

if __name__ == "__main__":
    test_full_features()
