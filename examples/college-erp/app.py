import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

# Ensure connector-sdk is importable
SDK_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "connector-sdk", "python"))
if SDK_PATH not in sys.path:
    sys.path.insert(0, SDK_PATH)

from plug_n_play_connector import (
    create_connector_router,
    TableSchema,
    ColumnSchema,
    SQLiteExecutor
)

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "college.db")
SHARED_SECRET = "college_erp_hmac_secret_key_987654"

# 1. Define College Semantic Schema Dictionary
COLLEGE_SCHEMA = [
    TableSchema(
        table_name="students",
        business_name="Students Roster",
        description="Official academic directory of registered students",
        allowed_roles=["admin", "student", "faculty"],
        columns=[
            ColumnSchema("student_id", "TEXT", "Unique student registration ID", row_identity_binding="auth_user_id"),
            ColumnSchema("name", "TEXT", "Full legal name of the student"),
            ColumnSchema("department", "TEXT", "Academic department/major"),
            ColumnSchema("year_of_study", "INTEGER", "Current year of study (1 to 4)"),
            ColumnSchema("cgpa", "REAL", "Cumulative Grade Point Average (0.0 - 10.0)"),
            ColumnSchema("email", "TEXT", "Official institutional email address", is_sensitive=True)
        ]
    ),
    TableSchema(
        table_name="attendance",
        business_name="Classroom Attendance Records",
        description="Course-wise subject attendance statistics for enrolled students",
        allowed_roles=["admin", "student", "faculty"],
        columns=[
            ColumnSchema("id", "INTEGER", "Primary record key"),
            ColumnSchema("student_id", "TEXT", "Associated student identifier", row_identity_binding="auth_user_id"),
            ColumnSchema("subject", "TEXT", "Enrolled course subject title"),
            ColumnSchema("total_classes", "INTEGER", "Total lectures scheduled to date"),
            ColumnSchema("attended_classes", "INTEGER", "Total lectures physically attended"),
            ColumnSchema("attendance_percentage", "REAL", "Computed attendance percentage")
        ]
    ),
    TableSchema(
        table_name="marks",
        business_name="Academic Examination Marks",
        description="Examination scores and letter grades across course subjects",
        allowed_roles=["admin", "student", "faculty"],
        columns=[
            ColumnSchema("id", "INTEGER", "Primary key"),
            ColumnSchema("student_id", "TEXT", "Student identifier", row_identity_binding="auth_user_id"),
            ColumnSchema("subject", "TEXT", "Course subject title"),
            ColumnSchema("score", "REAL", "Points achieved in examination"),
            ColumnSchema("max_score", "REAL", "Maximum achievable score in subject"),
            ColumnSchema("grade", "TEXT", "Letter grade awarded (e.g. A+, A, B, O)")
        ]
    ),
    TableSchema(
        table_name="fees",
        business_name="Tuition Fee Ledger",
        description="Financial account balance and fee status for students",
        allowed_roles=["admin", "student"],
        columns=[
            ColumnSchema("id", "INTEGER", "Ledger key"),
            ColumnSchema("student_id", "TEXT", "Student identifier", row_identity_binding="auth_user_id"),
            ColumnSchema("total_fees", "REAL", "Total semester tuition fee levied"),
            ColumnSchema("amount_paid", "REAL", "Total fee remitted to date"),
            ColumnSchema("pending_due", "REAL", "Outstanding balance payable"),
            ColumnSchema("due_date", "TEXT", "Payment settlement deadline")
        ]
    )
]

app = FastAPI(title="Apex Institute of Technology - College ERP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Mount Standard Plug-N-Play Connector Router (Plug-and-play in 2 lines!)
connector_router = create_connector_router(
    shared_secret=SHARED_SECRET,
    executor=SQLiteExecutor(DB_PATH),
    tables=COLLEGE_SCHEMA
)
app.include_router(connector_router, prefix="/api/v1/connector", tags=["Plug-N-Play Connector Bridge"])


@app.get("/", response_class=HTMLResponse)
async def student_portal():
    """Simple Student Portal demonstrating the embedded AI assistant."""
    session_token = ""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post("http://127.0.0.1:8000/api/v1/chat/sessions/create", json={
                "agent_id": "default",
                "external_user_id": "STU_1001",
                "user_role": "student"
            })
            if resp.status_code == 201:
                session_token = resp.json().get("session_token", "")
    except Exception:
        pass

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Apex Institute - Student Academic Portal</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --primary: #4338ca;
                --primary-hover: #3730a3;
                --bg: #0f172a;
                --card-bg: rgba(30, 41, 59, 0.7);
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --border: rgba(255, 255, 255, 0.1);
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }}
            body {{ background: var(--bg); color: var(--text); min-height: 100vh; padding: 2rem; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; }}
            .badge {{ background: #10b98120; color: #10b981; border: 1px solid #10b98140; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.85rem; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; margin-top: 2rem; }}
            .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; backdrop-filter: blur(12px); }}
            .card h3 {{ color: var(--text-muted); font-size: 0.9rem; font-weight: 500; }}
            .card .val {{ font-size: 2rem; font-weight: 700; margin-top: 0.5rem; color: #fff; }}
            .tag-low {{ color: #ef4444; font-weight: 600; }}
            .tag-good {{ color: #10b981; font-weight: 600; }}
            .info-box {{ margin-top: 2rem; background: rgba(67, 56, 202, 0.15); border: 1px solid rgba(67, 56, 202, 0.4); padding: 1.25rem; border-radius: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h2>Apex Institute of Technology</h2>
                <p style="color: var(--text-muted);">Student Portal &bull; Logged in as <strong>Alex Johnson (STU_1001)</strong></p>
            </div>
            <span class="badge">Connected to Plug-N-Play AI Layer</span>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Cumulative GPA</h3>
                <div class="val">8.4 / 10.0</div>
                <p style="color: var(--text-muted); margin-top: 0.5rem;">Academic Year 3 &bull; CSE</p>
            </div>
            <div class="card">
                <h3>Database Systems</h3>
                <div class="val tag-low">71.1%</div>
                <p style="color: #ef4444; margin-top: 0.5rem;">&bull; Below 75% Examination Threshold</p>
            </div>
            <div class="card">
                <h3>Data Structures</h3>
                <div class="val tag-good">82.0%</div>
                <p style="color: #10b981; margin-top: 0.5rem;">&bull; In Good Standing</p>
            </div>
            <div class="card">
                <h3>Tuition Fees Status</h3>
                <div class="val" style="color: #10b981;">PAID</div>
                <p style="color: var(--text-muted); margin-top: 0.5rem;">INR 0.00 Outstanding</p>
            </div>
        </div>

        <div class="info-box">
            <h4>💡 Plug-N-Play AI Assistant Active</h4>
            <p style="color: var(--text-muted); margin-top: 0.5rem;">
                Click the AI Assistant floating widget in the bottom right to query your live marks, attendance records, or ask about college policies!
            </p>
        </div>

        <!-- Embedded Plug-N-Play AI Widget -->
        <script src="http://127.0.0.1:8000/static/pnp-widget.js" 
                data-api-host="http://127.0.0.1:8000" 
                data-session-token="{session_token}">
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5050)
