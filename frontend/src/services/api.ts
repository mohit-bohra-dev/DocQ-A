import axios from 'axios';
import type { AxiosInstance } from 'axios';
import type {
    ApiResult,
    DocumentListResponse,
    HealthStatus,
    QueryResponse,
    UploadResponse,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

class ApiClient {
    private client: AxiosInstance;

    constructor() {
        this.client = axios.create({
            baseURL: BASE_URL,
            timeout: 60000,
        });
    }

    async checkHealth(): Promise<ApiResult<HealthStatus>> {
        try {
            const { data } = await this.client.get<HealthStatus>('/health', { timeout: 5000 });
            return { success: true, data };
        } catch (err) {
            return { success: false, error: this.extractError(err) };
        }
    }

    async listDocuments(): Promise<ApiResult<DocumentListResponse>> {
        try {
            const { data } = await this.client.get<DocumentListResponse>('/documents');
            return { success: true, data };
        } catch (err) {
            return { success: false, error: this.extractError(err) };
        }
    }

    async deleteDocument(documentName: string): Promise<ApiResult<{ message: string; chunks_deleted: number }>> {
        try {
            const { data } = await this.client.delete(`/documents/${encodeURIComponent(documentName)}`);
            return { success: true, data };
        } catch (err) {
            return { success: false, error: this.extractError(err) };
        }
    }

    async uploadDocument(
        file: File,
        replaceExisting = false,
        onProgress?: (pct: number) => void
    ): Promise<ApiResult<UploadResponse>> {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('replace_existing', String(replaceExisting));

            const { data } = await this.client.post<UploadResponse>('/upload', formData, {
                timeout: 120000,
                onUploadProgress: (e) => {
                    if (onProgress && e.total) {
                        onProgress(Math.round((e.loaded / e.total) * 100));
                    }
                },
            });
            return { success: true, data };
        } catch (err: any) {
            const status = err.response?.status;
            if (status === 409) {
                return {
                    success: false,
                    error: err.response?.data?.detail ?? 'Document already exists.',
                    duplicate: true,
                };
            }
            return { success: false, error: this.extractError(err) };
        }
    }

    async queryDocuments(
        question: string,
        topK = 5,
        documentName?: string
    ): Promise<ApiResult<QueryResponse>> {
        try {
            const payload: Record<string, unknown> = { question, top_k: topK };
            if (documentName) payload.document_name = documentName;

            const { data } = await this.client.post<QueryResponse>('/query', payload, {
                timeout: 90000,
            });
            return { success: true, data };
        } catch (err) {
            return { success: false, error: this.extractError(err) };
        }
    }

    private extractError(err: unknown): string {
        if (axios.isAxiosError(err)) {
            if (err.code === 'ECONNABORTED') return 'Request timed out. Please try again.';
            if (err.code === 'ERR_NETWORK') return 'Cannot connect to backend. Is the server running?';
            const detail = err.response?.data?.detail;
            if (detail) return typeof detail === 'string' ? detail : JSON.stringify(detail);
            return `HTTP ${err.response?.status ?? 'error'}: ${err.message}`;
        }
        if (err instanceof Error) return err.message;
        return 'An unexpected error occurred.';
    }
}

export const apiClient = new ApiClient();
