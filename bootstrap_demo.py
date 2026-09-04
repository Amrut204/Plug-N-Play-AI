import asyncio
import os
import sys

# Ensure paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import AsyncSessionLocal, init_db
from app.models.tenants import Tenant
from app.models.agents import Agent
from app.models.connections import Connection, SemanticTable, SemanticColumn
from app.models.rag import RAGSource, RAGChunk
from app.services.rag.chunker import TextChunker
from app.services.rag.embedder import EmbeddingService
from app.core.crypto import CryptoService
from sqlalchemy import select

import importlib.util

SEED_PATH = os.path.join(ROOT_DIR, "examples", "college-erp", "database", "seed_data.py")
spec = importlib.util.spec_from_file_location("seed_data_mod", SEED_PATH)
seed_data_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed_data_mod)
init_and_seed_college_db = seed_data_mod.init_and_seed_college_db

COLLEGE_SHARED_SECRET = "college_erp_hmac_secret_key_987654"


async def bootstrap():
    print("1. Seeding College ERP database (college.db)...")
    init_and_seed_college_db()

    print("2. Initializing Plug-N-Play Platform Database...")
    await init_db()

    async with AsyncSessionLocal() as session:
        # Check if tenant exists
        stmt = select(Tenant).where(Tenant.slug == "apex-institute")
        res = await session.execute(stmt)
        tenant = res.scalars().first()

        if not tenant:
            print("3. Creating Tenant: Apex Institute of Technology...")
            tenant = Tenant(name="Apex Institute of Technology", slug="apex-institute")
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
        else:
            print(f"3. Found existing Tenant: {tenant.name}")

        # Check if agent exists
        stmt_agent = select(Agent).where(Agent.tenant_id == tenant.id)
        res_agent = await session.execute(stmt_agent)
        agent = res_agent.scalars().first()

        if not agent:
            print("4. Creating AI Agent: Apex Student AI Advisor...")
            agent = Agent(
                tenant_id=tenant.id,
                name="Apex Student AI Advisor",
                system_prompt="You are the official student academic advisor for Apex Institute of Technology."
            )
            session.add(agent)
            await session.commit()
            await session.refresh(agent)
        else:
            print(f"4. Found existing Agent: {agent.name}")

        # Check if connection exists
        stmt_conn = select(Connection).where(Connection.tenant_id == tenant.id)
        res_conn = await session.execute(stmt_conn)
        connection = res_conn.scalars().first()

        if not connection:
            print("5. Registering Connection: http://127.0.0.1:5050/api/v1/connector...")
            connection = Connection(
                tenant_id=tenant.id,
                name="Apex College ERP Production Gateway",
                connection_type="connector_http",
                endpoint_url="http://127.0.0.1:5050/api/v1/connector",
                auth_secret_hash=CryptoService.encrypt(COLLEGE_SHARED_SECRET)
            )
            session.add(connection)
            await session.commit()
            await session.refresh(connection)
        else:
            # Ensure URL points to port 5050 and secret is encrypted
            connection.endpoint_url = "http://127.0.0.1:5050/api/v1/connector"
            connection.auth_secret_hash = CryptoService.encrypt(COLLEGE_SHARED_SECRET)
            await session.commit()
            print(f"5. Found Connection: {connection.name} -> {connection.endpoint_url}")

        # Ingest policies into RAG if needed
        stmt_source = select(RAGSource).where(RAGSource.tenant_id == tenant.id)
        res_source = await session.execute(stmt_source)
        source = res_source.scalars().first()

        if not source:
            print("6. Creating RAG Knowledge Source...")
            source = RAGSource(
                tenant_id=tenant.id,
                agent_id=agent.id,
                name="Apex Examination & Academic Regulations"
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)

            # Ingest docs
            policies_dir = os.path.join(ROOT_DIR, "examples", "college-erp", "policies")
            total_chunks = 0
            for fname in os.listdir(policies_dir):
                if fname.endswith(".md"):
                    fpath = os.path.join(policies_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        text = f.read()
                    chunks = TextChunker.chunk_text(text, chunk_size=400, chunk_overlap=50)
                    for c_str in chunks:
                        emb = await EmbeddingService.get_embedding(c_str)
                        chunk_obj = RAGChunk(
                            tenant_id=tenant.id,
                            rag_source_id=source.id,
                            content=c_str,
                            doc_metadata={
                                "title": fname.replace(".md", "").replace("_", " ").title(),
                                "allowed_roles": ["student", "faculty", "admin"]
                            },
                            embedding=emb
                        )
                        session.add(chunk_obj)
                        total_chunks += 1

            await session.commit()
            print(f"6. Ingested {total_chunks} policy chunks into RAG Knowledge Base.")
        else:
            print(f"6. Found existing RAG Source with indexed policy documents.")

    print("\n[SUCCESS] Bootstrap completed successfully!")


if __name__ == "__main__":
    asyncio.run(bootstrap())
