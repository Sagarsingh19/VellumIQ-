import logging
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Security, status
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.storage import storage_client
from app.api.deps import (
    get_current_user,
    get_current_organization_membership,
    verify_tenant_access,
    get_current_user_optional,
    api_key_header,
    api_key_query
)
from app.models.user import User
from app.models.document import Document
from app.models.membership import Membership
from app.schemas.review import ReviewSubmission
from app.tasks.document import process_document_task

router = APIRouter()

# Size and type validations
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "text/csv": ".csv",
    "application/vnd.ms-excel": ".csv",
    "text/plain": ".csv",
}


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    organization_id: uuid.UUID = Query(..., description="Organization context ID"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    authenticated_org_id: uuid.UUID = Depends(verify_tenant_access),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Uploads a document to object storage, registers metadata, and queues parsing task."""
    # verify_tenant_access dependency verifies EITHER valid active API Key OR User Org membership

    # 1.5 Check subscription page quota
    from app.services.usage import check_quota_async
    has_quota = await check_quota_async(db, organization_id, incoming_pages=1)
    if not has_quota:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Organization monthly page processing limit reached. Upgrade subscription."
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
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file.content_type not in ALLOWED_MIME_TYPES and file_ext != ".csv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not supported. Allowed formats: PDF, PNG, JPEG, CSV."
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
        uploaded_by_id=current_user.id if current_user else None,
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
    current_user: Optional[User] = Depends(get_current_user_optional),
    api_key_hdr: Optional[str] = Security(api_key_header),
    api_key_qry: Optional[str] = Security(api_key_query),
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
    await verify_tenant_access(
        organization_id=document.organization_id,
        api_key_hdr=api_key_hdr,
        api_key_qry=api_key_qry,
        current_user=current_user,
        db=db
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
    current_user: Optional[User] = Depends(get_current_user_optional),
    api_key_hdr: Optional[str] = Security(api_key_header),
    api_key_qry: Optional[str] = Security(api_key_query),
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
    await verify_tenant_access(
        organization_id=document.organization_id,
        api_key_hdr=api_key_hdr,
        api_key_qry=api_key_qry,
        current_user=current_user,
        db=db
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
    current_user: Optional[User] = Depends(get_current_user_optional),
    api_key_hdr: Optional[str] = Security(api_key_header),
    api_key_qry: Optional[str] = Security(api_key_query),
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
    await verify_tenant_access(
        organization_id=document.organization_id,
        api_key_hdr=api_key_hdr,
        api_key_qry=api_key_qry,
        current_user=current_user,
        db=db
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


@router.post("/{document_id}/review")
async def review_document(
    document_id: uuid.UUID,
    review_submission: ReviewSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submits human corrections for an invoice, updates extraction/validation schemas, and transitions document status."""
    # 1. Fetch document metadata
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalars().first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # 2. Enforce strict multi-tenant isolation
    await get_current_organization_membership(
        organization_id=document.organization_id, db=db, current_user=current_user
    )

    # 3. Retrieve original extraction results
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

    original_fields = extraction.extracted_fields
    corrected_dict = review_submission.corrected_fields.model_dump(mode="json")

    # 4. Save review log record
    from app.models.review import Review
    from datetime import datetime, timezone
    
    review_log = Review(
        document_id=document_id,
        reviewed_by_id=current_user.id,
        original_fields=original_fields,
        corrected_fields=corrected_dict,
        status="COMPLETED",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(review_log)

    # 5. Overwrite the extraction result with the human corrected data
    extraction.extracted_fields = corrected_dict
    # Set all corrected field confidence ratings to 1.0 (since verified by a human!)
    extraction.field_confidence = {key: 1.0 for key in corrected_dict.keys() if corrected_dict[key] is not None}
    db.add(extraction)

    # 6. Re-run validations based on corrected data
    from app.services.validation import InvoiceValidationEngine
    from app.models.validation_result import ValidationResult
    
    validation_output = InvoiceValidationEngine.validate(review_submission.corrected_fields)
    
    # Update validation result record in database
    val_result = await db.execute(
        select(ValidationResult).where(ValidationResult.document_id == document_id)
    )
    validation = val_result.scalars().first()
    if validation:
        validation.is_valid = validation_output.is_valid
        validation.validation_errors = [err.model_dump() for err in validation_output.errors]
        db.add(validation)

    # 7. Create Audit Log entry
    from app.models.audit_log import AuditLog
    audit = AuditLog(
        organization_id=document.organization_id,
        user_id=current_user.id,
        action="DOCUMENT_REVIEWED",
        entity_type="document",
        entity_id=document_id,
        details={
            "original_fields": original_fields,
            "corrected_fields": corrected_dict
        }
    )
    db.add(audit)

    # 8. Update Document status to COMPLETED (since reviewed by human)
    document.status = "COMPLETED"
    db.add(document)

    await db.commit()
    logger.info(f"Document {document_id} successfully reviewed and approved by user {current_user.id}")

    return {
        "status": "success",
        "document_status": document.status,
        "is_valid": validation_output.is_valid,
    }
