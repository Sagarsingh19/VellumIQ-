from pydantic import BaseModel, Field
from app.schemas.invoice import InvoiceExtractionSchema


class ReviewSubmission(BaseModel):
    corrected_fields: InvoiceExtractionSchema = Field(
        ...,
        description="The corrected invoice fields submitted by the human reviewer.",
    )
