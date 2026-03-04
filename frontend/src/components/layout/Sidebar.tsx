import { useHealth } from '../../hooks/useHealth';
import { useDocuments, useDeleteDocument } from '../../hooks/useDocuments';
import { useAppContext } from '../../context/AppContext';
import { Spinner } from '../ui/Spinner';
import {
    Activity,
    FileText,
    Trash2,
    BookOpen,
    RefreshCw,
    RotateCcw,
    Server,
    Cpu,
    Database,
    Brain,
    Eye,
} from 'lucide-react';
import clsx from 'clsx';

function ComponentIcon({ name }: { name: string }) {
    if (name.includes('embedding')) return <Cpu className="w-3.5 h-3.5" />;
    if (name.includes('vector')) return <Database className="w-3.5 h-3.5" />;
    if (name.includes('llm')) return <Brain className="w-3.5 h-3.5" />;
    if (name.includes('documents')) return <BookOpen className="w-3.5 h-3.5" />;
    return <Server className="w-3.5 h-3.5" />;
}

function cleanDocName(name: string): string {
    if (name.includes('_')) {
        const parts = name.split('_');
        // If the first part looks like a UUID segment, remove it
        if (parts[0].length === 36 || /^[a-f0-9-]{8,}$/i.test(parts[0])) {
            return parts.slice(1).join('_');
        }
    }
    return name;
}

export function Sidebar({ onViewDocument }: { onViewDocument?: (name: string) => void }) {
    const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useHealth();
    const { data: documents, isLoading: docsLoading, refetch: refetchDocs } = useDocuments();
    const deleteMut = useDeleteDocument();
    const { clearHistory, addToast } = useAppContext();

    const isHealthy = health?.status === 'healthy';

    async function handleDelete(docName: string) {
        if (!confirm(`Delete "${cleanDocName(docName)}"? This cannot be undone.`)) return;
        const result = await deleteMut.mutateAsync(docName);
        if (result.success) {
            addToast('success', 'Document deleted successfully.');
        } else {
            addToast('error', result.error ?? 'Failed to delete document.');
        }
    }

    return (
        <aside className="w-72 shrink-0 flex flex-col gap-4 h-full overflow-y-auto pr-1">
            {/* Header */}
            <div className="glass-card p-5">
                <div className="flex items-center gap-3 mb-1">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
                        <BookOpen className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-base font-700 gradient-text leading-tight font-bold">DocQ&A</h1>
                        <p className="text-xs text-slate-500">RAG-powered answers</p>
                    </div>
                </div>
            </div>

            {/* System Status */}
            <div className="glass-card p-4">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-slate-400" />
                        <span className="text-sm font-semibold text-slate-300">System Status</span>
                    </div>
                    <button
                        onClick={() => { refetchHealth(); refetchDocs(); }}
                        className="btn-ghost p-1.5 rounded-lg"
                        title="Refresh status"
                    >
                        <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                </div>

                {healthLoading ? (
                    <div className="flex items-center gap-2 py-2">
                        <Spinner size="sm" />
                        <span className="text-xs text-slate-500">Checking…</span>
                    </div>
                ) : health ? (
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            <span
                                className={clsx(
                                    'pulse-dot w-2 h-2 rounded-full',
                                    isHealthy ? 'bg-emerald-400' : 'bg-red-400'
                                )}
                            />
                            <span
                                className={clsx(
                                    'text-xs font-semibold uppercase tracking-wide',
                                    isHealthy ? 'text-emerald-400' : 'text-red-400'
                                )}
                            >
                                {isHealthy ? 'Online' : 'Degraded'}
                            </span>
                            <span className="ml-auto text-xs text-slate-600">v{health.version}</span>
                        </div>

                        <div className="mt-2 space-y-1.5 pt-2 border-t border-white/5">
                            {Object.entries(health.components).map(([key, val]) => {
                                if (val === undefined) return null;
                                const label = key.replace(/_/g, ' ');
                                const isError = typeof val === 'string' && val.includes('error');
                                const isNum = typeof val === 'number';
                                return (
                                    <div key={key} className="flex items-center gap-2 text-xs">
                                        <ComponentIcon name={key} />
                                        <span className="text-slate-500 capitalize truncate flex-1">{label}</span>
                                        <span
                                            className={clsx(
                                                'font-medium truncate max-w-[100px]',
                                                isError ? 'text-red-400' : isNum ? 'text-indigo-300' : 'text-emerald-400'
                                            )}
                                        >
                                            {isNum ? val : (typeof val === 'string' ? val.replace('ready (', '').replace(')', '') : val)}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ) : (
                    <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-red-400" />
                            <span className="text-xs font-semibold text-red-400 uppercase tracking-wide">Offline</span>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">Backend unavailable. Start the FastAPI server on port 8000.</p>
                    </div>
                )}
            </div>

            {/* Document Library */}
            <div className="glass-card p-4 flex-1">
                <div className="flex items-center gap-2 mb-3">
                    <FileText className="w-4 h-4 text-slate-400" />
                    <span className="text-sm font-semibold text-slate-300">Documents</span>
                    {!docsLoading && documents && (
                        <span className="ml-auto text-xs bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full font-medium">
                            {documents.length}
                        </span>
                    )}
                </div>

                {docsLoading ? (
                    <div className="flex items-center gap-2 py-2">
                        <Spinner size="sm" />
                        <span className="text-xs text-slate-500">Loading…</span>
                    </div>
                ) : documents && documents.length > 0 ? (
                    <ul className="space-y-2">
                        {documents.map((doc) => (
                            <li
                                key={doc.document_name}
                                className="flex items-start gap-2 p-2.5 rounded-lg bg-white/[0.03] border border-white/5 group hover:border-indigo-500/30 transition-colors"
                            >
                                <FileText className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                                <div className="flex-1 min-w-0">
                                    <p className="text-xs font-medium text-slate-300 truncate leading-snug">
                                        {cleanDocName(doc.document_name)}
                                    </p>
                                    <p className="text-[11px] text-slate-600 mt-0.5">{doc.chunks_count} chunks</p>
                                </div>
                                <button
                                    onClick={() => handleDelete(doc.document_name)}
                                    disabled={deleteMut.isPending}
                                    className="btn-ghost p-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:!border-red-500/40 hover:!text-red-400"
                                    title="Delete document"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                                {onViewDocument && (
                                    <button
                                        onClick={() => onViewDocument(doc.document_name)}
                                        className="btn-ghost p-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:!border-indigo-500/40 hover:!text-indigo-400"
                                        title="View PDF"
                                    >
                                        <Eye className="w-3.5 h-3.5" />
                                    </button>
                                )}
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="text-xs text-slate-600 py-2">No documents uploaded yet.</p>
                )}
            </div>

            {/* Actions */}
            <div className="glass-card p-4">
                <button
                    onClick={clearHistory}
                    className="btn-ghost w-full flex items-center justify-center gap-2 py-2 px-3"
                >
                    <RotateCcw className="w-4 h-4" />
                    <span className="text-sm">Clear Chat History</span>
                </button>
            </div>

            {/* About */}
            <div className="glass-card p-4">
                <p className="text-xs text-slate-500 leading-relaxed">
                    <span className="font-semibold text-slate-400">DocQ&A</span> uses{' '}
                    <span className="text-indigo-400">Retrieval-Augmented Generation</span> to answer
                    questions grounded in your uploaded PDF documents.
                </p>
            </div>
        </aside>
    );
}
