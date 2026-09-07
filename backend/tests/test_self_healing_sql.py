import asyncio
from app.services.sql.generator import TextToSQLEngine

def test_sql_repair_prompt_generation():
    print("--- 1. Testing SQL Repair Prompt Generation ---")
    user_query = "Show me the top 5 students by marks in CS101"
    failed_sql = "SELECT id, name, marks FROM students ORDER BY marks DESC LIMIT 5"
    db_error = 'column "marks" does not exist; perhaps you meant "cgpa"'
    schema_context = "students(id, name, department, attendance_pct, cgpa)\ncourses(course_id, course_title, open_seats)"

    repair_prompt = TextToSQLEngine.create_sql_repair_prompt(
        user_query=user_query,
        failed_sql=failed_sql,
        error_message=db_error,
        schema_context=schema_context,
        dialect="postgres"
    )

    print("Generated Repair Prompt:\n", repair_prompt)
    assert "Database Error: column \"marks\" does not exist" in repair_prompt
    assert "students(id, name, department, attendance_pct, cgpa)" in repair_prompt
    assert "Failed SQL:" in repair_prompt
    print("[PASS] SQL Repair Prompt correctly formats error and schema context!")

def test_sql_repair_ast_validation():
    print("\n--- 2. Testing Healed SQL AST Validation ---")
    mock_llm_repaired_response = "```sql\nSELECT id, name, cgpa FROM students ORDER BY cgpa DESC LIMIT 5;\n```"
    allowed_tables = {"students", "courses"}

    healed_sql, bound_params = TextToSQLEngine.extract_and_validate(
        raw_llm_response=mock_llm_repaired_response,
        allowed_tables=allowed_tables,
        dialect="postgres"
    )

    print("Validated Healed SQL:", healed_sql)
    assert "cgpa" in healed_sql
    assert "marks" not in healed_sql
    assert "SELECT" in healed_sql
    print("[PASS] Healed SQL successfully validated by AST and sanitized!")

if __name__ == "__main__":
    test_sql_repair_prompt_generation()
    test_sql_repair_ast_validation()
