"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { RefreshCw, FileText, CheckCircle, Clock, AlertTriangle, Play, ChevronRight, Eye } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { documentsService } from "@/services/documents";
import { Document } from "@/types";
import { Dropzone } from "@/components/Dropzone";

export default function DashboardPage() {
  const { activeOrganization } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [pollingActive, setPollingActive] = useState(false);

  const fetchDocuments = useCallback(async (showLoading = false) => {
    if (!activeOrganization) return;
    if (showLoading) setLoading(true);
    try {
      const docs = await documentsService.list(activeOrganization.id);
      setDocuments(docs);

      // Check if any document is in a processing state
      const hasProcessing = docs.some((doc) =>
        ["UPLOADED", "OCR_PROCESSING", "OCR_COMPLETE", "EXTRACTION_PROCESSING", "EXTRACTION_COMPLETE", "VALIDATING"].includes(doc.status)
      );
      setPollingActive(hasProcessing);
    } catch (e) {
      console.error("Failed to fetch documents", e);
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [activeOrganization]);

  useEffect(() => {
    fetchDocuments(true);
  }, [fetchDocuments]);

  // Set up polling if there are documents in processing states
  useEffect(() => {
    if (!pollingActive) return;

    const interval = setInterval(() => {
      fetchDocuments(false);
    }, 4000);

    return () => clearInterval(interval);
  }, [pollingActive, fetchDocuments]);

  // Calculated metrics
  const getTotals = () => {
    const totalCount = documents.length;
    const pendingReviews = documents.filter((d) => d.status === "REVIEW_REQUIRED").length;
    const completedCount = documents.filter((d) => d.status === "COMPLETED").length;
    const totalPagesProcessed = documents.reduce((acc, d) => acc + (d.page_count || 0), 0);

    return { totalCount, pendingReviews, completedCount, totalPagesProcessed };
  };

  const { pendingReviews, completedCount, totalPagesProcessed } = getTotals();

  // Handle status styling
  const renderStatusBadge = (status: Document["status"]) => {
    let color = "bg-slate-100 text-slate-700 border-slate-200";
    if (status === "COMPLETED") {
      color = "bg-emerald-50 text-emerald-700 border-emerald-200";
    } else if (status === "REVIEW_REQUIRED") {
      color = "bg-amber-50 text-amber-700 border-amber-200 animate-pulse";
    } else if (status === "FAILED") {
      color = "bg-rose-50 text-rose-700 border-rose-200";
    } else if (status.endsWith("PROCESSING") || status === "VALIDATING") {
      color = "bg-blue-50 text-blue-700 border-blue-200";
    }

    return (
      <span className={`text-[10px] font-bold border rounded-lg px-2 py-0.5 tracking-wider ${color}`}>
        {status.replace("_", " ")}
      </span>
    );
  };

  // Filters mapping
  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch = doc.original_filename.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || doc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-8">
      {/* Metrics Bar */}
      {activeOrganization && (
        <div className="grid grid-cols-4 gap-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-2">
            <p className="text-slate-400 text-xs font-bold uppercase tracking-wider">Quota Consumed</p>
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-black text-slate-800">{totalPagesProcessed}</span>
              <span className="text-slate-500 text-xs font-bold">/ {activeOrganization.monthly_page_limit} pages</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
              <div
                className="bg-blue-600 h-full rounded-full"
                style={{ width: `${Math.min(100, (totalPagesProcessed / activeOrganization.monthly_page_limit) * 100)}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-1">
            <p className="text-slate-400 text-xs font-bold uppercase tracking-wider">Required Reviews</p>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-black text-amber-600">{pendingReviews}</span>
              {pendingReviews > 0 && (
                <span className="bg-amber-100 text-amber-700 text-[10px] px-1.5 py-0.5 rounded font-black border border-amber-200 animate-bounce">
                  Action Required
                </span>
              )}
            </div>
            <p className="text-slate-500 text-xs font-medium">Documents flagged with math discrepancies</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-1">
            <p className="text-slate-400 text-xs font-bold uppercase tracking-wider">Processed Invoices</p>
            <span className="text-2xl font-black text-slate-800">{completedCount}</span>
            <p className="text-slate-500 text-xs font-medium">Successfully completed and validated</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-1">
            <p className="text-slate-400 text-xs font-bold uppercase tracking-wider">Active Workspace Plan</p>
            <span className="text-2xl font-black text-blue-600 tracking-wide">{activeOrganization.plan_tier}</span>
            <p className="text-slate-500 text-xs font-medium">Billing status active</p>
          </div>
        </div>
      )}

      {/* Upload Zone */}
      {activeOrganization && (
        <section className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <h2 className="text-slate-800 font-bold text-base">Ingest Financial Documents</h2>
          <Dropzone
            organizationId={activeOrganization.id}
            onUploadSuccess={() => fetchDocuments(false)}
          />
        </section>
      )}

      {/* Documents List */}
      <section className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        {/* Toolbar filter */}
        <div className="p-6 border-b border-slate-200 flex items-center justify-between gap-4">
          <h2 className="text-slate-800 font-bold text-base">Ingested Documents</h2>
          
          <div className="flex items-center gap-3">
            {/* Search Input */}
            <input
              type="text"
              placeholder="Search filename..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-blue-500/20 w-48"
            />

            {/* Filter tags */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-blue-500/20 bg-white font-semibold text-slate-600"
            >
              <option value="ALL">All Statuses</option>
              <option value="UPLOADED">Uploaded</option>
              <option value="OCR_PROCESSING">Processing OCR</option>
              <option value="REVIEW_REQUIRED">Review Required</option>
              <option value="COMPLETED">Completed</option>
              <option value="FAILED">Failed</option>
            </select>

            <button
              onClick={() => fetchDocuments(true)}
              className="p-1.5 hover:bg-slate-100 text-slate-500 hover:text-slate-700 rounded-lg border border-slate-200"
              title="Refresh Ingestion States"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Documents Table */}
        {loading ? (
          <div className="py-20 flex flex-col items-center gap-2">
            <RefreshCw className="h-8 w-8 text-blue-500 animate-spin" />
            <p className="text-slate-400 text-xs font-semibold">Loading documents list...</p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="py-20 text-center flex flex-col items-center">
            <FileText className="h-10 w-10 text-slate-300 mb-3" />
            <p className="text-slate-500 font-medium text-sm">No matching documents found.</p>
            <p className="text-slate-400 text-xs mt-0.5">Upload a document layout to start parsing.</p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-xs text-slate-600">
            <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-700">
              <tr>
                <th className="p-4 pl-6">Filename</th>
                <th className="p-4">Status</th>
                <th className="p-4">Pages</th>
                <th className="p-4">File Size</th>
                <th className="p-4">Uploaded At</th>
                <th className="p-4 pr-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredDocuments.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-50/50">
                  <td className="p-4 pl-6 font-semibold text-slate-800 flex items-center gap-2">
                    <FileText className="h-4 w-4 text-slate-400 shrink-0" />
                    <span className="truncate max-w-[200px]" title={doc.original_filename}>
                      {doc.original_filename}
                    </span>
                  </td>
                  <td className="p-4">{renderStatusBadge(doc.status)}</td>
                  <td className="p-4 font-mono font-medium">{doc.page_count || "-"}</td>
                  <td className="p-4 text-slate-500">{(doc.file_size / (1024 * 1024)).toFixed(2)} MB</td>
                  <td className="p-4 text-slate-500">{new Date(doc.uploaded_at).toLocaleString()}</td>
                  <td className="p-4 pr-6 text-right">
                    {doc.status === "REVIEW_REQUIRED" ? (
                      <Link
                        href={`/documents/${doc.id}`}
                        className="inline-flex items-center gap-1 px-3 py-1 bg-amber-600 text-white font-semibold rounded-lg hover:bg-amber-500 transition text-[10px] shadow"
                      >
                        <Play className="h-3 w-3 fill-white" />
                        Audit Review
                      </Link>
                    ) : (
                      <Link
                        href={`/documents/${doc.id}`}
                        className="inline-flex items-center gap-1 px-3 py-1 bg-slate-100 text-slate-700 font-semibold rounded-lg hover:bg-slate-200 transition text-[10px] border border-slate-200"
                      >
                        <Eye className="h-3 w-3" />
                        View
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
