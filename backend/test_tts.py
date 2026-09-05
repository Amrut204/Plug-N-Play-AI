import asyncio
import edge_tts
import os

scenes = [
    ("scene5", "Next, we configure our structured data engine, supporting live enterprise databases including PostgreSQL, MySQL, SQLite, and MongoDB. Here we introduce two major architectural innovations. First is Multi-Database Federation: by simply clicking Add Another Database, our orchestrator connects multiple disparate databases to a single agent. For example, customer orders can reside in PostgreSQL while product catalog records live in MySQL, and the agent executes federated cross-database lookups in a single conversational turn! Second is our Zero-Knowledge Schema-Only Mode: enterprises with stringent compliance requirements can simply paste their SQL DDL schema. The agent synthesizes verified queries without our platform ever needing live database credentials or firewall access."),
    ("scene6", "In Step 3, we establish Audience Guardrails and row-level access control. Different user tiers require different data visibility. In End-User Mode, strict row isolation automatically appends WHERE user_id equals current user to all SQL queries, mathematically preventing users from viewing anyone else's private orders or account data. Staff and Executive presets allow broader aggregate lookups while masking personally identifiable information. Furthermore, every generated query passes through our Abstract Syntax Tree Security Gate, which inspects query syntax and instantly blocks any destructive commands such as DROP, DELETE, UPDATE, or INSERT before execution."),
    ("scene7", "In Step 4, we configure proactive Actions and Live Human Escalation. When an inquiry requires human intervention or encounters complex edge cases, the agent instantly triggers automated escalation alerts through SMTP email notifications or webhook alerts. In addition, through our Ambient Browser Relay framework, agents can propose verified client-side actions, such as applying promotional vouchers or navigating to checkout, returning control smoothly to the user."),
    ("scene8", "Before deploying to production, developers can thoroughly test their agent in the live interactive Sandbox Console. Here, we can observe dual-engine retrieval in real time. When asking policy questions, the agent retrieves grounded vector snippets. When querying transactional data, such as checking order status or inventory levels, it translates natural language into read-only SQL, executing queries securely and displaying formatted data cards with sub-second streaming inference powered by Groq's high-speed Llama-3."),
    ("scene9", "Once validated, deploying the agent into any codebase requires zero complex refactoring or backend rewrites. Developers simply copy our universal one-line script snippet and paste it right before the closing body tag of their web application. That is all it takes! The widget initializes automatically, establishes secure session tokens, and is fully compatible with React, Next.js, WordPress, Shopify, Angular, Vue, or pure HTML with zero npm dependencies."),
    ("scene10", "Finally, our Workspace Dashboard provides full operational telemetry for your agent fleet. Engineering teams can monitor query latencies, token consumption, and security shield events across all active deployments, backed by strict cryptographic multi-tenant isolation. Plug-N-Play AI bridges the gap between static documents and live transactional databases with zero friction and enterprise-grade security. Thank you for considering our project for the Razorpay AI Builder 2026 Internship!")
]

async def gen_all():
    voice = "en-US-AndrewMultilingualNeural"
    for name, text in scenes:
        print(f"Generating {name}...")
        for attempt in range(3):
            try:
                comm = edge_tts.Communicate(text, voice, rate="-2%")
                await asyncio.wait_for(comm.save(f"{name}.mp3"), timeout=20)
                sz = os.path.getsize(f"{name}.mp3")
                print(f"  {name} saved! Size: {sz} bytes")
                break
            except Exception as e:
                print(f"  Attempt {attempt+1} failed: {e}")
                await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(gen_all())
