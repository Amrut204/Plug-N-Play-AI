import math
import hashlib
import re
import logging
from typing import List, Optional, Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from fastembed import TextEmbedding
    _fastembed_available = True
except ImportError:
    _fastembed_available = False


class EmbeddingService:
    """
    Computes vector embeddings for text chunks and queries.
    Primary: FastEmbed (BAAI/bge-small-en-v1.5, 384 dimensions) for local neural vectors.
    Fallback: OpenAI text-embedding-3-small or deterministic normalized vector.
    """

    DIMENSION: int = 384
    _model: Optional[Any] = None

    @classmethod
    def _get_fastembed_model(cls):
        if cls._model is None and _fastembed_available:
            try:
                cls._model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            except Exception as e:
                logger.warning(f"FastEmbed initialization error: {e}")
                cls._model = None
        return cls._model

    @classmethod
    async def get_embedding(cls, text: str) -> List[float]:
        """
        Returns a 384-dimensional normalized vector embedding for the input text.
        """
        # 1. Primary: FastEmbed local neural ONNX model
        fastembed_model = cls._get_fastembed_model()
        if fastembed_model is not None:
            try:
                embeddings = list(fastembed_model.embed([text]))
                if embeddings:
                    return [float(v) for v in embeddings[0]]
            except Exception as e:
                logger.warning(f"FastEmbed generation failed: {e}")

        # 2. Fallback: OpenAI if key is present
        if settings.OPENAI_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "input": text,
                            "model": "text-embedding-3-small",
                            "dimensions": cls.DIMENSION
                        }
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["data"][0]["embedding"]
            except Exception:
                pass

        # 3. Fallback: Deterministic normalized embedding
        return cls._compute_deterministic_embedding(text)

    @classmethod
    def _compute_deterministic_embedding(cls, text: str) -> List[float]:
        """
        Generates a 384-dimensional L2-normalized pseudo-semantic vector
        derived from tokens, character n-grams, and term hashing.
        """
        vector = [0.0] * cls.DIMENSION
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return vector

        for token in tokens:
            h1 = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % cls.DIMENSION
            h2 = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % cls.DIMENSION
            vector[h1] += 1.0
            vector[h2] += 0.5

            for i in range(len(token) - 2):
                shingle = token[i:i+3]
                hs = int(hashlib.sha1(shingle.encode("utf-8")).hexdigest(), 16) % cls.DIMENSION
                vector[hs] += 0.25

        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]

        return vector

    @classmethod
    def cosine_similarity(cls, vec_a: List[float], vec_b: List[float]) -> float:
        """Calculate cosine similarity between two normalized vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        return sum(a * b for a, b in zip(vec_a, vec_b))
