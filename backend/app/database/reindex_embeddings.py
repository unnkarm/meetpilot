"""Re-embed existing source text when the configured multilingual model changes.

Run after the model is installed and the schema migration has completed:
    python -m app.database.reindex_embeddings
The script commits one batch at a time and can be safely resumed.
"""

from sqlalchemy import or_

from app.core.app_config import APP_CONFIG
from app.database.session import SessionLocal
from app.models.document import DocumentChunk
from app.models.transcript import TranscriptSegment
from app.services.embedding_provider import embed_texts


def reindex_embeddings() -> dict[str, int]:
    counts: dict[str, int] = {}
    batch_size = APP_CONFIG.embeddings.batch_size
    model_name = APP_CONFIG.embeddings.model
    with SessionLocal() as db:
        for model in (TranscriptSegment, DocumentChunk):
            count = 0
            while True:
                rows = (
                    db.query(model)
                    .filter(or_(model.embedding_model.is_(None), model.embedding_model != model_name))
                    .order_by(model.id)
                    .limit(batch_size)
                    .all()
                )
                if not rows:
                    break
                vectors = embed_texts([row.text for row in rows], task_type="RETRIEVAL_DOCUMENT")
                if len(vectors) != len(rows):
                    raise RuntimeError("Embedding provider returned the wrong number of vectors")
                for row, vector in zip(rows, vectors):
                    row.embedding = vector
                    row.embedding_model = model_name
                db.commit()
                count += len(rows)
            counts[model.__tablename__] = count
    return counts


if __name__ == "__main__":
    print(reindex_embeddings())
