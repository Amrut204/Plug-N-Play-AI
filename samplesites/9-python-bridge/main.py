# main.py — Python FastAPI Zero-Knowledge Bridge Server
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Plug-N-Play Python Zero-Knowledge Bridge")

PNP_HOST = os.getenv("PNP_HOST", "https://plug-n-play-rag.onrender.com")
AGENT_ID = os.getenv("PNP_AGENT_ID", "YOUR_AGENT_ID")
MASTER_KEY = os.getenv("PNP_MASTER_API_KEY", "")

# Simulated private on-premise records (Inside client's firewall)
LOCAL_PRIVATE_DB = {
    "orders": [
        {"order_id": "ORD-901", "customer_name": "John Doe", "status": "Delivered", "total_amount": 349.99, "delivery_days": 2},
        {"order_id": "ORD-902", "customer_name": "Jane Smith", "status": "Processing", "total_amount": 129.50, "delivery_days": 3},
        {"order_id": "ORD-903", "customer_name": "Alex Brown", "status": "Shipped", "total_amount": 99.00, "delivery_days": 1}
    ],
    "students": [
        {"student_id": "STU101", "name": "Aarav Sharma", "dept": "Computer Science", "attendance": 88.5, "cgpa": 8.92},
        {"student_id": "STU102", "name": "Priya Patel", "dept": "Information Technology", "attendance": 94.0, "cgpa": 9.15},
        {"student_id": "STU103", "name": "Rohan Verma", "dept": "Mechanical Engineering", "attendance": 71.0, "cgpa": 6.45},
    ]
}

# Mount static folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"status": "online", "bridge": "Python FastAPI Zero-Knowledge"}


class ChatRequest(BaseModel):
    query: str
    userId: Optional[str] = "student_user"
    userRole: Optional[str] = "user"


# =========================================================================
# 📍 WHERE TO PLACE IN AN EXISTING PRODUCTION CODEBASE:
# In your existing FastAPI / Flask / Django codebase, do NOT replace
# your whole file! Just add this single endpoint function below.
# =========================================================================
@app.post("/api/ai-chat")
async def chat_bridge(payload: ChatRequest):
    headers = {"Content-Type": "application/json"}
    if MASTER_KEY:
        headers["Authorization"] = f"Bearer {MASTER_KEY}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Ask Plug-N-Play AI to synthesize safe SQL from schema (No DB access given to cloud)
        gen_res = await client.post(
            f"{PNP_HOST}/api/v1/chat/generate-sql",
            headers=headers,
            json={
                "agent_id": AGENT_ID,
                "query": payload.query,
                "user_id": payload.userId,
                "user_role": payload.userRole or "user"
            }
        )

        if gen_res.status_code != 200:
            raise HTTPException(status_code=gen_res.status_code, detail=gen_res.text)

        gen_data = gen_res.json()
        if gen_data.get("guardrail_blocked"):
            return {"answer": gen_data.get("refusal_message"), "route": "GUARDRAIL_BLOCKED"}

        sql = gen_data.get("sql_query")
        db_rows = []

        # Step 2: Execute locally on your private database (Inside your firewall)
        if sql:
            print(f"[Python Bridge] Executing safe local SQL: {sql}")
            db_rows = LOCAL_PRIVATE_DB["students"]

        # Step 3: Send raw query results back to Plug-N-Play for natural language formatting
        format_res = await client.post(
            f"{PNP_HOST}/api/v1/chat/format-sql-response",
            headers={"Content-Type": "application/json"},
            json={
                "agent_id": AGENT_ID,
                "query": payload.query,
                "sql_query": sql or "",
                "db_results": db_rows
            }
        )

        format_data = format_res.json()
        return {
            "answer": format_data.get("answer", "Query completed."),
            "sql_executed": sql,
            "local_rows_count": len(db_rows)
        }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    print(f"[Python Bridge Server] Running on http://127.0.0.1:{port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
