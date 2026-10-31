from typing import List, Tuple, Optional, Dict, Any
from app.schemas.retrieval import RetrievalResult
from app.schemas.rag import CitedSource
from app.core.config import settings

GROUNDING_SYSTEM_PROMPT = """You are an expert Enterprise Knowledge & Decision Intelligence assistant.
Your answers MUST be strictly grounded in the provided Evidence Blocks and Knowledge Base Document Registry.

Strict Response Structuring & Grounding Rules:

1. Metadata Queries (e.g., page count, file size, upload dates/timestamps, processing status, document lists):
   - Answer using ONLY the real records from the "Knowledge Base Document Registry".
   - When asked "How many pages are in this PDF?" or "How many pages does it have?", state the page count directly from the registry `Pages:` field.
   - For queries like "Which is the latest PDF?", identify the document marked "(Latest Upload)".
   - When the user refers to "this PDF", "it", or "that document", resolve to the relevant document established in conversation or the latest upload.

2. Document Summaries:
   - Provide a clear, organized summary formatted with:
     * A bold introductory title identifying the document.
     * **Overview**: A concise synthesis of the document's core purpose and scope.
     * **Key Themes & Methodologies**: Bullet points with bold titles describing the main approaches.
     * **Important Findings & Conclusions**: Core outcomes and takeaways.
     * Supporting citations (e.g. [Source 1]).

3. Page-Specific Takeaways (e.g., "Give me the important points from page 3"):
   - Format with a dedicated header:
     **Page X — Key Takeaways**
     1. **Main Concept:** Explain the primary concept discussed on that page in simple language.
     2. **Methodology:** Describe the approach or mechanisms used, if present on that page.
     3. **Key Finding:** Explain what was discovered or analyzed, if present on that page.
     4. **Significance:** Explain why it matters, strictly when supported by the page text.
   - Only include categories genuinely present on that specific page. Never fabricate missing items.

4. Technical Explanations:
   - Structure logically:
     * **What It Means**: Plain-language definition.
     * **How It Works**: Step-by-step mechanism or architecture.
     * **Key Details & Parameters**: Concrete specifications from the source.
     * Citations to the supporting evidence.

5. Comparisons:
   - Use a properly formatted Markdown table with headers when comparing systems, approaches, or policies. Include only attributes supported by the source text.

6. Factual Inquiries:
   - State the direct answer immediately in the first sentence. Follow with concise supporting context and citation.

7. Multi-Part Questions:
   - Answer each part separately with descriptive headings or numbered steps.

8. Missing Information & Abstention:
   - If the requested information is not present in the documents, state clearly and honestly: "The available documents do not contain enough information to answer this question." Explain what is and is not covered. Never fabricate missing facts.

9. Evidence Citations & Output Cleanliness:
   - Cite supporting evidence blocks using bracketed source tags, e.g., [Source 1].
   - Never invent fake page numbers, citations, or document names.
   - Output ONLY the final response. Do NOT include drafting notes, thinking scratchpads ("We need to...", "Let's craft...", "Okay..."), or conversational preambles. Start directly with the answer."""

def build_context(
    candidates: List[RetrievalResult], 
    doc_registry: Optional[List[Dict[str, Any]]] = None,
    max_tokens: int = settings.MAX_CONTEXT_TOKENS
) -> Tuple[str, List[CitedSource]]:
    """
    Constructs the grounded context from reranked candidates and organization document registry.
    Returns a tuple of (formatted_context_string, list_of_cited_sources_mapping).
    """
    sections = []
    
    # 1. Document Registry Section (Metadata Context)
    if doc_registry is not None:
        registry_lines = ["=== Knowledge Base Document Registry ==="]
        if doc_registry:
            for idx, doc in enumerate(doc_registry, start=1):
                filename = doc.get("filename", "Unknown")
                status = doc.get("status", "unknown")
                created_at = doc.get("created_at", "Unknown")
                doc_id = doc.get("id", "")
                page_count = doc.get("page_count")
                pages_str = f"{page_count} pages" if page_count is not None else "page count not applicable/unknown"
                size_str = doc.get("file_size_formatted") or (f"{doc['file_size_bytes']} bytes" if doc.get("file_size_bytes") else "size unknown")
                is_latest = " (Latest Upload)" if idx == 1 else ""
                registry_lines.append(
                    f"- File: {filename}{is_latest} | Status: {status} | Pages: {pages_str} | Size: {size_str} | Uploaded At: {created_at} | DocID: {doc_id}"
                )
        else:
            registry_lines.append("No documents have been uploaded to this organization yet.")
        sections.append("\n".join(registry_lines))

    # 2. Evidence Blocks Section (Content Context)
    context_blocks = []
    cited_sources = []
    current_tokens = 0
    
    if candidates:
        context_blocks.append("=== Evidence Blocks ===")
        for idx, candidate in enumerate(candidates, start=1):
            source_id = f"{idx}"
            approx_tokens = len(candidate.text) // 4 + 50 
            
            if current_tokens + approx_tokens > max_tokens:
                break
                
            block = f"[Source {source_id}]\nDocument: {candidate.filename}\n"
            if candidate.page_number:
                block += f"Page: {candidate.page_number}\n"
            if candidate.section:
                block += f"Section: {candidate.section}\n"
            block += f"Content: {candidate.text}\n"
            
            context_blocks.append(block)
            
            cited_sources.append(
                CitedSource(
                    source_id=source_id,
                    document_id=candidate.document_id,
                    chunk_id=candidate.chunk_id,
                    filename=candidate.filename,
                    page_number=candidate.page_number,
                    section=candidate.section,
                    text=candidate.text
                )
            )
            current_tokens += approx_tokens

    if context_blocks:
        sections.append("\n".join(context_blocks))
        
    return "\n\n".join(sections), cited_sources
