import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { ConversationEntry, ToastMessage } from '../types';
import { v4 as uuidv4 } from '../utils/uuid';

interface AppContextValue {
    conversationHistory: ConversationEntry[];
    addConversationEntry: (entry: Omit<ConversationEntry, 'id' | 'timestamp'>) => void;
    clearHistory: () => void;
    toasts: ToastMessage[];
    addToast: (type: ToastMessage['type'], message: string) => void;
    removeToast: (id: string) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
    const [conversationHistory, setConversationHistory] = useState<ConversationEntry[]>([]);
    const [toasts, setToasts] = useState<ToastMessage[]>([]);

    const addConversationEntry = useCallback(
        (entry: Omit<ConversationEntry, 'id' | 'timestamp'>) => {
            setConversationHistory((prev) => [
                { ...entry, id: uuidv4(), timestamp: new Date() },
                ...prev,
            ]);
        },
        []
    );

    const clearHistory = useCallback(() => setConversationHistory([]), []);

    const addToast = useCallback((type: ToastMessage['type'], message: string) => {
        const id = uuidv4();
        setToasts((prev) => [...prev, { id, type, message }]);
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 4000);
    }, []);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    return (
        <AppContext.Provider
            value={{ conversationHistory, addConversationEntry, clearHistory, toasts, addToast, removeToast }}
        >
            {children}
        </AppContext.Provider>
    );
}

export function useAppContext() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useAppContext must be used within AppProvider');
    return ctx;
}
