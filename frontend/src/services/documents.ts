import api from "./api";
import { Document, ExtractionResult, ValidationResult, InvoiceExtractionSchema } from "@/types";

export const documentsService = {
  async list(orgId: string): Promise<Document[]> {
    const response = await api.get(`/documents?organization_id=${orgId}`);
    return response.data;
  },

  async getDetails(docId: string): Promise<Document> {
    const response = await api.get(`/documents/${docId}`);
    return response.data;
  },

  async getExtraction(docId: string): Promise<ExtractionResult> {
    const response = await api.get(`/documents/${docId}/extraction`);
    return response.data;
  },

  async getValidation(docId: string): Promise<ValidationResult> {
    const response = await api.get(`/documents/${docId}/validation`);
    return response.data;
  },

  async upload(orgId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post(`/documents?organization_id=${orgId}`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  async submitReview(docId: string, correctedFields: InvoiceExtractionSchema): Promise<any> {
    const response = await api.post(`/documents/${docId}/review`, {
      corrected_fields: correctedFields,
    });
    return response.data;
  },
  
  getPageImageUrl(storagePath: string): string {
    return `/api/v1/documents/pages/view?object_name=${encodeURIComponent(storagePath)}`;
  }
};
