import { useState } from 'react';
import { ChevronDown, ChevronRight, MessageSquare, Clock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ConversationEntry } from '../../types';
import clsx from 'clsx';

function formatTime(date: Date): string {
    const now = new Date();
    const diff = (now.getTime() - date.getTime()) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
}

function HistoryEntry({ entry, defaultOpen }: { entry: ConversationEntry; defaultOpen: boolean }) {
    const [open, setOpen] = useState(defaultOpen);
    const pct = Math.round(entry.confidence_score * 100);

    return (
        <div className="glass-card overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center gap-3 p-4 text-left hover:bg-white/[0.02] transition-colors"
            >
                <div className="w-8 h-8 rounded-lg bg-indigo-500/15 flex items-center justify-center shrink-0">
                    <MessageSquare className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-300 truncate">
                        {entry.question}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                        <Clock className="w-3 h-3 text-slate-600" />
                        <span className="text-[11px] text-slate-600">{formatTime(entry.timestamp)}</span>
                        {entry.document_filter && (
                            <span className="text-[11px] text-indigo-500">· {entry.document_filter}</span>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    <span className={clsx(
                        'text-[11px] font-semibold px-2 py-0.5 rounded-full',
                        pct >= 75 ? 'text-emerald-400 bg-emerald-500/15' :
                            pct >= 50 ? 'text-amber-400 bg-amber-500/15' :
                                'text-red-400 bg-red-500/15'
                    )}>
                        {pct}%
                    </span>
                    {open
                        ? <ChevronDown className="w-4 h-4 text-slate-500" />
                        : <ChevronRight className="w-4 h-4 text-slate-500" />}
                </div>
            </button>

            {open && (
                <div className="px-4 pb-4 space-y-3 border-t border-white/5">
                    <div className="pt-3 prose-answer">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.answer}</ReactMarkdown>
                    </div>
                    {entry.source_references.length > 0 && (
                        <div className="space-y-1">
                            <p className="text-[11px] uppercase tracking-widest text-slate-600 font-medium">Sources</p>
                            {entry.source_references.map((ref, i) => (
                                <div key={i} className="text-xs text-slate-500 flex items-center gap-2">
                                    <span className="text-indigo-500">📄</span>
                                    <span className="font-medium text-slate-400">{ref.document_name}</span>
                                    <span>· p.{ref.page_number}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export function ConversationHistory({ entries }: { entries: ConversationEntry[] }) {
    if (entries.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-12 text-center opacity-40">
                <MessageSquare className="w-8 h-8 text-slate-600 mb-2" />
                <p className="text-sm text-slate-600">No conversation yet.</p>
                <p className="text-xs text-slate-700 mt-1">Ask a question to get started.</p>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {entries.map((entry, i) => (
                <HistoryEntry key={entry.id} entry={entry} defaultOpen={i === 0} />
            ))}
        </div>
    );
}
