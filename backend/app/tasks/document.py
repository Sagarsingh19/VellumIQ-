import logging
import io
import os
import tempfile
import uuid
import fitz  # PyMuPDF
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import sync_session_maker
from app.core.storage import storage_client
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.services.ocr.pdf_plumber_ocr import PDFPlumberOCREngine

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.document.process_document_task", bind=True, max_retries=3)
def process_document_task(self, document_id: str) -> str:
    """Asynchronous background task executing the document parsing pipeline."""
    logger.info(f"Starting processing pipeline for document: {document_id}")
    
    db: Session = sync_session_maker()
    try:
        # Cast to uuid.UUID object for SQLAlchemy SQLite engine compatibility
        doc_uuid = uuid.UUID(document_id) if isinstance(document_id, str) else document_id
        
        # 1. Fetch document metadata
        document = db.query(Document).filter(Document.id == doc_uuid).first()
        if not document:
            error_msg = f"Document {document_id} not found in database."
            logger.error(error_msg)
            return error_msg

        # 2. Update status: UPLOADED -> PROCESSING
        document.status = "PROCESSING"
        db.commit()
        logger.info(f"Document {document_id} updated to status: PROCESSING")

        # Create local temporary file path to download original file
        _, ext = os.path.splitext(document.original_filename.lower())
        temp_file_path = None
        
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            # Download file from storage
            storage_client.download_file(document.storage_path, temp_file_path)
            
            # 3. Update status: PROCESSING -> OCR_PROCESSING
            document.status = "OCR_PROCESSING"
            db.commit()
            
            # Extract text & coordinates using pdfplumber OCR engine
            ocr_engine = PDFPlumberOCREngine()
            ocr_result = ocr_engine.extract_text(temp_file_path)
            
            # 4. Rasterize pages to PNG and upload to storage, then write page metadata
            org_id = document.organization_id
            
            # Delete any existing document pages to ensure idempotency on retries
            db.query(DocumentPage).filter(DocumentPage.document_id == doc_uuid).delete()
            db.commit()
            
            if ext == ".pdf":
                # PDF Rasterization using PyMuPDF
                pdf_doc = fitz.open(temp_file_path)
                for idx, ocr_page in enumerate(ocr_result.pages):
                    page_num = ocr_page.page_number
                    # Extract pixmap image (DPI 150)
                    fitz_page = pdf_doc[page_num - 1]
                    pix = fitz_page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    
                    # Store PNG page
                    page_object_name = f"{org_id}/{doc_uuid}/pages/page_{page_num}.png"
                    storage_client.upload_file(io.BytesIO(img_bytes), page_object_name)
                    
                    # Write to database
                    db_page = DocumentPage(
                        document_id=doc_uuid,
                        page_number=page_num,
                        image_storage_path=page_object_name,
                        ocr_data=ocr_page.model_dump()
                    )
                    db.add(db_page)
                pdf_doc.close()
            else:
                # Image fallback: original file is the only page
                for idx, ocr_page in enumerate(ocr_result.pages):
                    page_num = ocr_page.page_number
                    db_page = DocumentPage(
                        document_id=doc_uuid,
                        page_number=page_num,
                        image_storage_path=document.storage_path,
                        ocr_data=ocr_page.model_dump()
                    )
                    db.add(db_page)
                    
            # 5. Update status: OCR_PROCESSING -> OCR_COMPLETE
            document.status = "OCR_COMPLETE"
            document.page_count = len(ocr_result.pages)
            db.commit()
            logger.info(f"OCR stage complete for {document_id}. Total pages: {document.page_count}")
            
            # --- Future Pipeline Steps (Placeholder) -------------
            # Phase 4: VLM Extraction
            # Phase 5: Schema & Math Validation
            # -----------------------------------------------------

            # Temporary completion flag for Phase 3 slice
            document.status = "COMPLETED"
            db.commit()
            logger.info(f"Document {document_id} successfully completed pipeline.")
            return f"Successfully processed document {document_id}"
            
        finally:
            # Cleanup temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp file {temp_file_path}: {str(cleanup_err)}")
                    
    except Exception as e:
        logger.exception(f"Pipeline failure for document {document_id}: {str(e)}")
        
        # Reload db connection and update status to FAILED
        try:
            db.rollback()
            document = db.query(Document).filter(Document.id == doc_uuid).first()
            if document:
                document.status = "FAILED"
                db.commit()
        except Exception as rollback_err:
            logger.critical(f"Failed to record FAILED status for {document_id}: {str(rollback_err)}")
            
        # Re-raise to trigger Celery retry mechanism or record failure
        raise e
        
    finally:
        db.close()
