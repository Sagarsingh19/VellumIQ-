"use client";

import React, { useState, useRef, useEffect } from "react";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize, RotateCw } from "lucide-react";
import { documentsService } from "@/services/documents";

interface DocumentViewerProps {
  pages: Array<{
    id: string;
    page_number: number;
    storage_path: string;
    ocr_data?: any;
  }>;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({ pages }) => {
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const activePage = pages[currentPageIndex];

  const handleZoom = (amount: number) => {
    setZoom((prev) => Math.max(50, Math.min(200, prev + amount)));
  };

  const handleRotate = () => {
    setRotation((prev) => (prev + 90) % 360);
  };

  if (!pages || pages.length === 0) {
    return (
      <div className="h-full bg-slate-100 rounded-xl flex items-center justify-center border border-slate-200">
        <p className="text-slate-500 text-sm">No page images found for this document.</p>
      </div>
    );
  }

  // Bounding box mapping details
  const renderOverlays = () => {
    const ocr = activePage.ocr_data;
    if (!ocr || (!ocr.lines && !ocr.words)) return null;

    // Simple heuristic parser for coordinate systems
    const lines = ocr.lines || [];
    const pageWidth = ocr.width || 612;
    const pageHeight = ocr.height || 792;

    return lines.map((line: any, idx: number) => {
      // Bounding box from line baseline x0, y0, x1, y1
      const x0 = line.x0 ?? 0;
      const y0 = line.top ?? 0;
      const x1 = line.x1 ?? 0;
      const y1 = line.bottom ?? 0;

      const leftPercent = (x0 / pageWidth) * 100;
      const topPercent = (y0 / pageHeight) * 100;
      const widthPercent = ((x1 - x0) / pageWidth) * 100;
      const heightPercent = ((y1 - y0) / pageHeight) * 100;

      return (
        <div
          key={`overlay-line-${idx}`}
          className="absolute border border-blue-500/20 bg-blue-500/5 hover:bg-blue-500/20 hover:border-blue-500/50 cursor-pointer rounded transition-all duration-100 group"
          style={{
            left: `${leftPercent}%`,
            top: `${topPercent}%`,
            width: `${widthPercent}%`,
            height: `${heightPercent}%`,
          }}
          title={line.text}
        >
          <span className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-slate-950 text-white text-[10px] font-medium rounded shadow whitespace-nowrap z-50">
            {line.text}
          </span>
        </div>
      );
    });
  };

  return (
    <div className="flex flex-col h-full bg-slate-100 rounded-xl border border-slate-200 overflow-hidden shadow-inner">
      {/* Viewer Toolbar */}
      <div className="bg-white border-b border-slate-200 px-4 py-2 flex items-center justify-between z-10">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPageIndex((p) => Math.max(0, p - 1))}
            disabled={currentPageIndex === 0}
            className="p-1.5 hover:bg-slate-50 text-slate-600 rounded disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs font-semibold text-slate-700">
            Page {currentPageIndex + 1} of {pages.length}
          </span>
          <button
            onClick={() => setCurrentPageIndex((p) => Math.min(pages.length - 1, p + 1))}
            disabled={currentPageIndex === pages.length - 1}
            className="p-1.5 hover:bg-slate-50 text-slate-600 rounded disabled:opacity-40"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => handleZoom(-10)}
            className="p-1.5 hover:bg-slate-50 text-slate-600 rounded"
            title="Zoom Out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="text-[10px] font-mono text-slate-600 w-10 text-center">{zoom}%</span>
          <button
            onClick={() => handleZoom(10)}
            className="p-1.5 hover:bg-slate-50 text-slate-600 rounded"
            title="Zoom In"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <div className="h-4 w-[1px] bg-slate-200 mx-1"></div>
          <button
            onClick={handleRotate}
            className="p-1.5 hover:bg-slate-50 text-slate-600 rounded"
            title="Rotate Page"
          >
            <RotateCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Raster Display Area */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto flex items-center justify-center p-6"
      >
        <div
          className="relative shadow-md bg-white border border-slate-300 transition-all duration-200"
          style={{
            width: `${zoom}%`,
            maxWidth: "800px",
            transform: `rotate(${rotation}deg)`,
          }}
        >
          {/* Raster Image */}
          <img
            ref={imgRef}
            src={documentsService.getPageImageUrl(activePage.storage_path)}
            alt={`Raster page ${currentPageIndex + 1}`}
            className="w-full h-auto select-none pointer-events-none"
          />

          {/* Coordinate Overlays */}
          <div className="absolute inset-0 z-20 pointer-events-auto">
            {renderOverlays()}
          </div>
        </div>
      </div>
    </div>
  );
};
export default DocumentViewer;
