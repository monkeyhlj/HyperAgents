"""Knowledge base service - Document parsing, embedding, and RAG retrieval."""
import json
import logging
import re
from typing import Optional
import hashlib

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.models import (
    DocumentModel,
    DocumentChunkModel,
    AgentKnowledgeBindingModel,
    ResourceModel,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service for managing knowledge base documents and RAG retrieval."""

    @staticmethod
    def parse_document(file_path: str, file_type: str) -> str:
        """
        Parse document and extract text content.
        
        Args:
            file_path: Path to the document file
            file_type: Type of document ('pdf', 'docx', 'md', 'txt')
            
        Returns:
            Extracted text content
        """
        if file_type == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        elif file_type == "md":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        elif file_type == "pdf":
            # Try pymupdf first (better Chinese PDF support), fallback to PyPDF2
            try:
                import fitz  # pymupdf
                text = []
                doc = fitz.open(file_path)
                for page in doc:
                    text.append(page.get_text())
                doc.close()
                return "\n".join(text)
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"pymupdf failed: {e}, trying PyPDF2")
            
            try:
                import PyPDF2
                text = []
                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text.append(page_text)
                return "\n".join(text)
            except ImportError:
                logger.warning("Neither pymupdf nor PyPDF2 installed, returning empty content for PDF")
                return ""
        
        elif file_type == "docx":
            # Use python-docx for DOCX parsing
            try:
                from docx import Document
                doc = Document(file_path)
                text = []
                for para in doc.paragraphs:
                    text.append(para.text)
                return "\n".join(text)
            except ImportError:
                logger.warning("python-docx not installed, returning empty content for DOCX")
                return ""
        
        else:
            logger.warning(f"Unsupported file type: {file_type}")
            return ""

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> list[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to split
            chunk_size: Size of each chunk (in characters)
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Split by sentences first
        sentences = re.split(r'(?<=[。！？\n])|(?<=[.!?\n])', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Add overlap
                    overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                    current_chunk = overlap_text + sentence
                else:
                    # Sentence too long, split by characters
                    for i in range(0, len(sentence), chunk_size - chunk_overlap):
                        chunks.append(sentence[i:i + chunk_size].strip())
                    current_chunk = ""
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [c for c in chunks if c]  # Filter empty chunks

    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Estimate token count (rough approximation).
        For accurate counting, use tiktoken library.
        """
        # Rough estimate: 1 token ≈ 4 characters (for English)
        # For Chinese: 1 token ≈ 1-1.5 characters
        return max(1, len(text) // 4)

    @staticmethod
    async def get_embeddings(
        texts: list[str],
        model: str = "text-embedding-3-small",
        embedding_provider: str = "openai"
    ) -> list[list[float]]:
        """
        Get embeddings for texts using OpenAI API.
        
        Args:
            texts: List of texts to embed
            model: Embedding model name
            embedding_provider: Provider (currently only "openai")
            
        Returns:
            List of embedding vectors
        """
        if embedding_provider != "openai":
            raise ValueError(f"Unsupported embedding provider: {embedding_provider}")
        
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        # OpenAI API expects max 2048 texts per request
        embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.openai_base_url}/embeddings",
                    json={
                        "input": batch,
                        "model": model,
                    },
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    }
                )
                
                if response.status_code != 200:
                    error_msg = f"OpenAI API error: {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                data = response.json()
                # Sort by index to maintain order
                sorted_data = sorted(data.get("data", []), key=lambda x: x["index"])
                batch_embeddings = [item["embedding"] for item in sorted_data]
                embeddings.extend(batch_embeddings)
        
        return embeddings

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate SHA256 hash of file for deduplication."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    async def retrieve_from_knowledge(
        db: Session,
        knowledge_id: str,
        query_text: str,
        query_embedding: list[float] | None = None,
        top_k: int = 3,
        similarity_threshold: float = 0.3,
    ) -> list[dict]:
        """
        Retrieve relevant chunks from knowledge base.
        Uses vector similarity search if embedding provided, otherwise full-text search.
        """
        from sqlalchemy import func, or_

        retrieved_chunks = []

        # Vector search (only when query_embedding is available and chunks have embeddings)
        if query_embedding:
            query_vector = json.dumps(query_embedding)
            stmt = select(
                DocumentChunkModel.id,
                DocumentChunkModel.content,
                DocumentChunkModel.document_id,
                DocumentModel.filename,
                DocumentChunkModel.source_metadata,
                (1 - func.cast(
                    DocumentChunkModel.embedding.op('<->')(query_vector),
                    float
                )).label("similarity")
            ).join(
                DocumentModel,
                DocumentChunkModel.document_id == DocumentModel.id
            ).where(
                and_(
                    DocumentChunkModel.knowledge_id == knowledge_id,
                    DocumentChunkModel.embedding_status == "done",
                    DocumentModel.status == "ready",
                )
            ).order_by(
                DocumentChunkModel.embedding.op('<->')(query_vector)
            ).limit(top_k)
            
            results = db.execute(stmt).fetchall()
            for row in results:
                if row.similarity >= similarity_threshold:
                    retrieved_chunks.append({
                        "chunk_id": row.id,
                        "content": row.content,
                        "document_id": row.document_id,
                        "filename": row.filename,
                        "similarity": float(row.similarity),
                        "metadata": row.source_metadata,
                    })

        # Full-text keyword search fallback (when no vector results or no embedding)
        if not retrieved_chunks:
            logger.info(f"[RAG] Using full-text search for knowledge_id={knowledge_id}")
            # Generate search keywords from the query
            # For Chinese text without spaces, generate n-grams prioritizing longer ones
            normalized = query_text.replace("，", " ").replace("。", " ").replace("？", " ").replace("?", " ").replace("、", " ")
            tokens = [t for t in normalized.split() if len(t) > 1]
            
            # Primary keywords: 4-char n-grams (specific) and full tokens
            primary_kws = set()
            all_kws = set()
            
            for token in tokens:
                primary_kws.add(token)
                all_kws.add(token)
            
            # If query has no spaces (pure Chinese), generate n-grams
            query_for_ngrams = "".join(tokens) if tokens else query_text
            for n in (4, 3):
                for i in range(len(query_for_ngrams) - n + 1):
                    sub = query_for_ngrams[i:i+n]
                    if n == 4:
                        primary_kws.add(sub)
                    all_kws.add(sub)
            
            search_kws = list(primary_kws)[:10]
            score_kws = list(all_kws)
            logger.info(f"[RAG] Full-text search keywords: {search_kws}")
            
            if search_kws:
                from sqlalchemy import or_
                conditions = [DocumentChunkModel.content.contains(kw) for kw in search_kws]
                ft_stmt = select(
                    DocumentChunkModel.id,
                    DocumentChunkModel.content,
                    DocumentChunkModel.document_id,
                    DocumentModel.filename,
                    DocumentChunkModel.source_metadata,
                ).join(
                    DocumentModel,
                    DocumentChunkModel.document_id == DocumentModel.id
                ).where(
                    and_(
                        DocumentChunkModel.knowledge_id == knowledge_id,
                        DocumentModel.status == "ready",
                        or_(*conditions),
                    )
                ).limit(top_k * 3)  # fetch more, then re-rank

                ft_results = db.execute(ft_stmt).fetchall()
                
                # Score: count DISTINCT keywords present (not frequency)
                # Weight 4-char primary keywords higher than 3-char secondary ones
                scored = []
                for row in ft_results:
                    primary_hits = sum(1 for kw in primary_kws if kw in row.content)
                    secondary_hits = sum(1 for kw in (all_kws - primary_kws) if kw in row.content)
                    # Primary keywords (4-char, more specific) worth 3x more
                    score = primary_hits * 3 + secondary_hits
                    scored.append((score, row))
                scored.sort(key=lambda x: x[0], reverse=True)
                
                for score, row in scored[:top_k]:
                    similarity = min(0.5 + score * 0.03, 0.9)
                    retrieved_chunks.append({
                        "chunk_id": row.id,
                        "content": row.content,
                        "document_id": row.document_id,
                        "filename": row.filename,
                        "similarity": similarity,
                        "metadata": row.source_metadata,
                    })

        return retrieved_chunks

    @staticmethod
    async def build_rag_context(
        db: Session,
        agent_id: str,
        query_text: str,
        query_embedding: list[float] | None = None,
        knowledge_base_ids: list[str] | None = None,
    ) -> str:
        """
        Build RAG context by retrieving from all bound knowledge bases.
        Falls back to knowledge_base_ids if no DB bindings found.
        """
        all_chunks = []

        # First try: knowledge_base_ids passed directly (from agent_config)
        if knowledge_base_ids:
            for kb_id in knowledge_base_ids:
                chunks = await KnowledgeService.retrieve_from_knowledge(
                    db=db,
                    knowledge_id=kb_id,
                    query_text=query_text,
                    query_embedding=query_embedding,
                    top_k=5,
                    similarity_threshold=0.3,
                )
                logger.info(f"[RAG] knowledge_id={kb_id}: {len(chunks)} chunks retrieved")
                all_chunks.extend(chunks)

        # Second try: DB bindings table
        if not all_chunks:
            stmt = select(AgentKnowledgeBindingModel).where(
                and_(
                    AgentKnowledgeBindingModel.agent_id == agent_id,
                    AgentKnowledgeBindingModel.enabled == True,
                )
            ).order_by(
                AgentKnowledgeBindingModel.priority.desc()
            )
            bindings = db.execute(stmt).scalars().all()

            for binding in bindings:
                top_k = binding.top_k or 5
                similarity_threshold = binding.similarity_threshold or 0.3
                chunks = await KnowledgeService.retrieve_from_knowledge(
                    db=db,
                    knowledge_id=binding.knowledge_id,
                    query_text=query_text,
                    query_embedding=query_embedding,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold,
                )
                logger.info(f"[RAG] binding knowledge_id={binding.knowledge_id}: {len(chunks)} chunks retrieved")
                all_chunks.extend(chunks)

        if not all_chunks:
            logger.info("[RAG] No chunks retrieved from any knowledge base")
            return ""

        # Sort by similarity and take top results
        all_chunks = sorted(all_chunks, key=lambda x: x["similarity"], reverse=True)[:5]

        # Build context
        context = "以下是相关的知识库内容:\n\n"
        for i, chunk in enumerate(all_chunks, 1):
            context += f"来源: {chunk['filename']} (相似度: {chunk['similarity']:.2%})\n"
            context += f"内容: {chunk['content'][:800]}\n\n"

        return context
