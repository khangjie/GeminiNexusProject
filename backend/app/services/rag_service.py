"""
RAG Service — Qdrant vector database for company purchase history retrieval.
Used by the Proposal Optimization Agent to search past purchases.

Qdrant setup:
  - Local:  run `docker run -p 6333:6333 qdrant/qdrant`
  - Cloud:  set QDRANT_URL + QDRANT_API_KEY in .env

Collection schema (auto-created on first upsert):
  Collection name : <company_id>_receipts
  Vector size     : 768  (text-embedding-004)
  Payload fields  : receipt_id, vendor, price, date, item_name
"""
import logging
import uuid
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

VECTOR_SIZE = 768
DISTANCE = "Cosine"


def _get_qdrant_client():
    """Return a QdrantClient instance, or None if qdrant-client is not installed."""
    if not settings.QDRANT_URL:
        return None
    try:
        from qdrant_client import QdrantClient
        kwargs: dict = {"url": settings.QDRANT_URL}
        if settings.QDRANT_API_KEY:
            kwargs["api_key"] = settings.QDRANT_API_KEY
        return QdrantClient(**kwargs)
    except ImportError:
        logger.warning("qdrant-client not installed. Run: pip install qdrant-client")
        return None
    except Exception as exc:
        logger.error("Qdrant connection error: %s", exc)
        return None


def _collection_name(company_id: str) -> str:
    # Qdrant collection names cannot contain hyphens — replace with underscores
    return f"{company_id.replace('-', '_')}_receipts"


def _ensure_collection(client, collection: str) -> None:
    """Create the Qdrant collection if it does not already exist."""
    from qdrant_client.models import Distance, VectorParams
    existing = [c.name for c in client.get_collections().collections]
    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", collection)


async def _get_embedding(text: str) -> list[float]:
    """
    Generate a text embedding.
    Tries google-generativeai embedding first, falls back to a zero vector.
    """
    try:
        import google.generativeai as genai
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="RETRIEVAL_DOCUMENT",
        )
        return result["embedding"]
    except Exception as exc:
        logger.warning("Embedding generation failed (%s), using zero vector.", exc)
        return [0.0] * VECTOR_SIZE


async def search_purchase_history(
    item_name: str,
    company_id: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Search company purchase history using Qdrant vector similarity.
    Returns a list of similar past purchase records.
    """
    client = _get_qdrant_client()
    if not client:
        return _mock_history_search(item_name)

    collection = _collection_name(company_id)

    try:
        _ensure_collection(client, collection)
        embedding = await _get_embedding(item_name)

        hits = client.search(
            collection_name=collection,
            query_vector=embedding,
            limit=top_k,
            with_payload=True,
        )

        return [
            {
                "vendor": hit.payload.get("vendor", "Unknown"),
                "price": hit.payload.get("price"),
                "date": hit.payload.get("date"),
                "item_name": hit.payload.get("item_name", item_name),
                "score": hit.score,
                "source": "company_history",
            }
            for hit in hits
        ]
    except Exception as exc:
        logger.error("Qdrant search error: %s", exc)
        return _mock_history_search(item_name)


async def upsert_receipt_embedding(
    receipt_id: str,
    text: str,
    company_id: str = "",
    vendor: str = "",
    price: float | None = None,
    date: str = "",
    item_name: str = "",
) -> None:
    """
    Upsert a receipt embedding into the company's Qdrant collection.
    Called after a receipt is processed and saved.
    """
    client = _get_qdrant_client()
    if not client or not company_id:
        return

    collection = _collection_name(company_id)

    try:
        from qdrant_client.models import PointStruct

        _ensure_collection(client, collection)
        embedding = await _get_embedding(text)

        point = PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, receipt_id)),
            vector=embedding,
            payload={
                "receipt_id": receipt_id,
                "vendor": vendor,
                "price": price,
                "date": date,
                "item_name": item_name,
                "company_id": company_id,
            },
        )
        client.upsert(collection_name=collection, points=[point])
        logger.info("Upserted receipt %s into Qdrant collection %s", receipt_id, collection)
    except Exception as exc:
        logger.error("Qdrant upsert error: %s", exc)


def _mock_history_search(item_name: str) -> list[dict[str, Any]]:
    return [
        {"vendor": "Historical Vendor A", "price": 85.00, "date": "2025-11-15", "item_name": item_name, "score": 0.91, "source": "company_history"},
        {"vendor": "Historical Vendor B", "price": 92.50, "date": "2025-10-03", "item_name": item_name, "score": 0.84, "source": "company_history"},
    ]
