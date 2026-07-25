"""Knowledge base API endpoints."""
import logging
from typing import Optional
import os

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.api.deps import get_current_user_id, get_db
from app.schemas.resource import Resource
from app.services.postgres_store import store
from app.db.models import (
    ResourceModel,
    DocumentModel,
    DocumentChunkModel,
    AgentKnowledgeBindingModel,
)
from app.models.enums import ResourceKind
from app.runtime.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["knowledge"])


class KnowledgeUploadResponse:
    """Response for document upload."""
    document_id: str
    filename: str
    file_type: str
    status: str
    message: str


@router.post("/{knowledge_id}/documents/upload")
async def upload_document(
    knowledge_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Upload a document to knowledge base.
    
    Supported formats: PDF, DOCX, MD, TXT
    """
    # Verify knowledge resource exists and user has access
    knowledge_resource = db.query(ResourceModel).filter(
        ResourceModel.id == knowledge_id
    ).first()
    
    if not knowledge_resource:
        raise HTTPException(status_code=404, detail="Knowledge resource not found")
    
    if knowledge_resource.kind != ResourceKind.KNOWLEDGE_BASE.value:
        raise HTTPException(status_code=400, detail="Resource is not a knowledge base")
    
    # Check user permission (must be project member)
    store.assert_project_member(db, knowledge_resource.project_id, user_id)
    
    # Validate file type
    allowed_types = ["pdf", "docx", "md", "txt"]
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_types)}"
        )
    
    try:
        # Save uploaded file temporarily
        upload_dir = f"/tmp/knowledge/{knowledge_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Calculate file hash for deduplication
        file_hash = KnowledgeService.calculate_file_hash(file_path)
        
        # Check if document already exists
        existing_doc = db.query(DocumentModel).filter(
            and_(
                DocumentModel.knowledge_id == knowledge_id,
                DocumentModel.file_hash == file_hash,
            )
        ).first()
        
        if existing_doc:
            raise HTTPException(
                status_code=409,
                detail="Document already exists (duplicate detected)"
            )
        
        # Create document record
        document = DocumentModel(
            knowledge_id=knowledge_id,
            project_id=knowledge_resource.project_id,
            filename=file.filename,
            file_type=file_ext,
            file_path=file_path,
            file_size=len(content),
            file_hash=file_hash,
            status="pending",
            created_by=user_id,
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(
            f"[Knowledge] Document uploaded: knowledge_id={knowledge_id}, "
            f"document_id={document.id}, filename={file.filename}"
        )
        
        return {
            "document_id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "status": document.status,
            "message": "Document uploaded successfully. Processing will start shortly.",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")


@router.get("/{knowledge_id}/documents")
def get_documents(
    knowledge_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get list of documents in knowledge base."""
    # Verify knowledge resource exists and user has access
    knowledge_resource = db.query(ResourceModel).filter(
        ResourceModel.id == knowledge_id
    ).first()
    
    if not knowledge_resource:
        raise HTTPException(status_code=404, detail="Knowledge resource not found")
    
    store.assert_project_member(db, knowledge_resource.project_id, user_id)
    
    # Build query
    query = db.query(DocumentModel).filter(
        DocumentModel.knowledge_id == knowledge_id
    )
    
    if status:
        query = query.filter(DocumentModel.status == status)
    
    total = query.count()
    
    documents = query.order_by(
        DocumentModel.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    items = [
        {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
            "total_tokens": doc.total_tokens,
            "error_message": doc.error_message,
            "created_at": doc.created_at.isoformat(),
            "created_by": doc.created_by,
        }
        for doc in documents
    ]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.delete("/{knowledge_id}/documents/{document_id}")
def delete_document(
    knowledge_id: str,
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Delete a document from knowledge base."""
    # Verify knowledge resource exists and user has access
    knowledge_resource = db.query(ResourceModel).filter(
        ResourceModel.id == knowledge_id
    ).first()
    
    if not knowledge_resource:
        raise HTTPException(status_code=404, detail="Knowledge resource not found")
    
    store.assert_project_member(db, knowledge_resource.project_id, user_id)
    
    # Find and delete document
    document = db.query(DocumentModel).filter(
        and_(
            DocumentModel.id == document_id,
            DocumentModel.knowledge_id == knowledge_id,
        )
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete associated chunks (cascade will handle this)
    db.delete(document)
    db.commit()
    
    logger.info(f"[Knowledge] Document deleted: {document_id}")
    
    return {"message": "Document deleted successfully"}


@router.post("/{knowledge_id}/reprocess")
def reprocess_documents(
    knowledge_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Reprocess failed documents in knowledge base."""
    # Verify knowledge resource exists and user has access
    knowledge_resource = db.query(ResourceModel).filter(
        ResourceModel.id == knowledge_id
    ).first()
    
    if not knowledge_resource:
        raise HTTPException(status_code=404, detail="Knowledge resource not found")
    
    store.assert_project_member(db, knowledge_resource.project_id, user_id)
    
    # Find all failed documents
    failed_docs = db.query(DocumentModel).filter(
        and_(
            DocumentModel.knowledge_id == knowledge_id,
            DocumentModel.status == "failed",
        )
    ).all()
    
    # Mark them for reprocessing
    for doc in failed_docs:
        doc.status = "pending"
        doc.error_message = None
    
    db.commit()
    
    logger.info(
        f"[Knowledge] Marked {len(failed_docs)} documents for reprocessing"
    )
    
    return {
        "message": f"Marked {len(failed_docs)} documents for reprocessing",
        "count": len(failed_docs),
    }
