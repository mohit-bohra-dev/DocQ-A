// Core domain types matching the FastAPI backend models

export interface Document {
    document_name: string;
    chunks_count: number;
    uploaded_at?: string;
}

export interface SourceReference {
    document_name: string;
    page_number: number | string;
    chunk_id?: string;
    relevance_score?: number;
    /** Excerpt of the chunk text, returned by the backend for PDF highlighting. */
    content_snippet?: string;
}

export interface QueryResponse {
    answer: string;
    source_references: SourceReference[];
    confidence_score: number;
}

export interface UploadResponse {
    message: string;
    document_id: string;
    chunks_created: number;
}

export interface DocumentListResponse {
    total_documents: number;
    documents: Document[];
}

export interface HealthComponents {
    embedding_service?: string;
    vector_store?: string;
    vector_store_backend?: string;
    documents_indexed?: number;
    llm_service?: string;
    [key: string]: string | number | undefined;
}

export interface HealthStatus {
    status: 'healthy' | 'unhealthy';
    version: string;
    components: HealthComponents;
}

export interface ApiResult<T> {
    success: boolean;
    data?: T;
    error?: string;
    duplicate?: boolean;
}

// UI-layer types
export interface ConversationEntry {
    id: string;
    question: string;
    answer: string;
    source_references: SourceReference[];
    confidence_score: number;
    timestamp: Date;
    document_filter?: string;
}

export type ProcessingStatus = 'idle' | 'uploading' | 'processing' | 'querying' | 'error';

export interface ToastMessage {
    id: string;
    type: 'success' | 'error' | 'info';
    message: string;
}
