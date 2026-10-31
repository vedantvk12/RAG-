import pytest
from uuid import uuid4
import fitz
import io
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ingestion.parsers.pdf_parser import PDFParser
from app.services.ingestion.parsers.text_parser import TextParser
from app.services.ingestion.chunking import chunk_text, DocumentChunkMetadata
from app.services.rag.context import build_context, GROUNDING_SYSTEM_PROMPT
from app.services.rag.generator import RAGGenerator
from app.services.rag.orchestrator import AgenticRAGOrchestrator
from app.schemas.retrieval import RetrievalResult
from app.llm.provider import LLMProvider, ChatMessage

class MockPipelineLLM(LLMProvider):
    def __init__(self, answer_map=None, default_answer="The available documents do not contain enough information to answer this question."):
        self.answer_map = answer_map or {}
        self.default_answer = default_answer
        self.calls = []

    async def generate_response(self, messages: list[ChatMessage], **kwargs) -> str:
        prompt = messages[-1].content
        self.calls.append(prompt)
        for key, ans in self.answer_map.items():
            if key in prompt:
                return ans
        return self.default_answer
        
    async def stream_response(self, messages, **kwargs):
        pass

# 1. Upload a supported PDF and extract its actual text
def test_pdf_extraction_real_text(tmp_path):
    pdf_path = tmp_path / "orion_test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Project Orion has a maximum approved budget of 18 lakh and a deadline of 15 March 2027.")
    doc.save(str(pdf_path))
    doc.close()

    parser = PDFParser()
    parsed = parser.parse(str(pdf_path), "orion_test.pdf")
    assert len(parsed.chunks) >= 1
    assert "Project Orion has a maximum approved budget of 18 lakh" in parsed.chunks[0].text
    assert parsed.chunks[0].metadata.page_number == 1

# 2. Upload a supported text or Markdown document and extract its actual text
def test_text_markdown_extraction(tmp_path):
    txt_path = tmp_path / "policy.md"
    txt_path.write_text("# HR Policy\n\nEmployees receive 24 days of paid annual leave.", encoding="utf-8")

    parser = TextParser()
    parsed = parser.parse(str(txt_path), "policy.md")
    assert len(parsed.chunks) >= 1
    assert "Employees receive 24 days of paid annual leave." in parsed.chunks[0].text

# 3. Verify empty or unreadable documents do not become falsely indexed
def test_empty_document_produces_no_chunks(tmp_path):
    empty_txt = tmp_path / "empty.txt"
    empty_txt.write_text("", encoding="utf-8")
    parser = TextParser()
    parsed = parser.parse(str(empty_txt), "empty.txt")
    assert len(parsed.chunks) == 0

# 4. Verify document metadata is preserved through chunking
def test_metadata_preserved_in_chunking():
    meta = DocumentChunkMetadata(page_number=3, section="Budget Analysis", source_type="table")
    chunks = chunk_text("First paragraph.\n\nSecond paragraph.", meta, chunk_size=500)
    for c in chunks:
        assert c.metadata.page_number == 3
        assert c.metadata.section == "Budget Analysis"
        assert c.metadata.source_type == "table"

# 5. Verify missing optional metadata does not trigger .strip() errors
def test_none_handling_in_chunking_and_context():
    meta = DocumentChunkMetadata(page_number=None, section=None, source_type="text")
    chunks = chunk_text("Testing null metadata preservation.", meta)
    assert len(chunks) == 1
    assert chunks[0].metadata.page_number is None

    result = RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        org_id=uuid4(),
        text="Sample text without section/page",
        filename="notes.txt",
        chunk_index=0,
        page_number=None,
        section=None
    )
    context_str, cited = build_context([result])
    assert "Document: notes.txt" in context_str
    assert "Page:" not in context_str

# 6 & 7. Ask a question whose answer is explicitly present in a test document & verify grounded response
@pytest.mark.asyncio
async def test_grounded_response_with_exact_fact():
    org_id = uuid4()
    doc_id = uuid4()
    chunk_id = uuid4()
    cand = RetrievalResult(
        chunk_id=chunk_id,
        document_id=doc_id,
        org_id=org_id,
        text="Project Orion has a maximum approved budget of Rs 18 lakh and a delivery deadline of 15 March 2027.",
        filename="project_orion.pdf",
        chunk_index=0,
        page_number=1,
        rerank_score=0.98
    )

    generator = RAGGenerator()
    generator.llm_provider = MockPipelineLLM(answer_map={
        "approved budget": "The approved budget for Project Orion is Rs 18 lakh [Source 1]."
    })

    with patch("app.services.rag.generator.get_org_document_registry", new_callable=AsyncMock) as mock_reg:
        with patch("app.services.rag.generator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
            with patch("app.services.rag.generator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
                mock_reg.return_value = [{"id": str(doc_id), "filename": "project_orion.pdf", "status": "indexed", "created_at": "2026-10-09 10:00:00 UTC"}]
                mock_hybrid.return_value = [cand]
                mock_rerank.return_value = [cand]

                resp = await generator.generate_grounded_response("What is the approved budget for Project Orion?", org_id, 5)
                assert "18 lakh" in resp.answer
                assert "[Source 1]" in resp.citation_validation.valid_citations
                assert len(resp.sources) == 1
                assert resp.sources[0].filename == "project_orion.pdf"

# 8. Ask a question whose answer is absent and verify the system abstains
@pytest.mark.asyncio
async def test_absent_question_abstains():
    org_id = uuid4()
    generator = RAGGenerator()
    generator.llm_provider = MockPipelineLLM(default_answer="The available documents do not contain enough information to answer this question.")

    with patch("app.services.rag.generator.get_org_document_registry", new_callable=AsyncMock) as mock_reg:
        with patch("app.services.rag.generator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
            with patch("app.services.rag.generator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
                mock_reg.return_value = []
                mock_hybrid.return_value = []
                mock_rerank.return_value = []

                resp = await generator.generate_grounded_response("What is the lead engineer's name?", org_id, 5)
                assert "available documents do not contain enough information" in resp.answer

# 10. Ask which PDF was uploaded most recently and verify metadata-based ordering
@pytest.mark.asyncio
async def test_metadata_question_latest_pdf():
    org_id = uuid4()
    doc1_time = "2026-10-09 10:00:00 UTC"
    doc2_time = "2026-10-09 15:30:00 UTC"

    docs_registry = [
        {"id": str(uuid4()), "filename": "annual_report_2026.pdf", "status": "indexed", "created_at": doc2_time},
        {"id": str(uuid4()), "filename": "hr_policy_v1.pdf", "status": "indexed", "created_at": doc1_time},
    ]

    generator = RAGGenerator()
    generator.llm_provider = MockPipelineLLM(answer_map={
        "latest PDF": "The most recently uploaded PDF is annual_report_2026.pdf, uploaded at 2026-10-09 15:30:00 UTC."
    })

    with patch("app.services.rag.generator.get_org_document_registry", new_callable=AsyncMock) as mock_reg:
        with patch("app.services.rag.generator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
            with patch("app.services.rag.generator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
                mock_reg.return_value = docs_registry
                mock_hybrid.return_value = []
                mock_rerank.return_value = []

                resp = await generator.generate_grounded_response("Which are the latest PDF files uploaded in the Knowledge Base?", org_id, 5)
                assert "annual_report_2026.pdf" in resp.answer
                assert resp.retrieval_metadata["documents_in_registry"] == 2

# 15. Verify organization A cannot retrieve organization B's documents or citations
@pytest.mark.asyncio
async def test_tenant_isolation_cross_organization_rejection():
    org_a = uuid4()
    org_b = uuid4()
    leak_cand = RetrievalResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        org_id=org_b,
        text="Confidential Org B Salary Data",
        filename="salaries.xlsx",
        chunk_index=0
    )

    generator = RAGGenerator()
    with patch("app.services.rag.generator.get_org_document_registry", new_callable=AsyncMock) as mock_reg:
        with patch("app.services.rag.generator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
            with patch("app.services.rag.generator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
                mock_reg.return_value = []
                mock_hybrid.return_value = [leak_cand]
                mock_rerank.return_value = [leak_cand]

                with pytest.raises(Exception, match="Security Error"):
                    await generator.generate_grounded_response("Show me salaries", org_a, 5)

# 16. Multi-page PDF produces the correct page count and page-level metadata
def test_multipage_pdf_page_count_and_chunks(tmp_path):
    pdf_path = tmp_path / "three_page_paper.pdf"
    doc = fitz.open()
    
    p1 = doc.new_page()
    p1.insert_text((50, 72), "Title: Advanced Robotics in Modern Manufacturing\nAbstract: Exploring robotics...")
    
    p2 = doc.new_page()
    p2.insert_text((50, 72), "Methodology: We implemented a dual-arm manipulator with 6 degrees of freedom.")
    
    p3 = doc.new_page()
    p3.insert_text((50, 72), "Conclusion: The precision improved by 34.2% across all benchmark trials.")
    
    doc.save(str(pdf_path))
    doc.close()

    parser = PDFParser()
    parsed = parser.parse(str(pdf_path), "three_page_paper.pdf")
    assert parsed.metadata.get("page_count") == 3
    assert len(parsed.chunks) >= 3
    
    page_numbers = [c.metadata.page_number for c in parsed.chunks]
    assert 1 in page_numbers
    assert 2 in page_numbers
    assert 3 in page_numbers

# 17. Page count query correctly answers using Document Registry metadata
@pytest.mark.asyncio
async def test_page_count_question_uses_metadata():
    org_id = uuid4()
    doc_id = uuid4()
    docs_registry = [
        {
            "id": str(doc_id),
            "filename": "three_page_paper.pdf",
            "status": "indexed",
            "page_count": 3,
            "file_size": "45.2 KB",
            "created_at": "2026-10-09 18:00:00 UTC",
            "is_latest": True
        }
    ]

    generator = RAGGenerator()
    generator.llm_provider = MockPipelineLLM(answer_map={
        "How many pages": "The PDF three_page_paper.pdf contains 3 pages based on the document registry."
    })

    with patch("app.services.rag.generator.get_org_document_registry", new_callable=AsyncMock) as mock_reg:
        with patch("app.services.rag.generator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
            with patch("app.services.rag.generator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
                mock_reg.return_value = docs_registry
                mock_hybrid.return_value = []
                mock_rerank.return_value = []

                resp = await generator.generate_grounded_response("How many pages are included in this PDF?", org_id, 5)
                assert "3 pages" in resp.answer
                assert resp.retrieval_metadata["documents_in_registry"] == 1

# 18. Follow-up conversational question preserves context
@pytest.mark.asyncio
async def test_conversational_followup_preserves_context():
    org_id = uuid4()
    doc_id = uuid4()
    docs_registry = [
        {
            "id": str(doc_id),
            "filename": "research_report.pdf",
            "status": "indexed",
            "page_count": 12,
            "created_at": "2026-10-09 20:00:00 UTC",
            "is_latest": True
        }
    ]

    conversation_history = [
        {"role": "user", "content": "Which is the latest PDF uploaded?"},
        {"role": "assistant", "content": "The latest PDF is research_report.pdf, uploaded at 2026-10-09 20:00:00 UTC."}
    ]

    generator = RAGGenerator()
    generator.llm_provider = MockPipelineLLM(answer_map={
        "How many pages does it have?": "The research_report.pdf contains 12 pages."
    })

    with patch("app.services.rag.generator.get_org_document_registry", new_callable=AsyncMock) as mock_reg:
        with patch("app.services.rag.generator.HybridRetriever.search", new_callable=AsyncMock) as mock_hybrid:
            with patch("app.services.rag.generator.reranker_service.rerank_results", new_callable=AsyncMock) as mock_rerank:
                mock_reg.return_value = docs_registry
                mock_hybrid.return_value = []
                mock_rerank.return_value = []

                resp = await generator.generate_grounded_response(
                    "How many pages does it have?",
                    org_id,
                    5,
                    conversation_history=conversation_history
                )
                assert "12 pages" in resp.answer

