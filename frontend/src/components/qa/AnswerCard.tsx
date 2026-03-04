import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText, BarChart2, BookOpen } from 'lucide-react';
import type { QueryResponse } from '../../types';
import clsx from 'clsx';

interface AnswerCardProps {
    response: QueryResponse;
    question: string;
}

function confidenceColor(score: number): string {
    if (score >= 0.75) return 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30';
    if (score >= 0.5) return 'text-amber-400 bg-amber-500/15 border-amber-500/30';
    return 'text-red-400 bg-red-500/15 border-red-500/30';
}

function cleanDocName(name: string): string {
    if (name.includes('_')) {
        const parts = name.split('_');
        if (/^[a-f0-9-]{8,}$/i.test(parts[0])) return parts.slice(1).join('_');
    }
    return name;
}

export function AnswerCard({ response, question }: AnswerCardProps) {
    const { answer, source_references, confidence_score } = response;
    const pct = Math.round(confidence_score * 100);

    return (
        <div className="glass-card p-5 fade-in-up space-y-4 border-indigo-500/20">
            {/* Question echo */}
            <div>
                <p className="text-[11px] uppercase tracking-widest text-slate-600 mb-1 font-medium">Question</p>
                <p className="text-sm text-slate-400 italic">"{question}"</p>
            </div>

            <div className="border-t border-white/5" />

            {/* Answer */}
            <div>
                <p className="text-[11px] uppercase tracking-widest text-slate-600 mb-2 font-medium flex items-center gap-1.5">
                    <BookOpen className="w-3 h-3" /> Answer
                </p>
                <div className="prose-answer">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
                </div>
            </div>

            {/* Metrics */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
                {/* Confidence */}
                <div className={clsx('flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium', confidenceColor(confidence_score))}>
                    <BarChart2 className="w-3.5 h-3.5" />
                    <span>Confidence {pct}%</span>
                </div>

                {/* Source count */}
                {source_references.length > 0 && (
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-xs font-medium">
                        <FileText className="w-3.5 h-3.5" />
                        <span>{source_references.length} source{source_references.length !== 1 ? 's' : ''}</span>
                    </div>
                )}
            </div>

            {/* Sources */}
            {source_references.length > 0 && (
                <div className="space-y-2">
                    <p className="text-[11px] uppercase tracking-widest text-slate-600 font-medium flex items-center gap-1.5">
                        <FileText className="w-3 h-3" /> Sources
                    </p>
                    <div className="space-y-1.5">
                        {source_references.map((ref, i) => (
                            <div
                                key={i}
                                className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/5 text-xs"
                            >
                                <div className="w-5 h-5 rounded-md bg-indigo-500/20 flex items-center justify-center shrink-0">
                                    <span className="text-[10px] font-bold text-indigo-400">{i + 1}</span>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-slate-300 font-medium truncate">{cleanDocName(ref.document_name)}</p>
                                    <p className="text-slate-600">Page {ref.page_number}</p>
                                </div>
                                {ref.relevance_score !== undefined && (
                                    <span className="text-slate-600 shrink-0">{(ref.relevance_score * 100).toFixed(0)}%</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
