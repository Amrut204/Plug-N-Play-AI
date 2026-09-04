import httpx

def test_multi_database_setup():
    client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60.0)

    print("--- Testing Multi-Database Quickstart Setup ---")
    payload = {
        "project_name": "Multi-Campus ERP",
        "agent_name": "Campus Master Bot",
        "service_type": "hybrid",
        "target_audience": "end_user",
        "connection_mode": "direct",
        "databases": [
            {
                "name": "Academics DB (Postgres)",
                "engine": "postgresql",
                "database_url": "postgresql://mock_user:mock_pass@localhost:5432/academics",
                "selected_tables": ["students", "courses", "grades"]
            },
            {
                "name": "Finance DB (MySQL)",
                "engine": "mysql",
                "database_url": "mysql://mock_user:mock_pass@localhost:3306/finance",
                "selected_tables": ["fees", "invoices", "payments"]
            }
        ],
        "document_title": "Multi-Campus Rules",
        "document_content": "Attendance policy requires 75% minimum across all university departments."
    }

    res = client.post("/api/v1/quickstart/setup", json=payload)
    print("Setup Status:", res.status_code)
    assert res.status_code == 201
    data = res.json()
    print("Agent ID:", data["agent_id"])
    print("[PASS] Multi-database agent provisioned successfully!")

if __name__ == "__main__":
    test_multi_database_setup()
