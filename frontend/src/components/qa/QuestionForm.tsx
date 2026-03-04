import { useState } from 'react';
import { Send, ChevronDown } from 'lucide-react';
import { useDocuments } from '../../hooks/useDocuments';
import { apiClient } from '../../services/api';
import { useAppContext } from '../../context/AppContext';
import { Spinner } from '../ui/Spinner';
import type { QueryResponse } from '../../types';

const TOP_K_OPTIONS = [3, 5, 7, 10];
const MAX_CHARS = 1000;

interface QuestionFormProps {
    onAnswer: (answer: QueryResponse, question: string, docFilter?: string) => void;
}

export function QuestionForm({ onAnswer }: QuestionFormProps) {
    const { data: documents } = useDocuments();
    const { addToast } = useAppContext();
    const [question, setQuestion] = useState('');
    const [topK, setTopK] = useState(5);
    const [selectedDoc, setSelectedDoc] = useState('__all__');
    const [isQuerying, setIsQuerying] = useState(false);

    const hasDocuments = (documents?.length ?? 0) > 0;

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!question.trim() || isQuerying) return;

        setIsQuerying(true);
        const docFilter = selectedDoc === '__all__' ? undefined : selectedDoc;

        const result = await apiClient.queryDocuments(question.trim(), topK, docFilter);
        setIsQuerying(false);

        if (result.success && result.data) {
            onAnswer(result.data, question.trim(), docFilter);
            setQuestion('');
        } else {
            addToast('error', result.error ?? 'Query failed.');
        }
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-3">
            {/* Document selector */}
            {hasDocuments && (
                <div className="relative">
                    <select
                        value={selectedDoc}
                        onChange={(e) => setSelectedDoc(e.target.value)}
                        className="w-full appearance-none bg-white/[0.04] border border-white/10 text-slate-300 text-sm rounded-xl px-4 py-2.5 pr-10 focus:outline-none focus:border-indigo-500/60 transition-colors cursor-pointer"
                    >
                        <option value="__all__">🔍 All Documents</option>
                        {documents?.map((doc) => (
                            <option key={doc.document_name} value={doc.document_name}>
                                📄 {doc.document_name}
                            </option>
                        ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                </div>
            )}

            {/* Text area */}
            <div className="relative">
                <textarea
                    value={question}
                    onChange={(e) => setQuestion(e.target.value.slice(0, MAX_CHARS))}
                    disabled={!hasDocuments || isQuerying}
                    placeholder={
                        hasDocuments
                            ? 'Ask a question about your documents…'
                            : 'Upload a document first to start asking questions…'
                    }
                    rows={4}
                    className="w-full bg-white/[0.04] border border-white/10 text-slate-200 text-sm rounded-xl px-4 py-3 placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 transition-colors resize-none disabled:opacity-40 disabled:cursor-not-allowed"
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit(e as any);
                    }}
                />
                <span className="absolute bottom-2.5 right-3 text-[11px] text-slate-600">
                    {question.length}/{MAX_CHARS}
                </span>
            </div>

            {/* Controls row */}
            <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                    <label className="text-xs text-slate-500 whitespace-nowrap">Sources:</label>
                    <div className="flex gap-1">
                        {TOP_K_OPTIONS.map((k) => (
                            <button
                                key={k}
                                type="button"
                                onClick={() => setTopK(k)}
                                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${topK === k
                                        ? 'bg-indigo-500/25 text-indigo-300 border border-indigo-500/40'
                                        : 'bg-white/[0.03] text-slate-500 border border-white/5 hover:border-white/10'
                                    }`}
                            >
                                {k}
                            </button>
                        ))}
                    </div>
                </div>
                <button
                    type="submit"
                    disabled={!hasDocuments || !question.trim() || isQuerying}
                    className="btn-accent ml-auto flex items-center gap-2 px-5 py-2.5"
                >
                    {isQuerying ? (
                        <>
                            <Spinner size="sm" />
                            Searching…
                        </>
                    ) : (
                        <>
                            <Send className="w-4 h-4" />
                            Ask
                        </>
                    )}
                </button>
            </div>
            <p className="text-[11px] text-slate-600">Tip: Press Ctrl+Enter to submit</p>
        </form>
    );
}
