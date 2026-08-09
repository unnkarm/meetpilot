import logging
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.document import KnowledgeDocument
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.schemas.document import (
    DocumentOut,
    DocumentUploadResponse,
    KnowledgeChatRequest,
    KnowledgeChatResponse,
    KnowledgeCitation,
)
from app.services.document_service import (
    SUPPORTED_EXTENSIONS,
    get_file_type_from_filename,
    process_and_index_document,
)
from app.services.knowledge_chat_service import answer_workspace_knowledge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["knowledge-documents"])


def _verify_workspace_membership(workspace_id: uuid.UUID, user: User, db: Session) -> WorkspaceMember:
    """Enforces strict server-side workspace isolation."""
    member = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id)
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this workspace.",
        )
    return member


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    workspace_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Uploads a company knowledge document (PDF, DOCX, TXT, MD), extracts text, generates embeddings, and indexes into pgvector."""
    _verify_workspace_membership(workspace_id, current_user, db)

    filename = file.filename or "document.txt"
    _, ext = os.path.splitext(filename)
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats are: PDF (.pdf), Word (.docx), Plain Text (.txt), and Markdown (.md).",
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > 30 * 1024 * 1024:  # 30MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 30MB limit for knowledge documents.",
        )

    file_type = get_file_type_from_filename(filename)
    title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").strip()

    # Create document record
    doc = KnowledgeDocument(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        title=title or filename,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        status="uploading",
        created_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process, chunk, embed, and store in pgvector
    processed_doc = process_and_index_document(db, doc, file_bytes)

    return DocumentUploadResponse(
        document=DocumentOut.model_validate(processed_doc),
        message=f"Document '{filename}' indexed successfully into workspace knowledge base ({processed_doc.chunk_count} chunks).",
    )


@router.get("/documents", response_model=List[DocumentOut])
def list_workspace_documents(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all indexed knowledge documents for a workspace."""
    _verify_workspace_membership(workspace_id, current_user, db)

    docs = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.workspace_id == workspace_id)
        .order_by(KnowledgeDocument.created_at.desc())
        .all()
    )
    return [DocumentOut.model_validate(d) for d in docs]


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a knowledge document and its associated vector chunks."""
    doc = db.get(KnowledgeDocument, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    _verify_workspace_membership(doc.workspace_id, current_user, db)

    db.delete(doc)
    db.commit()
    return {"success": True, "message": f"Document '{doc.filename}' deleted successfully."}


@router.post("/knowledge/chat", response_model=KnowledgeChatResponse)
def chat_with_workspace_knowledge(
    payload: KnowledgeChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grounded multi-source RAG across company documents and meeting transcripts in the active workspace."""
    _verify_workspace_membership(payload.workspace_id, current_user, db)

    answer, citations_data = answer_workspace_knowledge(db, payload.workspace_id, payload.question)

    citations = [KnowledgeCitation(**c) for c in citations_data]
    return KnowledgeChatResponse(answer=answer, citations=citations)
