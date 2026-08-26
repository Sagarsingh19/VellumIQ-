"use client";

import React, { useState } from "react";
import { AlertCircle, CheckCircle2, ShieldAlert, Loader2, Plus, Trash2 } from "lucide-react";
import { InvoiceExtractionSchema, ValidationError } from "@/types";
import { documentsService } from "@/services/documents";

interface FieldEditorProps {
  documentId: string;
  initialFields: InvoiceExtractionSchema;
  confidenceScores: Record<string, number>;
  validationErrors: ValidationError[];
  onReviewSubmitted: () => void;
}

export const FieldEditor: React.FC<FieldEditorProps> = ({
  documentId,
  initialFields,
  confidenceScores,
  validationErrors,
  onReviewSubmitted,
}) => {
  const [fields, setFields] = useState<InvoiceExtractionSchema>({ ...initialFields });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleFieldChange = (key: keyof InvoiceExtractionSchema, value: any) => {
    setFields((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleLineItemChange = (idx: number, key: any, value: any) => {
    const updatedItems = [...(fields.line_items || [])];
    updatedItems[idx] = {
      ...updatedItems[idx],
      [key]: value,
    };
    
    // Automatically calculate line item total if quantity and price are present
    if (key === "quantity" || key === "unit_price") {
      const q = Number(updatedItems[idx].quantity || 0);
      const p = Number(updatedItems[idx].unit_price || 0);
      updatedItems[idx].total_amount = Number((q * p).toFixed(2));
    }
    
    setFields((prev) => ({
      ...prev,
      line_items: updatedItems,
    }));
  };

  const addLineItem = () => {
    setFields((prev) => ({
      ...prev,
      line_items: [
        ...(prev.line_items || []),
        { description: "", quantity: 1, unit_price: 0.0, total_amount: 0.0 },
      ],
    }));
  };

  const removeLineItem = (idx: number) => {
    const updatedItems = (fields.line_items || []).filter((_, i) => i !== idx);
    setFields((prev) => ({
      ...prev,
      line_items: updatedItems,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await documentsService.submitReview(documentId, fields);
      onReviewSubmitted();
    } catch (err: any) {
      console.error(err);
      setSubmitError(err.response?.data?.detail || "Failed to submit review corrections.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Helper to color confidence badges
  const renderConfidenceBadge = (fieldName: string) => {
    const score = confidenceScores[fieldName];
    if (score === undefined) return null;
    
    let color = "bg-rose-50 text-rose-700 border-rose-200";
    if (score >= 0.85) color = "bg-emerald-50 text-emerald-700 border-emerald-200";
    else if (score >= 0.60) color = "bg-amber-50 text-amber-700 border-amber-200";

    return (
      <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 border rounded-md ${color}`}>
        {Math.round(score * 100)}%
      </span>
    );
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col h-full bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      {/* Form Header */}
      <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-slate-800 font-bold text-base">Human Verification Panel</h2>
          <p className="text-slate-500 text-xs mt-0.5">Edit highlighted errors and verify values</p>
        </div>
      </div>

      {/* Form Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        
        {/* Render Validation Warnings if any */}
        {validationErrors.length > 0 && (
          <div className="bg-rose-50/50 border border-rose-100 rounded-xl p-4 space-y-2">
            <div className="flex items-center gap-2 text-rose-800 font-semibold text-sm">
              <ShieldAlert className="h-5 w-5 text-rose-600" />
              <span>Failed Validation Rules ({validationErrors.length})</span>
            </div>
            <ul className="list-disc pl-5 text-xs text-rose-700 space-y-1">
              {validationErrors.map((err, idx) => (
                <li key={`val-err-${idx}`}>
                  <strong>{err.rule_id}</strong>: {err.message}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Section 1: Vendor Metadata */}
        <div className="space-y-4">
          <h3 className="text-slate-800 font-bold text-xs uppercase tracking-wider border-b border-slate-100 pb-1">
            Vendor Metadata
          </h3>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">Vendor Name</label>
                {renderConfidenceBadge("vendor_name")}
              </div>
              <input
                type="text"
                value={fields.vendor_name || ""}
                onChange={(e) => handleFieldChange("vendor_name", e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">Vendor Tax ID</label>
                {renderConfidenceBadge("vendor_tax_id")}
              </div>
              <input
                type="text"
                value={fields.vendor_tax_id || ""}
                onChange={(e) => handleFieldChange("vendor_tax_id", e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/20 outline-none"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-700">Vendor Address</label>
              {renderConfidenceBadge("vendor_address")}
            </div>
            <textarea
              value={fields.vendor_address || ""}
              onChange={(e) => handleFieldChange("vendor_address", e.target.value)}
              rows={2}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/20 outline-none resize-none"
            />
          </div>
        </div>

        {/* Section 2: Invoice Details */}
        <div className="space-y-4">
          <h3 className="text-slate-800 font-bold text-xs uppercase tracking-wider border-b border-slate-100 pb-1">
            Invoice Details
          </h3>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">Invoice Number</label>
                {renderConfidenceBadge("invoice_number")}
              </div>
              <input
                type="text"
                value={fields.invoice_number || ""}
                onChange={(e) => handleFieldChange("invoice_number", e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/20 outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">Payment Terms</label>
                {renderConfidenceBadge("payment_terms")}
              </div>
              <input
                type="text"
                value={fields.payment_terms || ""}
                onChange={(e) => handleFieldChange("payment_terms", e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/20 outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">Invoice Date</label>
                {renderConfidenceBadge("invoice_date")}
              </div>
              <input
                type="text"
                placeholder="YYYY-MM-DD"
                value={fields.invoice_date || ""}
                onChange={(e) => handleFieldChange("invoice_date", e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/20 outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">Due Date</label>
                {renderConfidenceBadge("due_date")}
              </div>
              <input
                type="text"
                placeholder="YYYY-MM-DD"
                value={fields.due_date || ""}
                onChange={(e) => handleFieldChange("due_date", e.target.value)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/20 outline-none"
              />
            </div>
          </div>
        </div>

        {/* Section 3: Line Items */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-1">
            <h3 className="text-slate-800 font-bold text-xs uppercase tracking-wider">
              Line Items Table
            </h3>
            <button
              type="button"
              onClick={addLineItem}
              className="text-xs flex items-center gap-1 text-blue-600 font-semibold hover:text-blue-500"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Row
            </button>
          </div>

          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full border-collapse text-left text-xs text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-700">
                <tr>
                  <th className="p-3">Description</th>
                  <th className="p-3 w-16">Qty</th>
                  <th className="p-3 w-24">Price</th>
                  <th className="p-3 w-24">Total</th>
                  <th className="p-3 w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(fields.line_items || []).map((item, idx) => (
                  <tr key={`line-item-${idx}`}>
                    <td className="p-2">
                      <input
                        type="text"
                        value={item.description || ""}
                        onChange={(e) => handleLineItemChange(idx, "description", e.target.value)}
                        className="w-full border border-slate-200 rounded px-2 py-1 outline-none text-xs"
                      />
                    </td>
                    <td className="p-2">
                      <input
                        type="number"
                        value={item.quantity ?? ""}
                        onChange={(e) => handleLineItemChange(idx, "quantity", e.target.value ? Number(e.target.value) : null)}
                        className="w-full border border-slate-200 rounded px-2 py-1 outline-none text-xs"
                      />
                    </td>
                    <td className="p-2">
                      <input
                        type="number"
                        step="0.01"
                        value={item.unit_price ?? ""}
                        onChange={(e) => handleLineItemChange(idx, "unit_price", e.target.value ? Number(e.target.value) : null)}
                        className="w-full border border-slate-200 rounded px-2 py-1 outline-none text-xs"
                      />
                    </td>
                    <td className="p-2">
                      <input
                        type="number"
                        step="0.01"
                        value={item.total_amount ?? ""}
                        onChange={(e) => handleLineItemChange(idx, "total_amount", e.target.value ? Number(e.target.value) : null)}
                        className="w-full border border-slate-200 rounded px-2 py-1 outline-none text-xs bg-slate-50 font-medium"
                      />
                    </td>
                    <td className="p-2 text-center">
                      <button
                        type="button"
                        onClick={() => removeLineItem(idx)}
                        className="p-1 hover:bg-slate-100 text-slate-400 hover:text-rose-600 rounded"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 4: Totals & Summary */}
        <div className="space-y-4">
          <h3 className="text-slate-800 font-bold text-xs uppercase tracking-wider border-b border-slate-100 pb-1">
            Financial Calculations
          </h3>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">Subtotal</label>
                {renderConfidenceBadge("subtotal")}
              </div>
              <input
                type="number"
                step="0.01"
                value={fields.subtotal ?? ""}
                onChange={(e) => handleFieldChange("subtotal", e.target.value ? Number(e.target.value) : null)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/20 outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">Tax Amount</label>
                {renderConfidenceBadge("tax_amount")}
              </div>
              <input
                type="number"
                step="0.01"
                value={fields.tax_amount ?? ""}
                onChange={(e) => handleFieldChange("tax_amount", e.target.value ? Number(e.target.value) : null)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/20 outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">Discount Amount</label>
                {renderConfidenceBadge("discount_amount")}
              </div>
              <input
                type="number"
                step="0.01"
                value={fields.discount_amount ?? ""}
                onChange={(e) => handleFieldChange("discount_amount", e.target.value ? Number(e.target.value) : null)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/20 outline-none"
              />
            </div>

            <div className="space-y-1.5 bg-slate-50 p-2.5 rounded-xl border border-slate-200">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-800">Grand Total Due</label>
                {renderConfidenceBadge("total_amount")}
              </div>
              <input
                type="number"
                step="0.01"
                value={fields.total_amount ?? ""}
                onChange={(e) => handleFieldChange("total_amount", e.target.value ? Number(e.target.value) : null)}
                className="w-full text-sm border border-slate-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-slate-800"
              />
            </div>
          </div>
        </div>

        {/* Section 5: Banking Information */}
        <div className="space-y-4">
          <h3 className="text-slate-800 font-bold text-xs uppercase tracking-wider border-b border-slate-100 pb-1">
            Bank Details
          </h3>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-700">Bank & Routing Numbers</label>
              {renderConfidenceBadge("bank_details")}
            </div>
            <textarea
              value={fields.bank_details || ""}
              onChange={(e) => handleFieldChange("bank_details", e.target.value)}
              rows={2}
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/20 outline-none resize-none"
            />
          </div>
        </div>
      </div>

      {/* Form Action Footer */}
      <div className="bg-slate-50 border-t border-slate-200 px-6 py-4 flex items-center justify-end gap-3 shrink-0">
        {submitError && (
          <p className="text-xs text-rose-600 font-medium mr-auto max-w-[200px] truncate" title={submitError}>
            {submitError}
          </p>
        )}
        <button
          type="button"
          onClick={() => setFields({ ...initialFields })}
          disabled={isSubmitting}
          className="px-4 py-2 border border-slate-300 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-100 disabled:opacity-40 transition"
        >
          Reset Fields
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-500 disabled:opacity-40 flex items-center gap-1.5 transition"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Saving...
            </>
          ) : (
            "Approve & Complete"
          )}
        </button>
      </div>
    </form>
  );
};
export default FieldEditor;
