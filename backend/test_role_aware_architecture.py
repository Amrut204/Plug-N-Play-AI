import asyncio
import sys
import unittest
from unittest.mock import patch, AsyncMock
from app.services.guardrails.compiler import AIGuardrailCompiler
from app.services.hybrid.orchestrator import QueryOrchestrator
from app.schemas.rag import DocumentIngestItem
from app.api.v1.quickstart import QuickstartSetupRequest


class TestRoleAwareArchitecture(unittest.TestCase):

    def test_gate1_universal_and_role_scoped_bans(self):
        """Test Gate 1 fast intent evaluation with role scoping."""
        config = {
            "banned_intents": ["jailbreak_system", "bypass_attendance"],
            "restricted_columns": ["password_hash", "faculty_salary"],
            "refusal_message": "Action restricted.",
            "role_scoped_bans": {
                "student": ["view_all_student_records", "salary_lookup"],
                "customer": ["wholesale_catalog"]
            }
        }

        # 1. Universal bans are blocked for EVERY role
        blocked, msg = AIGuardrailCompiler.evaluate_query("Please bypass attendance rules", config, user_role="student")
        self.assertTrue(blocked)
        blocked, msg = AIGuardrailCompiler.evaluate_query("Please bypass attendance rules", config, user_role="faculty")
        self.assertTrue(blocked)

        # 2. Restricted column queries are blocked for all roles
        blocked, msg = AIGuardrailCompiler.evaluate_query("What is the faculty salary?", config, user_role="student")
        self.assertTrue(blocked)

        # 3. Role-scoped ban blocked for student
        blocked, msg = AIGuardrailCompiler.evaluate_query("Show me view all student records", config, user_role="student")
        self.assertTrue(blocked)

        # 4. Same query is NOT blocked for faculty (not in faculty's banned list)
        blocked, msg = AIGuardrailCompiler.evaluate_query("Show me view all student records", config, user_role="faculty")
        self.assertFalse(blocked)

        # 5. Customer role-scoped ban
        blocked, msg = AIGuardrailCompiler.evaluate_query("Send me wholesale catalog", config, user_role="customer")
        self.assertTrue(blocked)
        blocked, msg = AIGuardrailCompiler.evaluate_query("Send me wholesale catalog", config, user_role="admin")
        self.assertFalse(blocked)

    def test_quickstart_schema_document_roles(self):
        """Test QuickstartSetupRequest handles document_allowed_roles properly."""
        req = QuickstartSetupRequest(
            project_name="College ERP",
            service_type="hybrid",
            document_title="Faculty Salary & Grant Guide",
            document_content="Salary scales are as follows...",
            document_allowed_roles=["faculty", "admin"]
        )
        self.assertEqual(req.document_allowed_roles, ["faculty", "admin"])

        req_default = QuickstartSetupRequest(
            project_name="Public Store",
            service_type="rag"
        )
        self.assertIsNone(req_default.document_allowed_roles)

    @patch("app.services.hybrid.orchestrator.LLMGateway.complete", new_callable=AsyncMock)
    def test_synthesize_response_role_prompt_injection(self, mock_complete):
        """Test that _synthesize_response injects user role and role instructions into system prompt."""
        mock_complete.return_value = "Here is your attendance record."

        guardrail_config = {
            "refusal_instructions": ["Do not share peer records."],
            "role_instructions": {
                "student": "Be encouraging, empathetic, and focus strictly on remedial next steps.",
                "faculty": "Be analytical and detail-oriented. Include administrative procedure links."
            }
        }

        async def run_test():
            # Test student role synthesis
            await QueryOrchestrator._synthesize_response(
                user_query="What is my current attendance status?",
                intent="RAG",
                sql_rows=[{"attendance_pct": 74.5}],
                rag_chunks=[{"content": "Attendance policy: Minimum 75% required.", "metadata": {"title": "Policy"}}],
                user_role="student",
                user_id="std_1042",
                guardrail_config=guardrail_config,
                agent_name="CampusBot",
                workspace_name="National University"
            )

            # Check messages sent to LLMGateway
            self.assertTrue(mock_complete.called)
            call_args = mock_complete.call_args[0][0]  # messages array
            sys_msg = call_args[0]["content"]

            # Assertions on prompt content
            self.assertIn("User Role: **student**", sys_msg)
            self.assertIn("User Identity / Auth ID: std_1042", sys_msg)
            self.assertIn("Be encouraging, empathetic", sys_msg)
            self.assertIn("National University", sys_msg)
            self.assertIn("CampusBot", sys_msg)

            # Test faculty role synthesis
            mock_complete.reset_mock()
            await QueryOrchestrator._synthesize_response(
                user_query="What are the grade submission deadlines?",
                intent="RAG",
                sql_rows=None,
                rag_chunks=[{"content": "Faculty deadline: Dec 15th.", "metadata": {"title": "Calendar"}}],
                user_role="faculty",
                user_id="prof_99",
                guardrail_config=guardrail_config,
                agent_name="CampusBot",
                workspace_name="National University"
            )

            call_args = mock_complete.call_args[0][0]
            sys_msg = call_args[0]["content"]
            self.assertIn("User Role: **faculty**", sys_msg)
            self.assertIn("User Identity / Auth ID: prof_99", sys_msg)
            self.assertIn("Be analytical and detail-oriented", sys_msg)

        asyncio.run(run_test())

    @patch("app.services.rag.retriever.EmbeddingService.cosine_similarity", return_value=0.85)
    @patch("app.services.rag.retriever.EmbeddingService.get_embedding", new_callable=AsyncMock)
    def test_rag_retriever_role_filtering(self, mock_get_embedding, mock_similarity):
        """Test that RAGRetriever filters chunks based on allowed_roles in doc_metadata."""
        from app.services.rag.retriever import RAGRetriever
        from app.models.rag import RAGChunk

        mock_get_embedding.return_value = [0.1] * 384

        chunk_public = RAGChunk(
            id="chunk-pub",
            tenant_id="ten-1",
            rag_source_id="src-1",
            content="Campus general rules.",
            doc_metadata={"title": "General", "allowed_roles": ["student", "faculty", "admin"]},
            embedding=[0.1] * 384
        )

        chunk_faculty_only = RAGChunk(
            id="chunk-fac",
            tenant_id="ten-1",
            rag_source_id="src-1",
            content="Faculty performance review criteria and confidential salary grades.",
            doc_metadata={"title": "Faculty Salary", "allowed_roles": ["faculty", "admin"]},
            embedding=[0.1] * 384
        )

        # Mock DB session returning both chunks
        from unittest.mock import MagicMock
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [chunk_public, chunk_faculty_only]
        mock_db.execute.return_value = mock_result

        async def run_test():
            # 1. Retrieve as student: faculty-only chunk should be filtered out
            student_chunks = await RAGRetriever.retrieve_relevant_chunks(
                db=mock_db,
                tenant_id="ten-1",
                query="What are the rules and salaries?",
                user_role="student"
            )
            student_chunk_ids = [c["chunk_id"] for c in student_chunks]
            self.assertIn("chunk-pub", student_chunk_ids)
            self.assertNotIn("chunk-fac", student_chunk_ids)

            # 2. Retrieve as faculty: both chunks should be visible
            faculty_chunks = await RAGRetriever.retrieve_relevant_chunks(
                db=mock_db,
                tenant_id="ten-1",
                query="What are the rules and salaries?",
                user_role="faculty"
            )
            faculty_chunk_ids = [c["chunk_id"] for c in faculty_chunks]
            self.assertIn("chunk-pub", faculty_chunk_ids)
            self.assertIn("chunk-fac", faculty_chunk_ids)

            # 3. Retrieve as admin: both chunks should be visible
            admin_chunks = await RAGRetriever.retrieve_relevant_chunks(
                db=mock_db,
                tenant_id="ten-1",
                query="What are the rules and salaries?",
                user_role="admin"
            )
            admin_chunk_ids = [c["chunk_id"] for c in admin_chunks]
            self.assertIn("chunk-pub", admin_chunk_ids)
            self.assertIn("chunk-fac", admin_chunk_ids)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
