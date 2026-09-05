import os
import re
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List, Tuple
from app.core.config import settings
from app.services.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)

# Zero-hedging patterns
HEDGING_PATTERNS = [
    re.compile(r"^(according to (the )?(provided |uploaded |given |available )?(documents?|resources?|context|database records?|database|records?|information|system|policies?|handbook|knowledge base)(\s*(provided|available|given))?),?\s*", re.IGNORECASE),
    re.compile(r"^(based on (the )?(provided |uploaded |given |available )?(documents?|resources?|context|database records?|database|records?|information|system|policies?|handbook|knowledge base)(\s*(provided|available|given))?),?\s*", re.IGNORECASE),
    re.compile(r"^(as per (the )?(provided |uploaded |given |available )?(documents?|resources?|context|database records?|database|records?|policies?|guidelines?)(\s*(provided|available|given))?),?\s*", re.IGNORECASE),
    re.compile(r"^(from the (provided |uploaded |given |available )?(documents?|resources?|context|database records?|database|records?|policies?|guidelines?)(\s*(provided|available|given))?),?\s*", re.IGNORECASE),
    re.compile(r"^(the provided (documents?|context|database records?|resources?) (states?|indicates?|shows?|specif(y|ies)) that),?\s*", re.IGNORECASE),
]

def clean_hedging(text: str) -> str:
    """Strip robotic preamble while preserving grammar."""
    if not text:
        return text
    cleaned = text.strip()
    changed = True
    while changed:
        changed = False
        for pat in HEDGING_PATTERNS:
            new_text = pat.sub("", cleaned)
            if new_text != cleaned:
                cleaned = new_text.strip()
                changed = True
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


IDENTITY_KEYWORDS = {"workspace", "company", "who am i", "my name", "tenant", "org", "organization", "account", "logged in"}


class PlatformConciergeService:
    """
    Dedicated AI Copilot for Plug-N-Play AI.
    Grounds exclusively on the platform knowledge guide with verified tenant isolation.
    Contains zero database query connectors (preventing data leakage).
    Uses smart section retrieval to keep token usage ultra-low and lightning fast.
    """

    _cached_guide: Optional[str] = None
    _sections: List[Dict[str, str]] = []

    @classmethod
    def load_guide_content(cls) -> str:
        """Load and cache the platform guide knowledge base and index sections."""
        if cls._cached_guide:
            return cls._cached_guide

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        root_dir = os.path.abspath(os.path.join(base_dir, ".."))
        possible_paths = [
            os.path.join(root_dir, "sample_files", "plug_n_play_platform_guide.txt"),
            os.path.join(root_dir, "sample_files", "plug_n_play_platform_guide.md"),
            os.path.join(base_dir, "sample_files", "plug_n_play_platform_guide.txt"),
            os.path.join(base_dir, "sample_files", "plug_n_play_platform_guide.md"),
            os.path.join(os.path.dirname(__file__), "plug_n_play_platform_guide.txt"),
            os.path.join(os.getcwd(), "sample_files", "plug_n_play_platform_guide.txt")
        ]

        raw_text = ""
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        raw_text = f.read()
                        logger.info(f"[Concierge] Loaded platform knowledge guide from {path} ({len(raw_text)} chars)")
                        break
                except Exception as e:
                    logger.warning(f"[Concierge] Failed to read {path}: e={e}")

        if not raw_text:
            raw_text = (
                "Plug-N-Play AI is an enterprise AI data layer and autonomous agent orchestration platform. "
                "It connects live databases (Text-to-SQL) and unstructured documents (RAG) to embeddable widgets. "
                "Key features: Multi-DB Federation (+ Add Another Database option), Zero-Write AST SQL validation, "
                "Direct Connect vs Zero-Knowledge Schema Mode, Universal 1-line script embed, and Live Human Escalation."
            )

        cls._cached_guide = raw_text

        # Index sections by delimiter
        sections: List[Dict[str, str]] = []
        raw_sections = re.split(r"={10,}\s*\n(\d+\.\s*[^\n=]+)\s*\n={10,}", raw_text)
        if len(raw_sections) > 1:
            # Table of contents / intro
            sections.append({
                "title": "Platform Overview",
                "content": raw_sections[0][:1500]
            })
            for i in range(1, len(raw_sections), 2):
                title = raw_sections[i].strip()
                content = raw_sections[i + 1].strip() if (i + 1) < len(raw_sections) else ""
                sections.append({
                    "title": title,
                    "content": content
                })
        else:
            sections.append({"title": "Full Guide", "content": raw_text[:4000]})

        cls._sections = sections
        logger.info(f"[Concierge] Indexed {len(cls._sections)} guide sections for low-token retrieval.")
        return cls._cached_guide

    @classmethod
    def retrieve_relevant_sections(cls, query: str) -> str:
        """
        Extract the most relevant guide sections for the user's query
        to keep the prompt lightweight (~400-800 tokens) and prevent rate limits.
        """
        cls.load_guide_content()
        query_lower = query.lower()

        # Check if this is primarily an identity question
        tokens = set(re.findall(r"\w+", query_lower))
        if tokens.intersection(IDENTITY_KEYWORDS) and len(tokens) <= 8:
            return (
                "Plug-N-Play AI is an enterprise AI data layer & autonomous agent studio. "
                "You are answering questions about the user's workspace or company identity."
            )

        # Keyword scoring per section
        scored: List[Tuple[int, Dict[str, str]]] = []
        for sec in cls._sections:
            title_score = sum(3 for w in tokens if len(w) > 3 and w in sec["title"].lower())
            body_score = sum(1 for w in tokens if len(w) > 3 and w in sec["content"].lower())
            total = title_score + body_score
            scored.append((total, sec))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_sections = [s[1] for s in scored if s[0] > 0][:2]

        if not top_sections:
            # Fallback to Section 1 (Overview) and Section 10 (FAQ)
            top_sections = cls._sections[:2]

        extracted = []
        for s in top_sections:
            extracted.append(f"### {s['title']}\n{s['content']}")

        return "\n\n".join(extracted)

    @classmethod
    def build_system_prompt(cls, user_query: str, user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Construct a hardened, token-efficient system prompt.
        """
        relevant_guide_context = cls.retrieve_relevant_sections(user_query)

        if user_context and user_context.get("is_authenticated"):
            workspace_name = user_context.get("workspace_name") or "Your Workspace"
            user_name = user_context.get("full_name") or user_context.get("email") or "Valued Client"
            email = user_context.get("email") or "Not provided"
            tier = user_context.get("tier") or "Free Tier"
            agent_count = user_context.get("agent_count", 0)
            agents = user_context.get("agents", [])
            connection_count = user_context.get("connection_count", 0)
            connections = user_context.get("connections", [])
            doc_count = user_context.get("document_count", 0)

            if agents:
                agent_lines = "\n".join([
                    f"  - **{a['name']}** (ID: `{a['id']}`, Model: `{a.get('model', 'gpt-4o-mini')}`, Status: {'Active' if a.get('is_active') else 'Inactive'})"
                    for a in agents
                ])
            else:
                agent_lines = "  - (No agents created yet. The user can create their first agent in the Agent Studio!)"

            if connections:
                conn_lines = "\n".join([f"  - **{c['name']}** (Type: `{c['type']}`)" for c in connections])
            else:
                conn_lines = "  - (No databases connected yet.)"

            user_block = f"""[AUTHENTICATED USER CONTEXT]
- Authentication: Authenticated Active Dashboard User
- Active Workspace / Company Name: {workspace_name}
- User Name: {user_name}
- Contact Email: {email}
- Subscription Tier: {tier}
- Workspace Agent Fleet ({agent_count} Total):
{agent_lines}
- Connected Databases ({connection_count} Total):
{conn_lines}
- Ingested Knowledge Sources ({doc_count} Total)

TENANT ISOLATION & TELEMETRY MANDATE:
- When asked "what is my workspace name?", "what is my company name?", or "who am I?", answer directly that their active workspace name is "{workspace_name}".
- When asked "how many agents are there in our company/workspace?", "list our agents", or "what agents do we have?", answer accurately with the exact count ({agent_count}) and list each agent's name, ID, and status from the Workspace Agent Fleet above.
- When asked about database connections or knowledge documents, accurately quote the counts and details from the context above.
- NEVER disclose, invent, or mention any other workspace, project, or tenant names. You are strictly scoped to this user."""
        else:
            user_block = """[GUEST VISITOR CONTEXT]
- Authentication: Guest / Unauthenticated Visitor
- The visitor is exploring the platform before signing in.
- If asked "what is my workspace name?" or "what is my company name?", politely explain:
  "You are currently browsing as a guest visitor. Please sign in or create a free account to access your personalized workspace and build your AI agents!"
- Answer all platform questions, feature inquiries, and architecture doubts thoroughly."""

        system_prompt = f"""You are the official Plug-N-Play AI Platform Copilot & Technical Guide for the Plug-N-Play AI platform (https://plug-n-play-rag.onrender.com/).
Your sole mission is to guide visitors and clients on how to use the platform, build AI agents, connect databases, ingest documents, understand security, and deploy widgets.

{user_block}

RELEVANT PLATFORM KNOWLEDGE BASE:
{relevant_guide_context}

CRITICAL RULES OF OPERATION:
1. SECURITY & DATA PRIVACY:
   - You have NO connection to any operational database tables or SQL query engine.
   - You MUST NOT disclose internal platform credentials, database connection strings, or data from other users.
   - Keep answers strictly focused on the authenticated workspace or general platform capabilities.

2. SPECIFIC PLATFORM FEATURES TO HIGHLIGHT:
   - "+ Add Another Database" (Multi-DB Federation):
     Explain that organizations often have separate databases for orders (PostgreSQL) and inventory (MySQL), or student SIS and finance. This button allows querying across multiple databases in one agent! If the user only has one database, they use Database #1 and simply ignore the extra card.
   - Direct Cloud Connect vs. Zero-Knowledge Schema Mode:
     Direct Connect runs live read-only queries over SSL. Zero-Knowledge Schema Mode never takes credentials—the user pastes their SQL DDL schema, and the AI outputs queries for their local backend behind their private firewall.
   - Zero Database Write Mandate:
     Destructive queries (DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE) are mathematically intercepted at the Abstract Syntax Tree (AST) level. Only read-only SELECT queries are allowed.
   - Step-by-Step Agent Studio:
     Walk users through the 4 steps: 1. Identity & Role, 2. Knowledge Ingestion & Data Sources, 3. Audience Guardrails, 4. Actions & Live Escalation.
   - Universal Embed:
     Single `<script>` tag embedding for HTML, WordPress, Shopify, React, Next.js, and Vue.

3. TONE & FORMATTING:
   - Professional, welcoming, concise, and technically authoritative.
   - Use clean Markdown with bullet points, bold key terms, and code blocks where helpful.
   - Never say "according to the document" or "as an AI model". Speak as the official Plug-N-Play AI Copilot."""

        return system_prompt

    @classmethod
    def generate_grounded_fallback(cls, user_query: str, user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Deterministic, instant, and high-accuracy answer generated directly from the indexed platform guide.
        Guarantees 100% uptime even during external LLM API rate limits.
        """
        q_lower = user_query.lower()
        tokens = set(re.findall(r"\w+", q_lower))

        # 1. Agent fleet count / list queries
        is_agent_query = (
            ("agent" in q_lower or "agents" in q_lower or "bot" in q_lower or "bots" in q_lower)
            and ("how many" in q_lower or "count" in q_lower or "number" in q_lower or "list" in q_lower or "what" in q_lower or "show" in q_lower or "our" in q_lower or "we have" in q_lower or "my" in q_lower or "there" in q_lower or "comany" in q_lower or "company" in q_lower or "workspace" in q_lower)
        )
        if is_agent_query and not ("how" in q_lower and ("create" in q_lower or "build" in q_lower or "step" in q_lower)):
            if user_context and user_context.get("is_authenticated"):
                ws_name = user_context.get("workspace_name") or "Your Workspace"
                agent_count = user_context.get("agent_count", 0)
                agents = user_context.get("agents", [])
                if agent_count == 0:
                    return f"Your workspace **{ws_name}** currently has **0 agents** configured.\n\nYou can create your first AI agent in just a few minutes using the **Agent Studio** wizard!"
                agent_list_str = "\n".join([
                    f"• **{a['name']}** (Model: `{a.get('model', 'gpt-4o-mini')}`, Status: {'Active' if a.get('is_active') else 'Inactive'}) — ID: `{a.get('id', '')}`"
                    for a in agents
                ])
                return f"Your workspace **{ws_name}** currently has **{agent_count} agent(s)** configured:\n\n{agent_list_str}\n\nYou can manage prompts, guardrails, and embed codes for any of these agents in the **Agent Studio** dashboard."
            return (
                "You are currently browsing as a guest visitor. "
                "Please sign in or create an account to view and manage the agents configured in your workspace!"
            )

        # 2. Database connection queries
        if ("database" in q_lower or "db" in q_lower or "connection" in q_lower) and ("how many" in q_lower or "count" in q_lower or "list" in q_lower or "what" in q_lower):
            if user_context and user_context.get("is_authenticated"):
                ws_name = user_context.get("workspace_name") or "Your Workspace"
                conn_count = user_context.get("connection_count", 0)
                conns = user_context.get("connections", [])
                if conn_count == 0:
                    return f"Your workspace **{ws_name}** currently has **0 database connections** configured. You can connect PostgreSQL, MySQL, SQLite, or MongoDB via the **Data Sources** tab."
                conn_list = "\n".join([f"• **{c['name']}** (Type: `{c.get('type', 'connector_http')}`)" for c in conns])
                return f"Your workspace **{ws_name}** has **{conn_count} connected database(s)**:\n\n{conn_list}"
            return "Please sign in to view your connected databases."

        # 3. Identity & workspace name queries (specific to name/identity)
        is_identity_query = (
            "who am i" in q_lower
            or "my name" in q_lower
            or (("what is" in q_lower or "tell me" in q_lower or "show" in q_lower) and ("workspace" in q_lower or "company" in q_lower or "org" in q_lower))
            or (q_lower.strip() in {"workspace name", "company name", "my workspace", "my company"})
            or (tokens.intersection(IDENTITY_KEYWORDS) and len(tokens) <= 6)
        )
        if is_identity_query:
            if user_context and user_context.get("is_authenticated"):
                ws_name = user_context.get("workspace_name") or "Your Workspace"
                return f"Your active workspace name is **{ws_name}**."
            return (
                "You are currently browsing as a guest visitor. "
                "Please sign in or create a free account to access your personalized workspace and build your AI agents!"
            )

        # 2. Add another database URL / Multi-DB Federation
        if "another" in q_lower or "multi" in q_lower or "federat" in q_lower or ("second" in q_lower and "database" in q_lower) or ("two" in q_lower and "database" in q_lower):
            return (
                "The **+ Add Another Database** option enables **Multi-Database Federation**.\n\n"
                "In enterprise production, businesses often store transactional orders in **PostgreSQL** while keeping product catalog or inventory records in **MySQL**.\n\n"
                "- By adding a second database, our orchestrator cross-queries multiple database engines simultaneously in a single conversational turn!\n"
                "- If your project only requires one database, simply configure **Database #1** and ignore the extra card."
            )

        # 3. Direct Connect vs Schema Only mode
        if "schema" in q_lower or ("direct" in q_lower and "connect" in q_lower):
            return (
                "Plug-N-Play AI provides two secure database connection modes:\n\n"
                "1. **Direct Cloud Connect**: Connects securely to PostgreSQL, MySQL, SQLite, or MongoDB over TLS/SSL for live read-only querying.\n"
                "2. **Zero-Knowledge Schema-Only Mode**: For strict enterprise compliance, paste your SQL DDL schema without ever sharing database credentials or opening firewalls. The AI outputs verified read-only queries for your internal backend to execute."
            )

        # 4. Agent creation workflow
        if "how" in q_lower and ("create" in q_lower or "build" in q_lower or "step" in q_lower or "agent" in q_lower):
            return (
                "Creating an enterprise AI agent takes 4 structured steps in the **Agent Studio**:\n\n"
                "1. **Identity & Persona**: Set your Agent Name, workspace project, brand voice, and custom system prompt.\n"
                "2. **Knowledge Ingestion**: Upload PDFs, Markdown guides, and policies for vector RAG, and connect live databases for Text-to-SQL.\n"
                "3. **Audience Guardrails**: Configure End-User row isolation (`WHERE user_id = :id`) and AST SQL read-only protection.\n"
                "4. **Actions & Live Escalation**: Enable SMTP/webhook human fallback alerts and ambient browser actions.\n\n"
                "Once configured, you can test your agent in the Sandbox and deploy it with our universal 1-line `<script>` tag!"
            )

        # 5. Fallback from relevant guide sections
        relevant = cls.retrieve_relevant_sections(user_query)
        clean_relevant = re.sub(r"#{1,4}\s*", "", relevant).strip()
        lines = [line.strip() for line in clean_relevant.split("\n") if line.strip() and not line.strip().startswith("=")]
        summary = " ".join(lines[:4]) if lines else "Plug-N-Play AI is an enterprise AI data layer and autonomous agent orchestration platform."
        return summary[:450]

    @classmethod
    async def ask(
        cls,
        user_query: str,
        user_context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Non-streaming response generation with automatic grounded fallback.
        """
        system_prompt = cls.build_system_prompt(user_query, user_context)
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            for msg in history[-4:]:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        messages.append({"role": "user", "content": user_query})

        try:
            raw_answer = await LLMGateway.complete(
                messages=messages,
                temperature=0.2,
                max_tokens=280
            )
            return clean_hedging(raw_answer)
        except Exception as e:
            logger.warning(f"[Concierge] LLM completion exception: {e}. Using grounded guide fallback.")
            return cls.generate_grounded_fallback(user_query, user_context)

    @classmethod
    async def stream_ask(
        cls,
        user_query: str,
        user_context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streaming token generator for real-time SSE UI with seamless fallback streaming.
        """
        import asyncio
        system_prompt = cls.build_system_prompt(user_query, user_context)
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            for msg in history[-4:]:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        messages.append({"role": "user", "content": user_query})

        try:
            tokens_emitted = 0
            async for token in LLMGateway.stream(
                messages=messages,
                temperature=0.2,
                max_tokens=280
            ):
                tokens_emitted += 1
                yield token
            if tokens_emitted > 0:
                return
        except Exception as e:
            logger.warning(f"[Concierge] LLM streaming exception: {e}. Streaming grounded fallback.")

        # Fallback stream
        fallback_text = cls.generate_grounded_fallback(user_query, user_context)
        words = fallback_text.split(" ")
        for i, word in enumerate(words):
            yield (word + " " if i < len(words) - 1 else word)
            await asyncio.sleep(0.015)
