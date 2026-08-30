export interface User {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  plan_tier: "FREE" | "GROWTH" | "ENTERPRISE";
  monthly_page_limit: number;
  subscription_active: boolean;
}

export interface Membership {
  id: string;
  organization_id: string;
  user_id: string;
  role: string;
  organization?: Organization;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface SignupPayload {
  email: string;
  password: string;
  organization_name: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
  memberships: Membership[];
}

export interface Document {
  id: string;
  organization_id: string;
  original_filename: string;
  status: "UPLOADED" | "OCR_PROCESSING" | "OCR_COMPLETE" | "EXTRACTION_PROCESSING" | "EXTRACTION_COMPLETE" | "VALIDATING" | "REVIEW_REQUIRED" | "COMPLETED" | "FAILED";
  mime_type: string;
  file_size: number;
  page_count: number;
  uploaded_at: string;
  created_at?: string;
  pages?: DocumentPage[];
}

export interface DocumentPage {
  id: string;
  page_number: number;
  storage_path: string;
  ocr_data?: any; // Contains text baseline bounding boxes
}

export interface InvoiceLineItem {
  description: string | null;
  quantity: number | null;
  unit_price: number | null;
  total_amount: number | null;
}

export interface InvoiceExtractionSchema {
  vendor_name: string | null;
  vendor_address: string | null;
  vendor_tax_id: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;
  subtotal: number | null;
  tax_amount: number | null;
  discount_amount: number | null;
  total_amount: number | null;
  payment_terms: string | null;
  bank_details: string | null;
  line_items: InvoiceLineItem[];
}

export interface ExtractionResult {
  document_id: string;
  extracted_fields: InvoiceExtractionSchema;
  field_confidence: Record<string, number>;
  created_at: string;
}

export interface ValidationError {
  rule_id: string;
  severity: "WARNING" | "ERROR";
  message: string;
  field_context: string[];
}

export interface ValidationResult {
  document_id: string;
  is_valid: boolean;
  validation_errors: ValidationError[];
  created_at: string;
}

export interface ApiKey {
  id: string;
  name: string;
  masked_key: string;
  is_active: boolean;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
  raw_key: string;
}
