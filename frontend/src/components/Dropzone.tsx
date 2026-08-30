"use client";

import React, { useState, useRef } from "react";
import { Upload, FileText, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import { documentsService } from "@/services/documents";

interface DropzoneProps {
  organizationId: string;
  onUploadSuccess: () => void;
}

export const Dropzone: React.FC<DropzoneProps> = ({ organizationId, onUploadSuccess }) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const processFile = async (file: File) => {
    setLoading(true);
    setStatus(null);
    try {
      await documentsService.upload(organizationId, file);
      setStatus({
        type: "success",
        message: `Successfully uploaded ${file.name}! Ingestion processing started.`,
      });
      onUploadSuccess();
    } catch (error: any) {
      console.error(error);
      const errMsg = error.response?.data?.detail || "Failed to upload document.";
      setStatus({
        type: "error",
        message: errMsg,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  return (
    <div className="w-full">
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`w-full py-10 px-6 border-2 border-dashed rounded-xl cursor-pointer transition-colors duration-200 flex flex-col items-center justify-center text-center ${
          isDragActive
            ? "border-blue-500 bg-blue-50/50"
            : "border-slate-300 hover:border-slate-400 bg-slate-50/50"
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInput}
          className="hidden"
          accept=".pdf,.png,.jpg,.jpeg,.csv"
          disabled={loading}
        />
        
        {loading ? (
          <div className="flex flex-col items-center">
            <Loader2 className="h-10 w-10 text-blue-500 animate-spin mb-4" />
            <p className="text-slate-600 font-medium">Uploading and rasterizing page layouts...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="p-3 bg-white rounded-lg shadow-sm border border-slate-100 mb-3 text-slate-500">
              <Upload className="h-6 w-6" />
            </div>
            <p className="text-slate-700 font-semibold mb-1">
              Drag & Drop your invoice file here
            </p>
            <p className="text-slate-500 text-sm mb-2">
              Supports PDF, PNG, JPEG, or CSV formats up to 10MB
            </p>
            <button
              type="button"
              className="px-4 py-2 bg-slate-900 text-white text-xs font-semibold rounded-lg hover:bg-slate-800 transition"
            >
              Browse Files
            </button>
          </div>
        )}
      </div>

      {status && (
        <div
          className={`mt-4 p-4 rounded-xl flex items-start gap-3 border ${
            status.type === "success"
              ? "bg-emerald-50 border-emerald-100 text-emerald-800"
              : "bg-rose-50 border-rose-100 text-rose-800"
          }`}
        >
          {status.type === "success" ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
          )}
          <span className="text-sm font-medium">{status.message}</span>
        </div>
      )}
    </div>
  );
};
export default Dropzone;
