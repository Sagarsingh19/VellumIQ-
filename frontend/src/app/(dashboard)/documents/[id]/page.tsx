"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, Loader2, ShieldAlert, CheckCircle2, FileText, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { documentsService } from "@/services/documents";
import { Document, ExtractionResult, ValidationResult } from "@/types";
import { DocumentViewer } from "@/components/DocumentViewer";
import { FieldEditor } from "@/components/FieldEditor";

export default function DocumentDetailsPage() {
  const router = useRouter();
  const params = useParams();
  const docId = params.id as string;

  const [document, setDocument] = useState<Document | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDocumentData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch document base metadata
      const doc = await documentsService.getDetails(docId);
      setDocument(doc);

      // 2. Fetch OCR page layers and VLM extraction results (if available yet)
      if (["EXTRACTION_COMPLETE", "VALIDATING", "REVIEW_REQUIRED", "COMPLETED"].includes(doc.status)) {
        const [extData, valData] = await Promise.all([
          documentsService.getExtraction(docId).catch(() => null),
          documentsService.getValidation(docId).catch(() => null),
        ]);
        setExtraction(extData);
        setValidation(valData);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "Failed to load document information.");
    } finally {
      setLoading(false);
    }
  }, [docId]);

  useEffect(() => {
    loadDocumentData();
  }, [loadDocumentData]);

  const handleReviewSuccess = () => {
    // Reload data and show completion
    loadDocumentData();
  };

  if (loading) {
    return (
      <div className="h-[80vh] flex flex-col items-center justify-center gap-3">
        <Loader2 className="h-10 w-10 text-blue-500 animate-spin" />
        <p className="text-slate-500 text-sm font-semibold">Retrieving document OCR & Extraction overlays...</p>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="max-w-xl mx-auto mt-20 bg-white border border-slate-200 rounded-2xl p-8 text-center space-y-4 shadow-sm">
        <AlertTriangle className="h-12 w-12 text-rose-500 mx-auto" />
        <h2 className="text-slate-800 font-extrabold text-lg">Failed to load document details</h2>
        <p className="text-slate-500 text-sm">{error || "Document not found."}</p>
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-500"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
      </div>
    );
  }

  // Renders state when document is still processing in background Celery queues
  if (["UPLOADED", "OCR_PROCESSING", "OCR_COMPLETE", "EXTRACTION_PROCESSING"].includes(document.status)) {
    return (
      <div className="max-w-xl mx-auto mt-20 bg-white border border-slate-200 rounded-2xl p-8 text-center space-y-4 shadow-sm">
        <Loader2 className="h-12 w-12 text-blue-500 animate-spin mx-auto" />
        <h2 className="text-slate-800 font-extrabold text-lg">Extraction in Progress</h2>
        <p className="text-slate-500 text-sm">
          VellumIQ is currently running OCR, converting layouts, and parsing fields with Gemini VLMs.
        </p>
        <p className="text-slate-400 text-xs font-medium bg-slate-50 border border-slate-100 py-2 rounded-lg">
          Status: <strong className="text-blue-600">{document.status.replace("_", " ")}</strong>
        </p>
        <button
          onClick={loadDocumentData}
          className="px-4 py-2 bg-slate-900 text-white font-semibold rounded-lg hover:bg-slate-800 text-xs transition"
        >
          Refresh Status
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 h-[88vh] flex flex-col">
      {/* Header breadcrumb */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-2 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-600 shadow-sm"
          >
            <ArrowLeft className="h-4.5 w-4.5" />
          </Link>
          <div>
            <h2 className="text-slate-800 font-extrabold text-lg flex items-center gap-2">
              <FileText className="h-5 w-5 text-slate-400" />
              {document.original_filename}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Status: <span className="font-bold text-slate-700">{document.status}</span>
            </p>
          </div>
        </div>

        {document.status === "COMPLETED" && (
          <div className="bg-emerald-50 border border-emerald-100 rounded-xl px-4 py-2 flex items-center gap-2 text-emerald-800 text-xs font-semibold shadow-sm">
            <CheckCircle2 className="h-4.5 w-4.5 text-emerald-600" />
            <span>Document Approved & Completed</span>
          </div>
        )}
      </div>

      {/* Side-by-Side Review Grid */}
      <div className="grid grid-cols-2 gap-6 flex-1 min-h-0 overflow-hidden">
        {/* Left Side: Raster Canvas */}
        <div className="h-full overflow-hidden">
          <DocumentViewer pages={document.pages || []} />
        </div>

        {/* Right Side: Form Editor */}
        <div className="h-full overflow-hidden">
          {document.status === "COMPLETED" ? (
            <div className="h-full bg-white border border-slate-200 rounded-xl p-8 text-center flex flex-col justify-center items-center gap-4">
              <CheckCircle2 className="h-12 w-12 text-emerald-500" />
              <h3 className="text-slate-800 font-extrabold text-base">Human Verification Done</h3>
              <p className="text-slate-500 text-sm max-w-sm">
                This document's fields have been successfully verified and saved. Field confidence metrics are reset to 100%.
              </p>
              <div className="w-full text-left text-xs bg-slate-50 p-4 border rounded-lg space-y-1 max-h-[250px] overflow-auto">
                <p className="font-bold text-slate-700 uppercase tracking-wider mb-2">Verified Output JSON</p>
                <pre className="font-mono text-[10px] text-slate-600">
                  {JSON.stringify(extraction?.extracted_fields, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <FieldEditor
              documentId={document.id}
              initialFields={extraction?.extracted_fields || {
                vendor_name: "", vendor_address: "", vendor_tax_id: "",
                invoice_number: "", invoice_date: "", due_date: "",
                subtotal: 0, tax_amount: 0, discount_amount: 0, total_amount: 0,
                payment_terms: "", bank_details: "", line_items: []
              }}
              confidenceScores={extraction?.field_confidence || {}}
              validationErrors={validation?.validation_errors || []}
              onReviewSubmitted={handleReviewSuccess}
            />
          )}
        </div>
      </div>
    </div>
  );
}
