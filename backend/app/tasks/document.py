import logging
import io
import os
import tempfile
import uuid
import fitz  # PyMuPDF
from sqlalchemy.orm import Session

from app.core.config import settings
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
            
            # Extract text & coordinates using OCR or CSV Parser engine
            if ext == ".csv":
                from app.services.ocr.csv_ocr import CSVParserEngine
                ocr_engine = CSVParserEngine()
            else:
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

            # 6. Update status: OCR_COMPLETE -> EXTRACTION_PROCESSING
            document.status = "EXTRACTION_PROCESSING"
            db.commit()

            # Retrieve DocumentPage metadata to assemble image paths and text
            db_pages = db.query(DocumentPage).filter(DocumentPage.document_id == doc_uuid).order_by(DocumentPage.page_number).all()
            
            full_ocr_text = "\n".join(page.ocr_data["text"] for page in db_pages if page.ocr_data and "text" in page.ocr_data)
            
            # Resolve local image paths for the VLM input
            page_image_local_paths = []
            temp_image_files = []
            
            try:
                for page in db_pages:
                    if settings.STORAGE_BACKEND == "local":
                        # Direct local path
                        local_path = os.path.join("storage_local", page.image_storage_path)
                        page_image_local_paths.append(local_path)
                    else:
                        # Cloud storage: download to temporary local file
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                            tmp_path = tmp_img.name
                        storage_client.download_file(page.image_storage_path, tmp_path)
                        page_image_local_paths.append(tmp_path)
                        temp_image_files.append(tmp_path)
                
                # Execute Extraction (CSV Direct Schema Population or Gemini VLM)
                from app.schemas.invoice import InvoiceExtractionSchema
                from app.models.extraction_result import ExtractionResult
                
                if ext == ".csv" and getattr(ocr_result, "extracted_fields", None) is not None:
                    raw_csv_fields = ocr_result.extracted_fields
                    extracted_data = InvoiceExtractionSchema(**raw_csv_fields)
                else:
                    from app.services.vlm.gemini_vlm import GeminiVLMExtractor
                    vlm_extractor = GeminiVLMExtractor()
                    extracted_data = vlm_extractor.extract_structured_data(
                        image_paths=page_image_local_paths,
                        ocr_text=full_ocr_text,
                        schema_class=InvoiceExtractionSchema
                    )
                
                # Delete any existing extraction result for idempotency
                db.query(ExtractionResult).filter(ExtractionResult.document_id == doc_uuid).delete()
                db.commit()
                
                # Setup basic initial confidence scores (stubbing for Phase 5)
                # Map each extracted field to 0.95 confidence score
                extracted_dict = extracted_data.model_dump(mode="json")
                confidence_scores = {field: 0.95 for field in extracted_dict.keys() if extracted_dict[field] is not None}
                
                # Store Extraction Result
                db_extraction = ExtractionResult(
                    document_id=doc_uuid,
                    extracted_fields=extracted_dict,
                    field_confidence=confidence_scores,
                    raw_model_response={"source": "gemini-2.0-flash", "data": extracted_dict}
                )
                db.add(db_extraction)
                
                # Update status: EXTRACTION_PROCESSING -> EXTRACTION_COMPLETE
                document.status = "EXTRACTION_COMPLETE"
                db.commit()
                logger.info(f"VLM Extraction complete for document {document_id}")

                # Log usage events for accounting/billing
                from app.services.usage import UsageTracker
                UsageTracker.log_ocr_pages(
                    db=db,
                    organization_id=org_id,
                    user_id=document.uploaded_by_id,
                    page_count=document.page_count
                )
                UsageTracker.log_vlm_extraction(
                    db=db,
                    organization_id=org_id,
                    user_id=document.uploaded_by_id
                )
                
            finally:
                # Cleanup downloaded temp cloud images
                for tmp_path in temp_image_files:
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception as clean_err:
                            logger.warning(f"Failed to delete temp page image {tmp_path}: {str(clean_err)}")

            # 7. Update status: EXTRACTION_COMPLETE -> VALIDATING
            document.status = "VALIDATING"
            db.commit()

            # Execute Deterministic Validations
            from app.services.validation import InvoiceValidationEngine
            from app.models.validation_result import ValidationResult
            
            validation_output = InvoiceValidationEngine.validate(extracted_data)
            
            # Delete any existing validation results for idempotency
            db.query(ValidationResult).filter(ValidationResult.document_id == doc_uuid).delete()
            db.commit()
            
            # Save Validation Result
            db_validation = ValidationResult(
                document_id=doc_uuid,
                is_valid=validation_output.is_valid,
                validation_errors=[err.model_dump() for err in validation_output.errors]
            )
            db.add(db_validation)
            db.commit()
            
            # Calculate OCR average confidence from pages
            avg_ocr_confidence = 1.0
            total_words = 0
            sum_ocr_confidence = 0.0
            
            for page in db_pages:
                if page.ocr_data and "lines" in page.ocr_data:
                    for line in page.ocr_data["lines"]:
                        if "words" in line:
                            for word in line["words"]:
                                confidence = word.get("confidence")
                                if confidence is not None:
                                    sum_ocr_confidence += confidence
                                    total_words += 1
                                    
            if total_words > 0:
                avg_ocr_confidence = sum_ocr_confidence / total_words
            
            # Execute Confidence Calculations
            from app.services.confidence import ConfidenceEngine
            
            # Map initial confidence scores (defaulting to 0.95)
            initial_scores = {field: 0.95 for field in extracted_dict.keys() if extracted_dict[field] is not None}
            
            confidence_result = ConfidenceEngine.calculate_confidence(
                extracted_fields=extracted_dict,
                model_confidence_scores=initial_scores,
                validation_output=validation_output,
                avg_ocr_confidence=avg_ocr_confidence
            )
            
            # Update extraction results with calculated confidence values
            db_extraction.field_confidence = confidence_result["field_confidence"]
            db_extraction.raw_model_response = {
                "source": "gemini-2.0-flash",
                "document_confidence": confidence_result["document_confidence"],
                "data": extracted_dict
            }
            db.commit()
            
            # 8. Set final status based on validation and confidence threshold
            # Auto-review threshold: document_confidence < 0.85 OR validation.is_valid is False
            if not validation_output.is_valid or confidence_result["document_confidence"] < 0.85:
                document.status = "REVIEW_REQUIRED"
                logger.info(f"Document {document_id} transitioned to REVIEW_REQUIRED. Valid: {validation_output.is_valid}, Confidence: {confidence_result['document_confidence']}")
            else:
                document.status = "COMPLETED"
                logger.info(f"Document {document_id} successfully completed parsing pipeline.")
                
            db.commit()
            return f"Processed document {document_id} with status: {document.status}"
            
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
