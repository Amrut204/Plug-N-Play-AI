import httpx
import json

BASE_URL = "http://127.0.0.1:8000"

def test_zero_knowledge_workflow():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    print("--- 1. Testing Zero-Knowledge Schema Parser (/connections/parse-schema) ---")
    sample_ddl = """
    CREATE TABLE students (
        id INT PRIMARY KEY,
        name VARCHAR(100),
        department VARCHAR(50),
        attendance_pct DECIMAL(5,2),
        cgpa DECIMAL(3,2)
    );

    CREATE TABLE courses (
        course_id INT PRIMARY KEY,
        title VARCHAR(150),
        open_seats INT
    );
    """
    res = client.post("/api/v1/connections/parse-schema", json={"schema_text": sample_ddl})
    assert res.status_code == 200, f"Failed parse-schema: {res.text}"
    p_data = res.json()
    print("Parsed tables:", p_data.get("table_names"))
    assert "students" in p_data.get("table_names")
    assert "courses" in p_data.get("table_names")
    print("[PASS] Schema parser verified!")

    print("\n--- 2. Testing Quickstart Setup in Zero-Knowledge Mode ---")
    setup_payload = {
        "project_name": "Apex University ERP",
        "agent_name": "Dean Assistant",
        "service_type": "hybrid",
        "target_audience": "end_user",
        "connection_mode": "schema_only",
        "schema_ddl": sample_ddl,
        "document_title": "Academic Attendance Policy",
        "document_content": "Students with attendance above 75% are eligible for final semester examinations."
    }
    res2 = client.post("/api/v1/quickstart/setup", json=setup_payload)
    assert res2.status_code == 201, f"Failed setup: {res2.text}"
    agent_info = res2.json()
    agent_id = agent_info["agent_id"]
    print(f"Provisioned Zero-Knowledge Agent: {agent_id}")
    print("[PASS] Quickstart Zero-Knowledge onboarding verified!")

    print("\n--- 3. Testing Generate-SQL for Client Backend Bridge (/chat/generate-sql) ---")
    gen_payload = {
        "agent_id": agent_id,
        "query": "How many students have attendance above 75%?",
        "user_id": "prof_smith",
        "user_role": "faculty"
    }
    res3 = client.post("/api/v1/chat/generate-sql", json=gen_payload)
    assert res3.status_code == 200, f"Failed generate-sql: {res3.text}"
    sql_data = res3.json()
    print("Generated Safe SQL:", sql_data.get("sql_query"))
    assert sql_data.get("guardrail_blocked") is False
    assert sql_data.get("sql_query") is not None
    assert "SELECT" in sql_data.get("sql_query").upper()
    print("[PASS] Zero-Knowledge SQL generation verified!")

    print("\n--- 4. Testing Format-SQL-Response from Local DB Execution ---")
    # Simulate client executing the query on their private database
    mock_db_results = [{"attendance_above_75_count": 142}]
    fmt_payload = {
        "agent_id": agent_id,
        "query": "How many students have attendance above 75%?",
        "sql_query": sql_data.get("sql_query"),
        "db_results": mock_db_results,
        "user_role": "faculty"
    }
    res4 = client.post("/api/v1/chat/format-sql-response", json=fmt_payload)
    assert res4.status_code == 200, f"Failed format-sql-response: {res4.text}"
    fmt_data = res4.json()
    print("Synthesized Answer:", fmt_data.get("answer"))
    assert len(fmt_data.get("answer")) > 0
    print("[PASS] Natural language response synthesis verified!")

    print("\n=======================================================")
    print("ALL ZERO-KNOWLEDGE SCHEMA-ONLY BRIDGE TESTS PASSED 100%!")
    print("=======================================================")

if __name__ == "__main__":
    test_zero_knowledge_workflow()
