import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppProvider, useAppContext } from './context/AppContext';
import { Sidebar } from './components/layout/Sidebar';
import { UploadZone } from './components/upload/UploadZone';
import { QuestionForm } from './components/qa/QuestionForm';
import { AnswerCard } from './components/qa/AnswerCard';
import { ConversationHistory } from './components/history/ConversationHistory';
import { ToastContainer } from './components/ui/Toast';
import { Upload, MessageSquare, History } from 'lucide-react';
import type { QueryResponse } from './types';

const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: 1 } },
});

type Tab = 'upload' | 'ask' | 'history';

function MainContent() {
    const [activeTab, setActiveTab] = useState<Tab>('upload');
    const [latestAnswer, setLatestAnswer] = useState<{ response: QueryResponse; question: string } | null>(null);
    const { conversationHistory, addConversationEntry } = useAppContext();

    function handleAnswer(response: QueryResponse, question: string, docFilter?: string) {
        setLatestAnswer({ response, question });
        addConversationEntry({
            question,
            answer: response.answer,
            source_references: response.source_references,
            confidence_score: response.confidence_score,
            document_filter: docFilter,
        });
        setActiveTab('ask');
    }

    const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
        { id: 'upload', label: 'Upload', icon: <Upload className="w-4 h-4" /> },
        { id: 'ask', label: 'Ask', icon: <MessageSquare className="w-4 h-4" /> },
        { id: 'history', label: `History${conversationHistory.length ? ` (${conversationHistory.length})` : ''}`, icon: <History className="w-4 h-4" /> },
    ];

    return (
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* Page heading */}
            <div className="px-8 pt-8 pb-4">
                <h2 className="text-2xl font-bold text-slate-100">
                    {activeTab === 'upload' && 'Upload Documents'}
                    {activeTab === 'ask' && 'Ask a Question'}
                    {activeTab === 'history' && 'Conversation History'}
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                    {activeTab === 'upload' && 'Add PDF files to build your knowledge base.'}
                    {activeTab === 'ask' && 'Query your documents with natural language.'}
                    {activeTab === 'history' && 'Review past questions and answers.'}
                </p>
            </div>

            {/* Tabs */}
            <div className="px-8 pb-2">
                <div className="flex gap-1 p-1 bg-white/[0.03] border border-white/5 rounded-xl w-fit">
                    {tabs.map((t) => (
                        <button
                            key={t.id}
                            onClick={() => setActiveTab(t.id)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${activeTab === t.id
                                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/25'
                                    : 'text-slate-500 hover:text-slate-300 hover:bg-white/[0.04]'
                                }`}
                        >
                            {t.icon}
                            {t.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-8 py-4">
                {activeTab === 'upload' && (
                    <div className="max-w-2xl">
                        <UploadZone />
                    </div>
                )}

                {activeTab === 'ask' && (
                    <div className="max-w-3xl space-y-5">
                        <div className="glass-card p-5">
                            <QuestionForm onAnswer={handleAnswer} />
                        </div>
                        {latestAnswer && (
                            <AnswerCard response={latestAnswer.response} question={latestAnswer.question} />
                        )}
                    </div>
                )}

                {activeTab === 'history' && (
                    <div className="max-w-3xl">
                        <ConversationHistory entries={conversationHistory} />
                    </div>
                )}
            </div>
        </div>
    );
}

function AppLayout() {
    return (
        <div
            className="flex h-screen overflow-hidden"
            style={{ background: 'linear-gradient(135deg, #0b0e17 0%, #0f172a 50%, #0b0e17 100%)' }}
        >
            {/* Subtle background grid */}
            <div
                className="absolute inset-0 pointer-events-none opacity-[0.03]"
                style={{
                    backgroundImage: `linear-gradient(rgba(99,102,241,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.5) 1px, transparent 1px)`,
                    backgroundSize: '40px 40px',
                }}
            />
            {/* Sidebar */}
            <div className="relative z-10 p-4 border-r border-white/5 overflow-y-auto">
                <Sidebar />
            </div>
            {/* Main */}
            <main className="relative z-10 flex-1 flex flex-col overflow-hidden">
                <MainContent />
            </main>
        </div>
    );
}

export default function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <AppProvider>
                <AppLayout />
                <ToastContainer />
            </AppProvider>
        </QueryClientProvider>
    );
}
