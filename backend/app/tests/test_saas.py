import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.organization import Organization
from app.models.api_key import ApiKey
from app.models.usage_event import UsageEvent
from app.tests.test_documents import create_test_user_and_headers, get_user_organization

pytestmark = pytest.mark.asyncio


async def test_api_keys_crud_and_auth(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup user & organization
    user_data = await create_test_user_and_headers(client, "saas_dev@example.com")
    org_id = await get_user_organization(db_session, user_data["user_id"])

    # 2. Create API Key
    key_payload = {"name": "Production Deploy Key"}
    response = await client.post(
        f"/api/v1/api-keys?organization_id={org_id}",
        json=key_payload,
        headers=user_data["headers"]
    )
    assert response.status_code == 201
    created_data = response.json()
    assert "raw_key" in created_data
    raw_key = created_data["raw_key"]
    assert raw_key.startswith("vq_live_")
    key_id = created_data["id"]

    # 3. List API Keys and verify masking
    list_res = await client.get(
        f"/api/v1/api-keys?organization_id={org_id}",
        headers=user_data["headers"]
    )
    assert list_res.status_code == 200
    keys_list = list_res.json()
    assert len(keys_list) == 1
    assert keys_list[0]["id"] == key_id
    assert keys_list[0]["masked_key"].startswith("vq_live_...")
    assert "raw_key" not in keys_list[0]  # Crucial security check!

    # 4. Upload a document using the generated API Key (Headless authentication)
    import fitz
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 50), "Vendor: Acme Corp")
    page.insert_text((50, 100), "Invoice Number: INV-KEY-1")
    page.insert_text((50, 120), "Invoice Date: 2026-08-25")
    page.insert_text((50, 140), "Subtotal: 100.00")
    page.insert_text((50, 160), "Total: 100.00")
    file_content = pdf_doc.write()
    pdf_doc.close()

    files = {"file": ("api_key_upload.pdf", file_content, "application/pdf")}
    api_key_headers = {"X-API-Key": raw_key}
    
    upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files=files,
        headers=api_key_headers
    )
    assert upload_res.status_code == 202
    assert "document_id" in upload_res.json()

    # 5. Revoke (delete) the API Key
    revoke_res = await client.delete(
        f"/api/v1/api-keys/{key_id}?organization_id={org_id}",
        headers=user_data["headers"]
    )
    assert revoke_res.status_code == 204

    # 6. Try uploading with the revoked key (should return 401)
    failed_upload_res = await client.post(
        f"/api/v1/documents?organization_id={org_id}",
        files={"file": ("failed.pdf", b"pdf data", "application/pdf")},
        headers=api_key_headers
    )
    assert failed_upload_res.status_code == 401
    assert "Invalid or revoked API Key" in failed_upload_res.json()["detail"]


async def test_saas_stripe_webhook_and_page_quotas(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup user & organization
    user_data = await create_test_user_and_headers(client, "saas_stripe@example.com")
    org_uuid = await get_user_organization(db_session, user_data["user_id"])

    # 2. Modify organization limit programmatically to 1 page (representing reached limit)
    result = await db_session.execute(select(Organization).where(Organization.id == org_uuid))
    org = result.scalars().first()
    org.monthly_page_limit = 1
    db_session.add(org)
    await db_session.commit()

    # 3. Generate a valid PDF page
    import fitz
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 50), "Vendor: Acme Corp\nInvoice Number: INV-Q-1\nInvoice Date: 2026-08-25\nSubtotal: 100.0\nTotal: 100.0")
    file_content = pdf_doc.write()
    pdf_doc.close()

    # 4. Upload 1st document (utilizes the 1 remaining page)
    files_1 = {"file": ("invoice1.pdf", file_content, "application/pdf")}
    res_1 = await client.post(
        f"/api/v1/documents?organization_id={org_uuid}",
        files=files_1,
        headers=user_data["headers"]
    )
    assert res_1.status_code == 202

    # 5. Attempt 2nd upload (should fail on 402 - Quota exceeded!)
    files_2 = {"file": ("invoice2.pdf", file_content, "application/pdf")}
    res_2 = await client.post(
        f"/api/v1/documents?organization_id={org_uuid}",
        files=files_2,
        headers=user_data["headers"]
    )
    assert res_2.status_code == 402
    assert "monthly page processing limit reached" in res_2.json()["detail"]

    # 6. Simulate Stripe Webhook Completed Checkout to Upgrade Plan to GROWTH (1000 pages limit)
    webhook_payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_test_growth_1",
                "subscription": "sub_test_growth_1",
                "metadata": {
                    "organization_id": str(org_uuid),
                    "plan_tier": "GROWTH"
                }
            }
        }
    }
    
    webhook_res = await client.post(
        "/api/v1/billing/webhook",
        json=webhook_payload
    )
    assert webhook_res.status_code == 200

    # 7. Attempt 2nd upload again (should now succeed since quota was upgraded to 1000 pages!)
    res_3 = await client.post(
        f"/api/v1/documents?organization_id={org_uuid}",
        files=files_2,
        headers=user_data["headers"]
    )
    assert res_3.status_code == 202
