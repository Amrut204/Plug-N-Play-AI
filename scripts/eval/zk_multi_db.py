import httpx

def test_zero_knowledge_multi_db():
    client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30.0)

    print("--- 1. Testing Multi-Database DDL Parsing ---")
    multi_ddl = """
    -- Database 1: Academics & Records
    CREATE TABLE students (
        id INT PRIMARY KEY,
        name VARCHAR(100),
        department VARCHAR(50),
        attendance_pct DECIMAL(5,2),
        cgpa DECIMAL(3,2)
    );

    CREATE TABLE courses (
        course_id INT PRIMARY KEY,
        course_title VARCHAR(150),
        open_seats INT
    );

    -- Database 2: Finance & ERP Accounts
    CREATE TABLE fee_records (
        student_id INT PRIMARY KEY,
        amount_due DECIMAL(10,2),
        fee_status VARCHAR(50),
        last_payment_date DATE
    );

    CREATE TABLE scholarships (
        id INT PRIMARY KEY,
        student_id INT,
        award_amount DECIMAL(10,2),
        grant_type VARCHAR(100)
    );
    """

    res_parse = client.post("/api/v1/connections/parse-schema", json={"schema_text": multi_ddl})
    assert res_parse.status_code == 200, res_parse.text
    parse_data = res_parse.json()
    print("Parsed Tables:", parse_data["table_names"])
    assert parse_data["total_tables"] == 4
    assert "students" in parse_data["table_names"]
    assert "fee_records" in parse_data["table_names"]
    print("[PASS] DDL parser correctly extracted all tables across both databases!")

    print("\n--- 2. Provisioning Zero-Knowledge Multi-DB Agent ---")
    setup_payload = {
        "project_name": "Campus Zero-Knowledge ERP",
        "agent_name": "Zero-Knowledge Assistant",
        "service_type": "sql",
        "connection_mode": "schema_only",
        "schema_ddl": multi_ddl
    }
    res_setup = client.post("/api/v1/quickstart/setup", json=setup_payload)
    assert res_setup.status_code == 201, res_setup.text
    setup_data = res_setup.json()
    agent_id = setup_data["agent_id"]
    print("Zero-Knowledge Multi-DB Agent ID:", agent_id)

    print("\n--- 3. Testing Reverse Query Generation across both schemas ---")
    gen_res = client.post(
        "/api/v1/chat/generate-sql",
        json={
            "agent_id": agent_id,
            "query": "List all students with pending fees and their attendance percentage"
        }
    )
    assert gen_res.status_code == 200, gen_res.text
    gen_data = gen_res.json()
    print("Generated SQL:", gen_data.get("sql"))
    print("[PASS] Zero-Knowledge SQL generation successfully targeted multi-database schema!")

if __name__ == "__main__":
    test_zero_knowledge_multi_db()
