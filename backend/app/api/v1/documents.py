import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.storage import storage_client
from app.api.deps import get_current_user, get_current_organization_membership
from app.models.user import User
from app.models.document import Document
from app.models.membership import Membership
from app.tasks.document import process_document_task

router = APIRouter()

# Size and type validations
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
}


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    organization_id: uuid.UUID = Query(..., description="Organization context ID"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Uploads a document to object storage, registers metadata, and queues parsing task."""
    # 1. Authorize user has membership in target organization
    await get_current_organization_membership(
        organization_id=organization_id, db=db, current_user=current_user
    )

    # 2. File validation checks
    # Size check
    file_size = 0
    # Read chunk by chunk to limit memory load and get size
    contents = await file.read()
    file_size = len(contents)
    # Seek back to start
    await file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB."
        )

    # Content Type check
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not supported. Allowed formats: PDF, PNG, JPEG."
        )

    # 3. Create document record
    doc_id = uuid.uuid4()
    # Format target storage path
    file_ext = ALLOWED_MIME_TYPES[file.content_type]
    object_name = f"{organization_id}/{doc_id}/original{file_ext}"

    # 4. Upload file to Object Storage
    try:
        # Wrap bytes in raw stream object for upload
        import io
        file_stream = io.BytesIO(contents)
        storage_client.upload_file(file_stream, object_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage upload failed: {str(e)}"
        )

    # 5. Commit record to database
    db_document = Document(
        id=doc_id,
        organization_id=organization_id,
        uploaded_by_id=current_user.id,
        original_filename=file.filename,
        storage_path=object_name,
        mime_type=file.content_type,
        file_size=file_size,
        page_count=0,
        status="UPLOADED",
    )
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)

    # 6. Trigger Celery worker background parsing task
    process_document_task.delay(str(db_document.id))

    return {
        "document_id": db_document.id,
        "filename": db_document.original_filename,
        "status": db_document.status,
    }


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves metadata and current processing status for a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalars().first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # Enforce strict multi-tenant isolation
    await get_current_organization_membership(
        organization_id=document.organization_id, db=db, current_user=current_user
    )

    # Get temporary pre-signed URL to view file
    presigned_url = storage_client.generate_presigned_url(document.storage_path)

    return {
        "id": document.id,
        "organization_id": document.organization_id,
        "original_filename": document.original_filename,
        "status": document.status,
        "mime_type": document.mime_type,
        "file_size": document.file_size,
        "presigned_url": presigned_url,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


@router.get("/local-file/{object_name:path}")
async def get_local_file(
    object_name: str,
    current_user: User = Depends(get_current_user),
):
    """Local file delivery endpoint for local dev file storage."""
    if settings.STORAGE_BACKEND != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local file storage is not active."
        )

    # Resolve local path
    base_dir = os.path.abspath("storage_local")
    safe_name = os.path.normpath(object_name).lstrip(os.path.sep)
    full_path = os.path.join(base_dir, safe_name)
    
    if not full_path.startswith(base_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Directory traversal block."
        )

    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found locally."
        )

    return FileResponse(full_path)


@router.get("/{document_id}/extraction")
async def get_document_extraction(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves the extracted fields and confidence scores for a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalars().first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # Enforce strict multi-tenant isolation
    await get_current_organization_membership(
        organization_id=document.organization_id, db=db, current_user=current_user
    )

    from app.models.extraction_result import ExtractionResult
    ext_result = await db.execute(
        select(ExtractionResult).where(ExtractionResult.document_id == document_id)
    )
    extraction = ext_result.scalars().first()
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction results not found for this document."
        )

    return {
        "document_id": extraction.document_id,
        "extracted_fields": extraction.extracted_fields,
        "field_confidence": extraction.field_confidence,
        "created_at": extraction.created_at,
    }


@router.get("/{document_id}/validation")
async def get_document_validation(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves the programmatic validation results and failed rule details for a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalars().first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # Enforce strict multi-tenant isolation
    await get_current_organization_membership(
        organization_id=document.organization_id, db=db, current_user=current_user
    )

    from app.models.validation_result import ValidationResult
    val_result = await db.execute(
        select(ValidationResult).where(ValidationResult.document_id == document_id)
    )
    validation = val_result.scalars().first()
    if not validation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation results not found for this document."
        )

    return {
        "document_id": validation.document_id,
        "is_valid": validation.is_valid,
        "validation_errors": validation.validation_errors,
        "created_at": validation.created_at,
    }
