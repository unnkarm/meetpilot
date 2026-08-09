import io
import sys
import unittest
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Mock optional third-party modules if needed
for mod in ["pydantic_settings", "google", "google.genai", "google.genai.errors", "redis", "gradio_client"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

from app.models.document import KnowledgeDocument, DocumentChunk
from app.services.document_service import (
    chunk_document_pages,
    extract_document_pages,
    extract_text_from_docx,
    extract_text_from_text_file,
    get_file_type_from_filename,
    process_and_index_document,
)


class TestDocumentService(unittest.TestCase):
    def setUp(self):
        self.workspace_id = uuid.uuid4()
        self.doc_id = uuid.uuid4()
        self.doc = KnowledgeDocument(
            id=self.doc_id,
            workspace_id=self.workspace_id,
            title="Engineering Product Roadmap",
            filename="Product_Roadmap.pdf",
            file_type="pdf",
            file_size=1024,
            status="uploading",
        )

    def test_file_type_detection(self):
        """Tests that normalized file extensions are correctly identified."""
        self.assertEqual(get_file_type_from_filename("architecture.PDF"), "pdf")
        self.assertEqual(get_file_type_from_filename("specs.docx"), "docx")
        self.assertEqual(get_file_type_from_filename("notes.md"), "md")
        self.assertEqual(get_file_type_from_filename("readme.markdown"), "md")
        self.assertEqual(get_file_type_from_filename("data.txt"), "txt")

    def test_extract_text_from_text_and_markdown(self):
        """Tests UTF-8 text and markdown extraction."""
        content = "# Q4 Goals\n- Deliver pgvector hybrid search\n- Enable AI Knowledge Base".encode("utf-8")
        pages = extract_text_from_text_file(content)
        self.assertEqual(len(pages), 1)
        self.assertIn("Deliver pgvector hybrid search", pages[0][1])

    def test_extract_text_from_docx(self):
        """Tests DOCX extraction using zip archive and XML parsing."""
        # Create an in-memory docx structure
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as z:
            doc_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:body>
                    <w:p><w:t>MeetPilot AI Enterprise Architecture Document</w:t></w:p>
                    <w:p><w:t>Confidential security specifications.</w:t></w:p>
                </w:body>
            </w:document>"""
            z.writestr("word/document.xml", doc_xml)

        pages = extract_text_from_docx(zip_buf.getvalue())
        self.assertEqual(len(pages), 1)
        self.assertIn("Enterprise Architecture Document", pages[0][1])
        self.assertIn("Confidential security specifications", pages[0][1])

    def test_chunking_with_page_numbers(self):
        """Tests that chunking splits text into paragraphs/windows while maintaining page numbers."""
        pages = [
            (1, "Page 1 intro: This is the first section of the company knowledge base. " * 5),
            (2, "Page 2 specs: This is the second section detailing our cloud infrastructure budget. " * 5),
        ]
        chunks = chunk_document_pages(pages, target_chunk_size=200, overlap=40)
        self.assertTrue(len(chunks) >= 2)
        self.assertEqual(chunks[0]["page_number"], 1)
        self.assertEqual(chunks[-1]["page_number"], 2)

    @patch("app.services.document_service.embed_texts")
    def test_process_and_index_document(self, mock_embed):
        """Tests end-to-end document processing and pgvector chunk creation."""
        mock_embed.return_value = [[0.1] * 768, [0.2] * 768]

        content = ("MeetPilot AI empowers teams with instant meeting summaries and company knowledge retrieval. " * 10).encode("utf-8")
        self.doc.filename = "Overview.txt"
        self.doc.file_type = "txt"

        mock_db = MagicMock()
        processed = process_and_index_document(mock_db, self.doc, content)

        self.assertEqual(processed.status, "ready")
        self.assertTrue(processed.chunk_count >= 1)
        mock_db.add_all.assert_called_once()
        mock_db.commit.assert_called()


if __name__ == "__main__":
    unittest.main()
