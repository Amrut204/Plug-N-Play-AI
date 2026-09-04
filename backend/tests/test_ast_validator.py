import pytest
from app.services.sql.validator import SQLASTValidator, SQLSecurityViolation


def test_valid_select_query():
    sql = "SELECT student_id, attendance_percentage FROM attendance WHERE subject = 'Database Systems'"
    allowed_tables = {"attendance", "students"}
    
    sanitized_sql, bound_params = SQLASTValidator.validate_and_sanitize(
        raw_sql=sql,
        allowed_tables=allowed_tables,
        max_limit=25
    )
    
    assert "SELECT" in sanitized_sql
    assert "LIMIT 25" in sanitized_sql


def test_forbidden_operations_blocked():
    allowed_tables = {"attendance", "students"}
    
    dangerous_queries = [
        "DROP TABLE students",
        "DELETE FROM attendance WHERE student_id = 'STU_1001'",
        "UPDATE students SET cgpa = 10.0",
        "INSERT INTO students (student_id) VALUES ('HACKED')",
        "ALTER TABLE students ADD COLUMN secret TEXT",
        "TRUNCATE TABLE attendance"
    ]
    
    for q in dangerous_queries:
        with pytest.raises(SQLSecurityViolation):
            SQLASTValidator.validate_and_sanitize(raw_sql=q, allowed_tables=allowed_tables)


def test_multi_statement_injection_blocked():
    sql = "SELECT * FROM attendance; DROP TABLE students;"
    allowed_tables = {"attendance", "students"}
    
    with pytest.raises(SQLSecurityViolation):
        SQLASTValidator.validate_and_sanitize(raw_sql=sql, allowed_tables=allowed_tables)


def test_unauthorized_table_blocked():
    sql = "SELECT * FROM faculty_payroll"
    allowed_tables = {"attendance", "students"}
    
    with pytest.raises(SQLSecurityViolation):
        SQLASTValidator.validate_and_sanitize(raw_sql=sql, allowed_tables=allowed_tables)


def test_forbidden_column_blocked():
    sql = "SELECT password_hash FROM students"
    allowed_tables = {"students"}
    allowed_columns = {"students": {"student_id", "name", "cgpa"}}
    
    with pytest.raises(SQLSecurityViolation):
        SQLASTValidator.validate_and_sanitize(
            raw_sql=sql,
            allowed_tables=allowed_tables,
            allowed_columns=allowed_columns
        )


def test_row_identity_binding_injection():
    sql = "SELECT subject, attendance_percentage FROM attendance"
    allowed_tables = {"attendance"}
    identity_filter = ("attendance", "student_id", "STU_1001")
    
    sanitized_sql, bound_params = SQLASTValidator.validate_and_sanitize(
        raw_sql=sql,
        allowed_tables=allowed_tables,
        identity_filter=identity_filter
    )
    
    assert "attendance.student_id" in sanitized_sql
    assert "auth_student_id" in sanitized_sql or "auth_user_id" in sanitized_sql
    assert bound_params["auth_student_id"] == "STU_1001"
