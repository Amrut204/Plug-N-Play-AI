import httpx
import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Unified LLM Gateway abstracting OpenAI, Groq, Anthropic, and Mock/Local models.
    Provides uniform non-streaming completions and streaming token generators.
    """

    @classmethod
    async def complete(
        cls,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 450
    ) -> str:
        """
        Non-streaming LLM completion.
        """
        provider = provider or settings.DEFAULT_MODEL_PROVIDER
        model = model or settings.DEFAULT_MODEL_NAME

        if provider == "openai" and settings.OPENAI_API_KEY:
            return await cls._call_openai_completion(messages, model, temperature, max_tokens)
        elif (provider == "groq" or not settings.OPENAI_API_KEY) and settings.groq_api_keys:
            return await cls._call_groq_completion(messages, model, temperature, max_tokens)

        # Standalone / Deterministic Mock Response for testing/offline execution
        return cls._generate_mock_completion(messages)

    @classmethod
    async def stream(
        cls,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 450
    ) -> AsyncGenerator[str, None]:
        """
        Streaming token generator for Server-Sent Events (SSE).
        """
        provider = provider or settings.DEFAULT_MODEL_PROVIDER
        model = model or settings.DEFAULT_MODEL_NAME

        if provider == "openai" and settings.OPENAI_API_KEY:
            async for token in cls._stream_openai(messages, model, temperature, max_tokens):
                yield token
            return
        elif (provider == "groq" or not settings.OPENAI_API_KEY) and settings.groq_api_keys:
            async for token in cls._stream_groq(messages, model, temperature, max_tokens):
                yield token
            return

        # Fallback stream for local test/offline mode
        full_text = cls._generate_mock_completion(messages)
        import asyncio
        words = full_text.split(" ")
        for i, word in enumerate(words):
            yield (word + " " if i < len(words) - 1 else word)
            await asyncio.sleep(0.01)

    @classmethod
    async def _call_openai_completion(
        cls, messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: int
    ) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    @classmethod
    async def _stream_openai(
        cls, messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                    except Exception:
                        continue

    _current_groq_key_idx: int = 0

    @classmethod
    def get_active_groq_keys(cls) -> List[str]:
        """Returns all configured non-empty Groq API keys in priority order."""
        return settings.groq_api_keys

    @classmethod
    def get_current_groq_key(cls) -> Optional[str]:
        """Returns the currently active Groq API key from the pool."""
        keys = cls.get_active_groq_keys()
        if not keys:
            return None
        return keys[cls._current_groq_key_idx % len(keys)]

    @classmethod
    def rotate_groq_key(cls, reason: str = "limit_reached") -> str:
        """
        Rotates to the next configured Groq API key in round-robin order when rate limit or quota is reached.
        """
        keys = cls.get_active_groq_keys()
        if not keys:
            return ""
        prev_idx = cls._current_groq_key_idx % len(keys)
        cls._current_groq_key_idx = (cls._current_groq_key_idx + 1) % len(keys)
        new_key = keys[cls._current_groq_key_idx]
        old_masked = keys[prev_idx][:10] + "..." if len(keys[prev_idx]) > 10 else "***"
        new_masked = new_key[:10] + "..." if len(new_key) > 10 else "***"
        logger.warning(
            f"Groq API key rotated ({reason}): switched from key #{prev_idx + 1} ({old_masked}) "
            f"to key #{cls._current_groq_key_idx + 1} ({new_masked})"
        )
        return new_key

    @classmethod
    async def _call_groq_completion(
        cls, messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: int
    ) -> str:
        import asyncio
        url = "https://api.groq.com/openai/v1/chat/completions"
        groq_model = model if ("qwen" in model.lower() or "llama" in model.lower() or "gpt-oss" in model.lower()) else settings.DEFAULT_MODEL_NAME
        keys = cls.get_active_groq_keys()
        if not keys:
            raise RuntimeError("No Groq API keys configured in .env (GROQ_API_KEY, GROQ_API_KEY_1, GROQ_API_KEY_2).")

        current_max_tokens = max_tokens
        max_key_attempts = len(keys)
        last_error = None

        async with httpx.AsyncClient(timeout=35.0) as client:
            for key_attempt in range(max_key_attempts):
                active_key = cls.get_current_groq_key()
                headers = {
                    "Authorization": f"Bearer {active_key}",
                    "Content-Type": "application/json"
                }

                for attempt in range(2):
                    trimmed_messages = cls._trim_messages_for_budget(messages, current_max_tokens, budget=7500)
                    payload = {
                        "model": groq_model,
                        "messages": trimmed_messages,
                        "temperature": temperature,
                        "max_tokens": current_max_tokens
                    }
                    try:
                        resp = await client.post(url, headers=headers, json=payload)
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Groq connection exception on key #{cls._current_groq_key_idx + 1}: {e}")
                        cls.rotate_groq_key(reason="connection_exception")
                        break

                    if resp.status_code == 413 and attempt < 1:
                        current_max_tokens = max(30, current_max_tokens // 2)
                        logger.warning(f"Groq 413: reducing max_tokens to {current_max_tokens}")
                        await asyncio.sleep(0.5)
                        continue

                    # If rate limited (429) or quota reached / auth failure (401/403), rotate to next key
                    if resp.status_code in (429, 401, 403):
                        logger.warning(
                            f"Groq HTTP {resp.status_code} limit reached on key #{cls._current_groq_key_idx + 1}. "
                            f"Switching to failover Groq key..."
                        )
                        last_error = RuntimeError(f"Groq error ({resp.status_code}): {resp.text}")
                        cls.rotate_groq_key(reason=f"HTTP_{resp.status_code}")
                        break

                    if resp.status_code != 200:
                        last_error = RuntimeError(f"Groq error ({resp.status_code}): {resp.text}")
                        break

                    data = resp.json()
                    return data["choices"][0]["message"]["content"]

        if last_error:
            raise last_error
        raise RuntimeError("Groq completion failed across all configured API keys.")

    @classmethod
    def _trim_messages_for_budget(cls, messages: List[Dict[str, str]], max_tokens: int, budget: int = 7500) -> List[Dict[str, str]]:
        """
        Estimate total token cost (prompt + max_tokens) and truncate message content
        if it exceeds the budget. Groq counts TPM as prompt_tokens + max_tokens.
        """
        total_chars = sum(len(m.get("content", "")) for m in messages)
        estimated_prompt_tokens = total_chars // 4  # ~4 chars per token
        total_estimated = estimated_prompt_tokens + max_tokens
        
        if total_estimated <= budget:
            return messages
        
        # Need to cut (total_estimated - budget) tokens from prompt ≈ *4 chars
        chars_to_cut = (total_estimated - budget) * 4 + 200  # extra margin
        logger.warning(f"Trimming {chars_to_cut} chars from prompt (est {total_estimated} tokens vs {budget} budget)")
        
        trimmed = []
        for m in messages:
            content = m.get("content", "")
            if len(content) > 500 and chars_to_cut > 0:
                cut = min(chars_to_cut, len(content) - 200)
                content = content[:len(content) - cut] + "\n[truncated]"
                chars_to_cut -= cut
            trimmed.append({"role": m["role"], "content": content})
        return trimmed

    @classmethod
    async def _stream_groq(
        cls, messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        url = "https://api.groq.com/openai/v1/chat/completions"
        groq_model = model if ("qwen" in model.lower() or "llama" in model.lower() or "gpt-oss" in model.lower()) else settings.DEFAULT_MODEL_NAME
        keys = cls.get_active_groq_keys()
        if not keys:
            raise RuntimeError("No Groq API keys configured in .env (GROQ_API_KEY, GROQ_API_KEY_1, GROQ_API_KEY_2).")

        for key_attempt in range(len(keys)):
            active_key = cls.get_current_groq_key()
            headers = {
                "Authorization": f"Bearer {active_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": groq_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    async with client.stream("POST", url, headers=headers, json=payload) as response:
                        if response.status_code in (429, 401, 403) and key_attempt < len(keys) - 1:
                            logger.warning(
                                f"Groq streaming HTTP {response.status_code} limit on key #{cls._current_groq_key_idx + 1}. "
                                f"Switching to failover key..."
                            )
                            cls.rotate_groq_key(reason=f"stream_HTTP_{response.status_code}")
                            continue

                        if response.status_code != 200:
                            err_body = await response.aread()
                            raise RuntimeError(f"Groq streaming error ({response.status_code}): {err_body.decode('utf-8')}")

                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk["choices"][0]["delta"]
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
                            except Exception:
                                continue
                        return
                except Exception as e:
                    if key_attempt < len(keys) - 1:
                        logger.warning(f"Groq streaming exception on key #{cls._current_groq_key_idx + 1} ({e}). Switching to failover key...")
                        cls.rotate_groq_key(reason="stream_exception")
                        continue
                    raise e

    @classmethod
    def _generate_mock_completion(cls, messages: List[Dict[str, str]]) -> str:
        """
        Intelligent mock completion for offline testing and zero-key environments.
        Inspects the last user message and generates appropriate SQL or reasoning.
        """
        user_msg = ""
        system_msg = ""
        for m in messages:
            if m.get("role") == "system":
                system_msg = m.get("content", "")
            if m.get("role") == "user":
                user_msg = m.get("content", "")

        q_lower = user_msg.lower()

        # Text-to-SQL prompt detection
        if "available schema" in system_msg.lower() or "text-to-sql" in system_msg.lower():
            if "attendance" in q_lower:
                return "```sql\nSELECT subject, attendance_percentage FROM attendance WHERE student_id = :auth_user_id LIMIT 10;\n```"
            elif "marks" in q_lower or "score" in q_lower or "grade" in q_lower:
                return "```sql\nSELECT subject, score, max_score, grade FROM marks WHERE student_id = :auth_user_id LIMIT 10;\n```"
            elif "fees" in q_lower or "due" in q_lower:
                return "```sql\nSELECT total_fees, amount_paid, pending_due FROM fees WHERE student_id = :auth_user_id LIMIT 1;\n```"
            return "```sql\nSELECT * FROM students WHERE student_id = :auth_user_id LIMIT 1;\n```"

        # Intent classification detection
        if "classify the intent" in system_msg.lower():
            if any(w in q_lower for w in ["can i sit", "eligible for", "eligibility", "qualify", "allowed to"]):
                return '{"intent": "HYBRID", "reason": "Requires both student operational metrics and institutional policy regulations."}'
            elif any(w in q_lower for w in ["policy", "rule", "regulations", "guideline", "handbook", "criteria", "deadline", "how to"]):
                return '{"intent": "RAG", "reason": "Requires retrieving unstructured policy documentation."}'
            elif any(w in q_lower for w in ["attendance", "marks", "grade", "score", "fee", "how many", "cgpa"]):
                return '{"intent": "SQL", "reason": "Requires querying structured operational records."}'
            return '{"intent": "DIRECT", "reason": "Direct general conversation."}'

        # Hybrid / Synthesis Mock Responses (Confident, BLUF, Zero Hedging)
        if "attendance" in q_lower or "exam" in q_lower or "sit" in q_lower:
            return (
                "You currently do not meet the 75% attendance requirement to sit for the Database Systems final examination.\n\n"
                "- **Your Recorded Attendance**: 71.1%\n"
                "- **Institutional Minimum**: 75.0% (Examination Policy, Article 4)\n"
                "- **Attendance Shortfall**: 3.9%\n\n"
                "**Actionable Next Step**: Because your attendance is between 65% and 74%, you qualify to apply for **Medical Condonation** with the Academic Registrar before the semester cutoff."
            )

        if "return" in q_lower or "refund" in q_lower:
            return (
                "Our return window is **30 days** from the date of delivery.\n\n"
                "- Items must be in original condition, unworn, and with tags attached.\n"
                "- Refunds will be credited to your original payment method within 5–7 business days.\n\n"
                "**To initiate a return**: Visit your Order History page and click **Request Return** next to your order."
            )

        if "fee" in q_lower or "due" in q_lower:
            return (
                "Your pending tuition balance for the current semester is **₹24,500**.\n\n"
                "- **Total Semester Fee**: ₹65,000\n"
                "- **Amount Paid**: ₹40,500\n"
                "- **Due Date**: November 15, 2026\n\n"
                "**Payment Options**: You can pay online via the Student Finance Portal or at the Accounts Office."
            )

        return (
            "I am your dedicated enterprise AI Assistant. "
            "How can I assist you with your records, account details, or organizational policies today?"
        )
