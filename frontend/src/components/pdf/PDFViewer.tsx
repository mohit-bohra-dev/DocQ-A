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

    /**
     * Pre-compute a Set of "distinctive" words from the snippet.
     * Only words with ≥ 6 characters are kept — this naturally filters out
     * common stop-words (the, with, from, that, this, also, been, …) that
     * caused rampant false-positive highlighting with the old approach.
     */
    const snippetWordSet = useMemo(() => {
        if (!highlightText) return null;
        const tokens = highlightText
            .replace(/\s+/g, ' ')
            .trim()
            .toLowerCase()
            .split(/[^a-z0-9]+/)
            .filter(w => w.length >= 6);
        return tokens.length > 0 ? new Set(tokens) : null;
    }, [highlightText]);

    /**
     * Highlight strategy — two complementary approaches:
     *
     * Approach A (distinctive-word-set matching):
     *   Extract distinctive words (≥ 6 chars) from the snippet into a Set.
     *   A PDF span is highlighted only when a majority (≥ 60 %) of its own
     *   distinctive words appear in the Set.  This avoids the old problem
     *   where every 4-char common word on the page lit up.
     *
     * Approach B (contiguous phrase regex):
     *   pdfjs sometimes groups many words into a single span.  If a leading
     *   segment (first 120 chars) of the snippet appears inside the span
     *   text, highlight just that matching portion.
     *
     * Spans shorter than 4 chars are skipped entirely.
     */
    const customTextRenderer = useCallback(
        ({ str }: { str: string; itemIndex: number }): string => {
            // debugger;
            if (!snippetWordSet || !highlightText || !str) return str;
            const trimmed = str.trim();
            if (trimmed.length < 4) return str;

            // ── Approach A: distinctive-word-set matching ─────────────────
            const spanWords = trimmed
                .toLowerCase()
                .split(/[^a-z0-9]+/)
                .filter(w => w.length >= 6);

            if (spanWords.length > 0) {
                const matchCount = spanWords.filter(w => snippetWordSet.has(w)).length;
                // Require ≥ 60 % AND at least 2 matches to avoid single-word false positives
                // (e.g. "Corruption" appears everywhere in a corruption essay)
                if (matchCount >= 2 && matchCount >= Math.ceil(spanWords.length * 0.6)) {
                    return str.replace(trimmed, `<mark class="pdf-highlight">${trimmed}</mark>`);
                }
            }

            // ── Approach B: contiguous phrase regex ───────────────────────
            const head = highlightText.slice(0, 120).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const headRegex = new RegExp(`(${head})`, 'i');
            if (headRegex.test(str)) {
                return str.replace(headRegex, `<mark class="pdf-highlight">$1</mark>`);
            }

            return str;
        },
        [snippetWordSet, highlightText]
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
