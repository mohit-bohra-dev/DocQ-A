import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import {
    ChevronLeft,
    ChevronRight,
    ZoomIn,
    ZoomOut,
    FileText,
    ExternalLink,
    AlertCircle,
    Loader2,
    Highlighter,
} from 'lucide-react';
import { apiClient } from '../../services/api';

// CDN worker (user-configured)
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export interface PDFViewerProps {
    docName: string | null;
    /** Jump to this page number when set (1-indexed). */
    jumpToPage?: number;
    /** Highlight occurrences of this text string in the rendered text layer. */
    highlightText?: string;
}

const ZOOM_STEPS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0];


export function PDFViewer({ docName, jumpToPage, highlightText }: PDFViewerProps) {
    const [numPages, setNumPages] = useState<number>(0);
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [zoomIndex, setZoomIndex] = useState<number>(2); // default 1.0
    const [loadError, setLoadError] = useState<string | null>(null);
    const scrollAreaRef = useRef<HTMLDivElement>(null);

    const scale = ZOOM_STEPS[zoomIndex];
    const fileUrl = docName ? apiClient.getDocumentFileUrl(docName) : null;

    // Jump to requested page whenever it changes
    useEffect(() => {
        if (jumpToPage && jumpToPage >= 1) {
            setCurrentPage(jumpToPage);
        }
    }, [jumpToPage]);

    // After the page renders, scroll the view back to the top of the canvas
    useEffect(() => {
        scrollAreaRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
    }, [currentPage]);

    const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
        setNumPages(numPages);
        setCurrentPage(jumpToPage && jumpToPage >= 1 ? jumpToPage : 1);
        setLoadError(null);
    }, [jumpToPage]);

    const onDocumentLoadError = useCallback((error: Error) => {
        setLoadError(
            error.message.includes('404') || error.message.includes('not found')
                ? 'This document was uploaded before the PDF viewer feature was enabled. Please re-upload it to view it here.'
                : `Failed to load PDF: ${error.message}`
        );
    }, []);

    /** Pre-process the snippet once: normalise whitespace, lowercase. */
    const normalSnippet = useMemo(() => {
        if (!highlightText) return null;
        return highlightText.replace(/\s+/g, ' ').trim().toLowerCase();
    }, [highlightText]);

    /**
     * Highlight strategy — tries BOTH approaches so neither is lost:
     *
     * Approach A (token-in-snippet / containment):
     *   PDF text-layer tokens are usually 1-5 words. If the token appears as
     *   a substring of the backend chunk excerpt it almost certainly belongs to
     *   the cited passage → highlight it.
     *
     * Approach B (snippet-in-token / direct-regex):
     *   pdfjs sometimes groups several words into a single span. If the entire
     *   highlightText (or a long portion of it) appears inside the token string,
     *   we can do a regex replace to highlight just the matching part.
     *
     * Tokens shorter than 4 chars are skipped to avoid stop-word noise.
     * The return value is used as innerHTML by react-pdf, so raw HTML is safe.
     */
    const customTextRenderer = useCallback(
        ({ str }: { str: string; itemIndex: number }): string => {
            if (!normalSnippet || !highlightText || !str) return str;
            const trimmed = str.trim();
            if (trimmed.length < 4) return str;

            const normStr = trimmed.replace(/\s+/g, ' ').toLowerCase();

            // ── Approach A: token is a substring of the snippet ──────────────
            if (normalSnippet.includes(normStr)) {
                return str.replace(trimmed, `<mark class="pdf-highlight">${trimmed}</mark>`);
            }

            // ── Approach B: snippet phrase appears inside the token ───────────
            // Build a simple escaped regex from the first 60 chars of the snippet
            // (enough to be distinctive, short enough to avoid excessive backtracking)
            const head = highlightText.slice(0, 60).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const headRegex = new RegExp(`(${head})`, 'i');
            if (headRegex.test(str)) {
                return str.replace(headRegex, `<mark class="pdf-highlight">$1</mark>`);
            }

            return str;
        },
        [normalSnippet, highlightText]
    );

    function prevPage() {
        setCurrentPage((p) => Math.max(1, p - 1));
    }

    function nextPage() {
        setCurrentPage((p) => Math.min(numPages, p + 1));
    }

    function zoomIn() {
        setZoomIndex((i) => Math.min(ZOOM_STEPS.length - 1, i + 1));
    }

    function zoomOut() {
        setZoomIndex((i) => Math.max(0, i - 1));
    }

    // Empty state
    if (!docName || !fileUrl) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-600">
                <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center justify-center">
                    <FileText className="w-8 h-8" />
                </div>
                <div className="text-center">
                    <p className="text-sm font-medium text-slate-500">No document selected</p>
                    <p className="text-xs mt-1">Click the eye icon next to a document in the sidebar, or a citation source in an answer.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full gap-3">
            {/* Toolbar */}
            <div className="glass-card px-4 py-2.5 flex items-center gap-3 shrink-0 flex-wrap">
                {/* Document name */}
                <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                <span className="text-sm font-medium text-slate-300 truncate flex-1 min-w-0">{docName}</span>

                {/* Active highlight badge */}
                {highlightText && (
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs shrink-0">
                        <Highlighter className="w-3 h-3" />
                        <span className="truncate max-w-[120px]">"{highlightText}"</span>
                    </div>
                )}

                {/* Page controls */}
                {numPages > 0 && (
                    <div className="flex items-center gap-1.5 shrink-0">
                        <button
                            onClick={prevPage}
                            disabled={currentPage <= 1}
                            className="btn-ghost p-1.5 rounded-lg disabled:opacity-30"
                            title="Previous page"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <span className="text-xs text-slate-400 tabular-nums w-20 text-center">
                            {currentPage} / {numPages}
                        </span>
                        <button
                            onClick={nextPage}
                            disabled={currentPage >= numPages}
                            className="btn-ghost p-1.5 rounded-lg disabled:opacity-30"
                            title="Next page"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                )}

                <div className="w-px h-5 bg-white/10 shrink-0" />

                {/* Zoom controls */}
                <div className="flex items-center gap-1.5 shrink-0">
                    <button
                        onClick={zoomOut}
                        disabled={zoomIndex <= 0}
                        className="btn-ghost p-1.5 rounded-lg disabled:opacity-30"
                        title="Zoom out"
                    >
                        <ZoomOut className="w-4 h-4" />
                    </button>
                    <span className="text-xs text-slate-500 tabular-nums w-12 text-center">
                        {Math.round(scale * 100)}%
                    </span>
                    <button
                        onClick={zoomIn}
                        disabled={zoomIndex >= ZOOM_STEPS.length - 1}
                        className="btn-ghost p-1.5 rounded-lg disabled:opacity-30"
                        title="Zoom in"
                    >
                        <ZoomIn className="w-4 h-4" />
                    </button>
                </div>

                <div className="w-px h-5 bg-white/10 shrink-0" />

                {/* External link */}
                <a
                    href={fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-ghost p-1.5 rounded-lg"
                    title="Open in new tab"
                >
                    <ExternalLink className="w-4 h-4" />
                </a>
            </div>

            {/* PDF canvas area */}
            <div ref={scrollAreaRef} className="flex-1 overflow-auto pdf-scroll-area flex justify-center">
                {loadError ? (
                    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center max-w-sm mx-auto">
                        <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center">
                            <AlertCircle className="w-6 h-6 text-red-400" />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-red-400 mb-1">Could not load PDF</p>
                            <p className="text-xs text-slate-500 leading-relaxed">{loadError}</p>
                        </div>
                        <a
                            href={fileUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn-ghost px-3 py-1.5 rounded-lg text-xs flex items-center gap-1.5"
                        >
                            <ExternalLink className="w-3.5 h-3.5" />
                            Try opening directly
                        </a>
                    </div>
                ) : (
                    <Document
                        file={fileUrl}
                        onLoadSuccess={onDocumentLoadSuccess}
                        onLoadError={onDocumentLoadError}
                        loading={
                            <div className="flex flex-col items-center justify-center gap-3 py-24">
                                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                                <p className="text-sm text-slate-500">Loading document…</p>
                            </div>
                        }
                        className="pdf-document"
                    >
                        <Page
                            pageNumber={currentPage}
                            scale={scale}
                            className="pdf-page"
                            loading={
                                <div className="flex items-center justify-center py-8">
                                    <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                                </div>
                            }
                            customTextRenderer={highlightText ? customTextRenderer : undefined}
                            renderAnnotationLayer
                            renderTextLayer
                        />
                    </Document>
                )}
            </div>

            {/* Page indicator strip */}
            {numPages > 0 && (
                <div className="shrink-0 flex items-center justify-center gap-2 py-1">
                    <button
                        onClick={prevPage}
                        disabled={currentPage <= 1}
                        className="btn-accent px-3 py-1.5 rounded-lg text-xs flex items-center gap-1 disabled:opacity-30"
                    >
                        <ChevronLeft className="w-3.5 h-3.5" /> Prev
                    </button>
                    <span className="text-xs text-slate-500 tabular-nums">
                        Page {currentPage} of {numPages}
                    </span>
                    <button
                        onClick={nextPage}
                        disabled={currentPage >= numPages}
                        className="btn-accent px-3 py-1.5 rounded-lg text-xs flex items-center gap-1 disabled:opacity-30"
                    >
                        Next <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                </div>
            )}
        </div>
    );
}
