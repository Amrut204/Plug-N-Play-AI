import asyncio
from app.core.database import engine
from sqlalchemy import text

async def add_feedback_columns():
    async with engine.begin() as conn:
        print("Adding feedback columns to chat_messages if not existing...")
        await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS feedback_rating INTEGER;"))
        await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS feedback_comment TEXT;"))
        print("Columns added successfully!")

if __name__ == "__main__":
    asyncio.run(add_feedback_columns())
