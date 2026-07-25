"""Background tasks for processing knowledge base documents."""
import logging
import asyncio
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import DocumentModel, DocumentChunkModel
from app.runtime.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)


async def process_pending_documents():
    """
    Background task to process pending documents.
    - Parse document content
    - Split into chunks
    - Generate embeddings
    """
    db = SessionLocal()
    
    try:
        # Get all pending documents
        pending_docs = db.query(DocumentModel).filter(
            DocumentModel.status == "pending"
        ).all()
        
        if not pending_docs:
            return
        
        logger.info(f"[Knowledge Background] Processing {len(pending_docs)} documents")
        
        for doc in pending_docs:
            try:
                await process_document(db, doc)
            except Exception as e:
                logger.error(
                    f"Error processing document {doc.id}: {str(e)}",
                    exc_info=True
                )
                doc.status = "failed"
                doc.error_message = str(e)[:500]
                db.commit()
    
    finally:
        db.close()


async def process_document(db: Session, document: DocumentModel):
    """Process a single document: parse, chunk, and embed."""
    
    logger.info(f"[Knowledge] Processing document: {document.filename}")
    document.status = "processing"
    db.commit()
    
    try:
        # Step 1: Parse document
        logger.debug(f"[Knowledge] Parsing document: {document.filename}")
        text = KnowledgeService.parse_document(document.file_path, document.file_type)
        
        if not text or not text.strip():
            raise ValueError("Document is empty or could not be parsed")
        
        # Step 2: Split into chunks
        config = document.metadata or {}
        chunk_size = config.get("chunk_size", 512)
        chunk_overlap = config.get("chunk_overlap", 50)
        
        logger.debug(f"[Knowledge] Chunking document (size={chunk_size}, overlap={chunk_overlap})")
        chunks = KnowledgeService.chunk_text(text, chunk_size, chunk_overlap)
        
        if not chunks:
            raise ValueError("No chunks generated from document")
        
        # Step 3: Create chunk records and get embeddings
        logger.debug(f"[Knowledge] Creating {len(chunks)} chunks")
        
        chunk_records = []
        for i, chunk_text in enumerate(chunks):
            tokens = KnowledgeService.count_tokens(chunk_text)
            chunk = DocumentChunkModel(
                document_id=document.id,
                knowledge_id=document.knowledge_id,
                project_id=document.project_id,
                chunk_index=i,
                content=chunk_text,
                tokens=tokens,
                embedding_status="pending",
                embedding_model="openai:text-embedding-3-small",
                source_metadata={"page": 0, "position": i},  # TODO: Extract real metadata
            )
            chunk_records.append(chunk)
        
        db.add_all(chunk_records)
        db.flush()
        
        # Update document statistics
        total_tokens = sum(c.tokens for c in chunk_records)
        document.chunk_count = len(chunk_records)
        document.total_tokens = total_tokens
        
        # Step 4: Generate embeddings (async)
        logger.debug(f"[Knowledge] Generating embeddings for {len(chunk_records)} chunks")
        
        texts_to_embed = [c.content for c in chunk_records]
        
        try:
            embeddings = await KnowledgeService.get_embeddings(
                texts_to_embed,
                model="text-embedding-3-small",
                embedding_provider="openai"
            )
            
            # Update chunks with embeddings
            for chunk, embedding in zip(chunk_records, embeddings):
                chunk.embedding = embedding
                chunk.embedding_status = "done"
            
            logger.info(
                f"[Knowledge] Document processed successfully: {document.filename}, "
                f"chunks={len(chunk_records)}, tokens={total_tokens}"
            )
        
        except Exception as e:
            logger.warning(
                f"[Knowledge] Could not generate embeddings (continuing): {str(e)}"
            )
            # Mark chunks as ready even without embeddings (RAG may fail but processing succeeds)
            for chunk in chunk_records:
                chunk.embedding_status = "failed"
                chunk.embedding_error = str(e)[:200]
        
        # Mark document as ready
        document.status = "ready"
        document.error_message = None
        
        db.commit()
        
        logger.info(f"[Knowledge] Document ready: {document.id}")
    
    except Exception as e:
        logger.error(f"[Knowledge] Error processing document: {str(e)}", exc_info=True)
        document.status = "failed"
        document.error_message = str(e)[:500]
        db.commit()
        raise


async def process_pending_embeddings():
    """
    Background task to process chunks with pending embeddings.
    (For retrying failed embeddings or batch processing)
    """
    db = SessionLocal()
    
    try:
        # Get chunks with pending embeddings
        pending_chunks = db.query(DocumentChunkModel).filter(
            DocumentChunkModel.embedding_status == "pending"
        ).all()
        
        if not pending_chunks:
            return
        
        logger.info(f"[Knowledge Background] Processing {len(pending_chunks)} pending embeddings")
        
        # Batch process
        batch_size = 100
        for i in range(0, len(pending_chunks), batch_size):
            batch = pending_chunks[i:i+batch_size]
            
            try:
                texts = [chunk.content for chunk in batch]
                embeddings = await KnowledgeService.get_embeddings(
                    texts,
                    model="text-embedding-3-small",
                    embedding_provider="openai"
                )
                
                for chunk, embedding in zip(batch, embeddings):
                    chunk.embedding = embedding
                    chunk.embedding_status = "done"
                
                db.commit()
            
            except Exception as e:
                logger.error(f"Error embedding batch: {str(e)}")
                # Mark as failed so we can retry later
                for chunk in batch:
                    chunk.embedding_status = "failed"
                    chunk.embedding_error = str(e)[:200]
                db.commit()
    
    finally:
        db.close()
