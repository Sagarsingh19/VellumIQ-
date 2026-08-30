import io
import os
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.document import Document
from app.models.membership import Membership
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def create_test_user_and_headers(client: AsyncClient, email: str):
    """Utility to create a user, log them in, and return headers + user object details."""
    signup_res = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "testpassword123"},
    )
    assert signup_res.status_code == 201
    user_id = uuid.UUID(signup_res.json()["id"])
    
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "testpassword123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": user_id
    }


async def get_user_organization(db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
    """Helper to fetch the auto-created organization ID for a user."""
    result = await db.execute(
        select(Membership.organization_id).where(Membership.user_id == user_id)
    )
    return result.scalars().first()


async def test_upload_document_success(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup user and organization
    user_data = await create_test_user_and_headers(client, "uploader@example.com")
    org_id = await get_user_organization(db_session, user_data["user_id"])
    
    # Generate a valid PDF using PyMuPDF to test rasterization and digital text parsing
    import fitz
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 30), "Vendor: Acme Corp")
    page.insert_text((50, 50), "Invoice Number: INV-12345")
    page.insert_text((50, 80), "Invoice Date: 2026-08-25")
    page.insert_text((50, 100), "Subtotal: 1000.00")
    page.insert_text((50, 120), "Tax: 150.00")
    page.insert_text((50, 140), "Total: 1150.00")
    file_content = pdf_doc.write()
    pdf_doc.close()
    
    # 2. Upload file
    files = {"file": ("invoice.pdf", file_content, "application/pdf")}
    
    response = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files=files,
        headers=user_data["headers"]
    )
    assert response.status_code == 202
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "invoice.pdf"
    assert data["status"] == "UPLOADED"
    
    # 3. Verify database updates
    doc_id = uuid.UUID(data["document_id"])
    db_result = await db_session.execute(select(Document).where(Document.id == doc_id))
    db_doc = db_result.scalars().first()
    
    assert db_doc is not None
    assert db_doc.original_filename == "invoice.pdf"
    assert db_doc.file_size == len(file_content)
    
    # Since CELERY_TASK_ALWAYS_EAGER=True in conftest, the Celery task executed synchronously,
    # and the document state should transition to COMPLETED immediately.
    assert db_doc.status == "COMPLETED"

    # 4. Verify pages were created in DB
    from app.models.document_page import DocumentPage
    pages_result = await db_session.execute(
        select(DocumentPage).where(DocumentPage.document_id == doc_id)
    )
    db_pages = pages_result.scalars().all()
    assert len(db_pages) == 1
    assert db_pages[0].page_number == 1
    assert db_pages[0].image_storage_path.endswith(".png")
    assert "Invoice Number:" in db_pages[0].ocr_data["text"]
    
    # 5. Verify local storage has the rasterized PNG page
    local_img_path = os.path.join("storage_local", db_pages[0].image_storage_path)
    assert os.path.exists(local_img_path)


async def test_upload_document_invalid_type(client: AsyncClient, db_session: AsyncSession):
    user_data = await create_test_user_and_headers(client, "invalid@example.com")
    org_id = await get_user_organization(db_session, user_data["user_id"])
    
    files = {"file": ("malicious.html", b"<html></html>", "text/html")}
    
    response = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files=files,
        headers=user_data["headers"]
    )
    assert response.status_code == 400
    assert "Allowed formats" in response.json()["detail"]


async def test_upload_document_too_large(client: AsyncClient, db_session: AsyncSession):
    user_data = await create_test_user_and_headers(client, "largefile@example.com")
    org_id = await get_user_organization(db_session, user_data["user_id"])
    
    # Generate larger chunk than 10MB limit
    large_data = b"0" * (11 * 1024 * 1024)
    files = {"file": ("big.pdf", large_data, "application/pdf")}
    
    response = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files=files,
        headers=user_data["headers"]
    )
    assert response.status_code == 413
    assert "exceeds maximum allowed size" in response.json()["detail"]


async def test_get_document_success(client: AsyncClient, db_session: AsyncSession):
    user_data = await create_test_user_and_headers(client, "viewer@example.com")
    org_id = await get_user_organization(db_session, user_data["user_id"])
    
    files = {"file": ("invoice.png", b"PNG dummy data", "image/png")}
    upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files=files,
        headers=user_data["headers"]
    )
    doc_id = upload_res.json()["document_id"]
    
    # Fetch details
    response = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers=user_data["headers"]
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original_filename"] == "invoice.png"
    assert "presigned_url" in data
    # Local Storage client URL format
    assert f"/api/v1/documents/local-file/{org_id}/{doc_id}" in data["presigned_url"]


async def test_get_document_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    # User A uploads a document
    user_a = await create_test_user_and_headers(client, "usera@example.com")
    org_a = await get_user_organization(db_session, user_a["user_id"])
    
    files = {"file": ("usera_invoice.pdf", b"PDF dummy content A", "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_a}",
        files=files,
        headers=user_a["headers"]
    )
    doc_id = upload_res.json()["document_id"]
    
    # User B logs in and tries to fetch User A's document
    user_b = await create_test_user_and_headers(client, "userb@example.com")
    
    response = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers=user_b["headers"]
    )
    # Enforces tenant isolation
    assert response.status_code == 403
    assert "not a member" in response.json()["detail"]


async def test_get_document_extraction_success(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup user and organization
    user_data = await create_test_user_and_headers(client, "extraction_viewer@example.com")
    org_id = await get_user_organization(db_session, user_data["user_id"])
    
    # 2. Generate a valid PDF with specific details
    import fitz
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 50), "Vendor: VLM Consulting Group")
    page.insert_text((50, 100), "Invoice Number: INV-98765-ABC")
    page.insert_text((50, 120), "Subtotal: 2500.00")
    page.insert_text((50, 140), "Tax: 250.00")
    page.insert_text((50, 160), "Total Due: 2750.00")
    file_content = pdf_doc.write()
    pdf_doc.close()
    
    # 3. Upload file
    files = {"file": ("vlm_invoice.pdf", file_content, "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files=files,
        headers=user_data["headers"]
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["document_id"]
    
    # 4. Fetch extraction results
    response = await client.get(
        f"/api/v1/documents/{doc_id}/extraction",
        headers=user_data["headers"]
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    
    # Assert extracted values match the input text layer from the PDF!
    fields = data["extracted_fields"]
    assert fields["invoice_number"] == "INV-98765-ABC"
    assert fields["vendor_name"] == "VLM Consulting Group"
    assert fields["subtotal"] == 2500.0
    assert fields["tax_amount"] == 250.0
    assert fields["total_amount"] == 2750.0
    
    # Assert field confidence exists
    assert data["field_confidence"]["invoice_number"] == 0.95


async def test_get_document_extraction_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    # User A uploads a document
    user_a = await create_test_user_and_headers(client, "usera_ext@example.com")
    org_a = await get_user_organization(db_session, user_a["user_id"])
    
    import fitz
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 50), "Invoice Number: INV-1")
    file_content = pdf_doc.write()
    pdf_doc.close()
    
    files = {"file": ("usera_inv.pdf", file_content, "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_a}",
        files=files,
        headers=user_a["headers"]
    )
    doc_id = upload_res.json()["document_id"]
    
    # User B logs in and tries to fetch User A's extraction results
    user_b = await create_test_user_and_headers(client, "userb_ext@example.com")
    
    response = await client.get(
        f"/api/v1/documents/{doc_id}/extraction",
        headers=user_b["headers"]
    )
    # Enforces tenant isolation on extraction endpoint
    assert response.status_code == 403
    assert "not a member" in response.json()["detail"]


async def test_validation_success_and_high_confidence(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup user and organization
    user_data = await create_test_user_and_headers(client, "val_success@example.com")
    org_id = await get_user_organization(db_session, user_data["user_id"])
    
    # 2. Generate a valid PDF with correct totals: 1000 subtotal + 100 tax = 1100 total
    import fitz
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 50), "Vendor: Acme Corp")
    page.insert_text((50, 100), "Invoice Number: INV-001")
    page.insert_text((50, 120), "Invoice Date: 2026-08-25")
    page.insert_text((50, 140), "Subtotal: 1000.00")
    page.insert_text((50, 160), "Tax: 100.00")
    page.insert_text((50, 180), "Total: 1100.00")
    file_content = pdf_doc.write()
    pdf_doc.close()
    
    # 3. Upload file
    files = {"file": ("val_success.pdf", file_content, "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files=files,
        headers=user_data["headers"]
    )
    doc_id = upload_res.json()["document_id"]
    
    # 4. Fetch validation result
    response = await client.get(
        f"/api/v1/documents/{doc_id}/validation",
        headers=user_data["headers"]
    )
    assert response.status_code == 200
    data = response.json()
    print("VALIDATION ERRORS:", data["validation_errors"])
    assert data["is_valid"] is True
    assert len(data["validation_errors"]) == 0
    
    # 5. Fetch document metadata to verify COMPLETED status (because it passed validations and had high confidence)
    doc_res = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers=user_data["headers"]
    )
    assert doc_res.status_code == 200
    assert doc_res.json()["status"] == "COMPLETED"


async def test_validation_failure_and_review_required(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup user and organization
    user_data = await create_test_user_and_headers(client, "val_failure@example.com")
    org_id = await get_user_organization(db_session, user_data["user_id"])
    
    # 2. Generate a mathematically incorrect PDF: 1000 subtotal + 100 tax != 1500 total
    import fitz
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 50), "Vendor: Acme Corp")
    page.insert_text((50, 100), "Invoice Number: INV-002")
    page.insert_text((50, 120), "Invoice Date: 2026-08-25")
    page.insert_text((50, 140), "Subtotal: 1000.00")
    page.insert_text((50, 160), "Tax: 100.00")
    page.insert_text((50, 180), "Total: 1500.00")
    file_content = pdf_doc.write()
    pdf_doc.close()
    
    # 3. Upload file
    files = {"file": ("val_failure.pdf", file_content, "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files=files,
        headers=user_data["headers"]
    )
    doc_id = upload_res.json()["document_id"]
    
    # 4. Fetch validation result
    response = await client.get(
        f"/api/v1/documents/{doc_id}/validation",
        headers=user_data["headers"]
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert len(data["validation_errors"]) == 1
    assert data["validation_errors"][0]["rule_name"] == "ARITHMETIC_TOTAL_MISMATCH"
    
    # 5. Fetch document metadata to verify status is REVIEW_REQUIRED (due to validation math failure)
    doc_res = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers=user_data["headers"]
    )
    assert doc_res.status_code == 200
    assert doc_res.json()["status"] == "REVIEW_REQUIRED"

    # 6. Fetch extraction to verify confidence ratings were deducted
    ext_res = await client.get(
        f"/api/v1/documents/{doc_id}/extraction",
        headers=user_data["headers"]
    )
    ext_data = ext_res.json()
    # Initial 0.95 - 0.40 arithmetic deduction = 0.55 confidence score for total fields
    assert ext_data["field_confidence"]["total_amount"] == 0.55


async def test_document_human_review_success(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup user and organization
    user_data = await create_test_user_and_headers(client, "reviewer@example.com")
    org_id = await get_user_organization(db_session, user_data["user_id"])
    
    # 2. Generate a mathematically incorrect PDF
    import fitz
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 50), "Vendor: Acme Corp")
    page.insert_text((50, 100), "Invoice Number: INV-101")
    page.insert_text((50, 120), "Invoice Date: 2026-08-25")
    page.insert_text((50, 140), "Subtotal: 1000.00")
    page.insert_text((50, 160), "Tax: 100.00")
    page.insert_text((50, 180), "Total: 1500.00")  # Invalid math!
    file_content = pdf_doc.write()
    pdf_doc.close()
    
    # 3. Upload file ( Celery executes synchronously, transitions to REVIEW_REQUIRED)
    files = {"file": ("invoice_to_review.pdf", file_content, "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files=files,
        headers=user_data["headers"]
    )
    doc_id = upload_res.json()["document_id"]
    
    # Verify status is REVIEW_REQUIRED
    doc_res = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers=user_data["headers"]
    )
    assert doc_res.json()["status"] == "REVIEW_REQUIRED"
    
    # 4. Construct human corrected review submission fields: 1000 subtotal + 100 tax = 1100 total (valid!)
    submission_data = {
        "corrected_fields": {
            "vendor_name": "Acme Corp",
            "vendor_address": "123 Industrial Way, Tech City",
            "invoice_number": "INV-101",
            "invoice_date": "2026-08-25",
            "due_date": "2026-09-25",
            "currency": "USD",
            "subtotal": 1000.00,
            "tax_amount": 100.00,
            "discount_amount": 0.0,
            "total_amount": 1100.00,  # Corrected Grand Total!
            "line_items": []
        }
    }
    
    # 5. POST review corrections
    response = await client.post(
        f"/api/v1/documents/{doc_id}/review",
        json=submission_data,
        headers=user_data["headers"]
    )
    assert response.status_code == 200
    review_res = response.json()
    assert review_res["status"] == "success"
    assert review_res["document_status"] == "COMPLETED"
    assert review_res["is_valid"] is True
    
    # 6. Fetch extraction to verify totals are corrected and confidence is set to 1.0 (human verified)
    ext_res = await client.get(
        f"/api/v1/documents/{doc_id}/extraction",
        headers=user_data["headers"]
    )
    ext_data = ext_res.json()
    assert ext_data["extracted_fields"]["total_amount"] == 1100.0
    assert ext_data["field_confidence"]["total_amount"] == 1.0
    
    # 7. Fetch validation results to verify is_valid is now True
    val_res = await client.get(
        f"/api/v1/documents/{doc_id}/validation",
        headers=user_data["headers"]
    )
    assert val_res.json()["is_valid"] is True
    assert len(val_res.json()["validation_errors"]) == 0
    
    # 8. Check audit_logs and reviews tables programmatically in DB
    from app.models.review import Review
    from app.models.audit_log import AuditLog
    from sqlalchemy.future import select
    
    # Use standard DB execution
    reviews_result = await db_session.execute(
        select(Review).where(Review.document_id == uuid.UUID(doc_id))
    )
    db_review = reviews_result.scalars().first()
    assert db_review is not None
    assert db_review.original_fields["total_amount"] == 1500.0
    assert db_review.corrected_fields["total_amount"] == 1100.0
    assert db_review.status == "COMPLETED"
    
    audits_result = await db_session.execute(
        select(AuditLog).where(AuditLog.entity_id == uuid.UUID(doc_id))
    )
    db_audit = audits_result.scalars().first()
    assert db_audit is not None
    assert db_audit.action == "DOCUMENT_REVIEWED"


async def test_document_human_review_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    # User A uploads a document
    user_a = await create_test_user_and_headers(client, "usera_review@example.com")
    org_a = await get_user_organization(db_session, user_a["user_id"])
    
    import fitz
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 50), "Invoice Number: INV-9")
    file_content = pdf_doc.write()
    pdf_doc.close()
    
    files = {"file": ("usera_inv.pdf", file_content, "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_a}",
        files=files,
        headers=user_a["headers"]
    )
    doc_id = upload_res.json()["document_id"]
    
    # User B logs in and tries to submit review corrections for User A's document
    user_b = await create_test_user_and_headers(client, "userb_review@example.com")
    submission_data = {
        "corrected_fields": {
            "vendor_name": "Acme Corp",
            "invoice_number": "INV-9",
            "subtotal": 100.00,
            "total_amount": 100.00,
            "line_items": []
        }
    }
    
    response = await client.post(
        f"/api/v1/documents/{doc_id}/review",
        json=submission_data,
        headers=user_b["headers"]
    )
    # Enforces strict isolation checks
    assert response.status_code == 403
    assert "not a member" in response.json()["detail"]


async def test_upload_csv_document_success(client: AsyncClient, db_session: AsyncSession):
    # Setup user and organization
    user_data = await create_test_user_and_headers(client, "csv_uploader@example.com")
    org_id = await get_user_organization(db_session, user_data["user_id"])

    csv_content = (
        "vendor,invoice_number,invoice_date,subtotal,tax,discount,total\n"
        "Acme Corp,INV-CSV-100,2026-08-30,1000.00,100.00,50.00,1050.00\n"
    ).encode("utf-8")

    files = {"file": ("dataset_invoice.csv", csv_content, "text/csv")}
    upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files=files,
        headers=user_data["headers"]
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["document_id"]

    # Verify document processing and extraction state
    get_res = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers=user_data["headers"]
    )
    assert get_res.status_code == 200
    doc_data = get_res.json()
    assert doc_data["status"] == "COMPLETED"
    assert doc_data.get("overall_confidence", 1.0) >= 0.85

