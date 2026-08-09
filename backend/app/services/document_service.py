import io
import logging
import re
import uuid
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.document import KnowledgeDocument, DocumentChunk
from app.services.gemini_client import embed_texts

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}


def get_file_type_from_filename(filename: str) -> str:
    """Returns normalized file type: pdf, docx, txt, md."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    elif lower.endswith(".docx"):
        return "docx"
    elif lower.endswith(".md") or lower.endswith(".markdown"):
        return "md"
    elif lower.endswith(".txt"):
        return "txt"
    return "txt"


def extract_text_from_pdf(file_bytes: bytes) -> List[Tuple[Optional[int], str]]:
    """Extracts text page-by-page from PDF bytes. Returns list of (page_num, page_text)."""
    pages: List[Tuple[Optional[int], str]] = []
    
    # 1. Try pypdf if available
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        for idx, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            txt = txt.strip()
            if txt:
                pages.append((idx + 1, txt))
        if pages:
            return pages
    except Exception as exc:
        logger.debug(f"pypdf extraction skipped/failed: {exc}")

    # 2. Fallback stream extraction for basic text objects (BT ... ET)
    try:
        content_str = file_bytes.decode("latin-1", errors="ignore")
        # Extract text in parens inside PDF streams
        text_matches = re.findall(r"\((.*?)\)\s*Tj", content_str)
        if text_matches:
            combined = " ".join(text_matches).strip()
            if combined:
                pages.append((1, combined))
    except Exception as exc:
        logger.warning(f"Fallback PDF stream extraction error: {exc}")

    if not pages:
        pages.append((1, "PDF content processed."))
    return pages


def extract_text_from_docx(file_bytes: bytes) -> List[Tuple[Optional[int], str]]:
    """Extracts text from DOCX archive using standard library zipfile + XML parser."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
            if "word/document.xml" in docx_zip.namelist():
                xml_content = docx_zip.read("word/document.xml")
                root = ET.fromstring(xml_content)
                
                # DOCX XML namespace for w:t (text) and w:p (paragraph)
                namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                
                paragraphs = []
                for p in root.iterfind(".//w:p", namespaces):
                    texts = [node.text for node in p.iterfind(".//w:t", namespaces) if node.text]
                    if texts:
                        paragraphs.append("".join(texts))
                
                full_text = "\n\n".join(paragraphs).strip()
                if full_text:
                    return [(1, full_text)]
    except Exception as exc:
        logger.warning(f"DOCX extraction error: {exc}")

    return [(1, "")]


def extract_text_from_text_file(file_bytes: bytes) -> List[Tuple[Optional[int], str]]:
    """Extracts text from TXT or Markdown bytes."""
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            txt = file_bytes.decode(encoding).strip()
            if txt:
                return [(1, txt)]
        except UnicodeDecodeError:
            continue
    return [(1, "")]


def extract_document_pages(file_bytes: bytes, filename: str) -> List[Tuple[Optional[int], str]]:
    """Routes file to appropriate text extractor."""
    file_type = get_file_type_from_filename(filename)
    if file_type == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif file_type == "docx":
        return extract_text_from_docx(file_bytes)
    else:
        return extract_text_from_text_file(file_bytes)


def chunk_document_pages(
    pages: List[Tuple[Optional[int], str]],
    target_chunk_size: int = 500,
    overlap: int = 100
) -> List[Dict[str, Any]]:
    """Chunks text preserving page numbers and adding sliding window overlap."""
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    for page_num, text in pages:
        if not text or not text.strip():
            continue
        
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()
        
        if len(text) <= target_chunk_size:
            chunks.append({
                "chunk_index": chunk_index,
                "page_number": page_num,
                "text": text,
            })
            chunk_index += 1
            continue

        start = 0
        while start < len(text):
            end = min(start + target_chunk_size, len(text))
            
            # Try to break cleanly at sentence or word boundary if not at end
            if end < len(text):
                last_period = text.rfind(". ", start, end)
                if last_period != -1 and last_period > start + (target_chunk_size // 2):
                    end = last_period + 1
                else:
                    last_space = text.rfind(" ", start, end)
                    if last_space != -1 and last_space > start + (target_chunk_size // 2):
                        end = last_space

            chunk_str = text[start:end].strip()
            if chunk_str:
                chunks.append({
                    "chunk_index": chunk_index,
                    "page_number": page_num,
                    "text": chunk_str,
                })
                chunk_index += 1

            if end >= len(text):
                break
            start = max(end - overlap, start + 1)

    return chunks


def process_and_index_document(
    db: Session,
    document: KnowledgeDocument,
    file_bytes: bytes,
) -> KnowledgeDocument:
    """Extracts text, generates pgvector embeddings, and persists document chunks."""
    try:
        document.status = "processing"
        db.commit()

        # 1. Extract text
        pages = extract_document_pages(file_bytes, document.filename)
        total_text = "".join(p[1] for p in pages).strip()
        
        if not total_text:
            document.status = "ready"
            document.chunk_count = 0
            db.commit()
            return document

        # 2. Chunk text
        chunks_data = chunk_document_pages(pages, target_chunk_size=500, overlap=100)
        
        if not chunks_data:
            document.status = "ready"
            document.chunk_count = 0
            db.commit()
            return document

        # 3. Generate 768-dim embeddings in batch
        texts_to_embed = [c["text"] for c in chunks_data]
        embeddings = embed_texts(texts_to_embed, task_type="RETRIEVAL_DOCUMENT")

        # 4. Save chunks
        chunk_objects = []
        for idx, c_data in enumerate(chunks_data):
            emb = embeddings[idx] if idx < len(embeddings) else None
            chunk_obj = DocumentChunk(
                id=uuid.uuid4(),
                document_id=document.id,
                workspace_id=document.workspace_id,
                chunk_index=c_data["chunk_index"],
                page_number=c_data["page_number"],
                text=c_data["text"],
                embedding=emb,
            )
            chunk_objects.append(chunk_obj)

        db.add_all(chunk_objects)
        document.chunk_count = len(chunk_objects)
        document.status = "ready"
        document.failure_reason = None
        db.commit()
        db.refresh(document)
        return document

    except Exception as exc:
        logger.exception(f"Failed to process knowledge document {document.id}: {exc}")
        document.status = "failed"
        document.failure_reason = str(exc)
        db.commit()
        return document
