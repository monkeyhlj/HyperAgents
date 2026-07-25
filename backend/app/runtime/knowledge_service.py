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
            # Use PyPDF2 for PDF parsing
            try:
                import PyPDF2
                text = []
                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text.append(page.extract_text())
                return "\n".join(text)
            except ImportError:
                logger.warning("PyPDF2 not installed, returning empty content for PDF")
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
        
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set")
        
        # OpenAI API expects max 2048 texts per request
        embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.OPENAI_BASE_URL}/embeddings",
                    json={
                        "input": batch,
                        "model": model,
                    },
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
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
        query_embedding: list[float],
        top_k: int = 3,
        similarity_threshold: float = 0.7,
    ) -> list[dict]:
        """
        Retrieve relevant chunks from knowledge base using similarity search.
        
        Args:
            db: Database session
            knowledge_id: ID of knowledge resource
            query_text: User query text
            query_embedding: Embedding vector of query
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of relevant chunks with metadata
        """
        from sqlalchemy import func
        
        # Convert list to PostgreSQL vector format
        query_vector = json.dumps(query_embedding)
        
        # PostgreSQL similarity search using cosine distance
        stmt = select(
            DocumentChunkModel.id,
            DocumentChunkModel.content,
            DocumentChunkModel.document_id,
            DocumentModel.filename,
            DocumentChunkModel.source_metadata,
            # Calculate cosine similarity (1 - distance)
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
        
        retrieved_chunks = []
        for row in results:
            # Only include chunks above threshold
            if row.similarity >= similarity_threshold:
                retrieved_chunks.append({
                    "chunk_id": row.id,
                    "content": row.content,
                    "document_id": row.document_id,
                    "filename": row.filename,
                    "similarity": float(row.similarity),
                    "metadata": row.source_metadata,
                })
        
        return retrieved_chunks

    @staticmethod
    async def build_rag_context(
        db: Session,
        agent_id: str,
        query_text: str,
        query_embedding: list[float],
    ) -> str:
        """
        Build RAG context by retrieving from all bound knowledge bases.
        
        Args:
            db: Database session
            agent_id: ID of agent
            query_text: User query
            query_embedding: Query embedding
            
        Returns:
            Formatted RAG context to be added to LLM prompt
        """
        # Get all knowledge bases bound to this agent
        stmt = select(AgentKnowledgeBindingModel).where(
            and_(
                AgentKnowledgeBindingModel.agent_id == agent_id,
                AgentKnowledgeBindingModel.enabled == True,
            )
        ).order_by(
            AgentKnowledgeBindingModel.priority.desc()
        )
        
        bindings = db.execute(stmt).scalars().all()
        
        if not bindings:
            return ""
        
        all_chunks = []
        
        for binding in bindings:
            # Use binding-specific config or defaults
            top_k = binding.top_k or 3
            similarity_threshold = binding.similarity_threshold or 0.7
            
            chunks = await KnowledgeService.retrieve_from_knowledge(
                db=db,
                knowledge_id=binding.knowledge_id,
                query_text=query_text,
                query_embedding=query_embedding,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )
            
            all_chunks.extend(chunks)
        
        if not all_chunks:
            return ""
        
        # Sort by similarity and take top results
        all_chunks = sorted(all_chunks, key=lambda x: x["similarity"], reverse=True)[:3]
        
        # Build context
        context = "以下是相关的知识库内容:\n\n"
        for i, chunk in enumerate(all_chunks, 1):
            context += f"来源: {chunk['filename']} (相似度: {chunk['similarity']:.2%})\n"
            context += f"内容: {chunk['content'][:500]}...\n\n"
        
        return context
