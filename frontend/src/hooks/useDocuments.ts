import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import type { Document } from '../types';

export function useDocuments() {
    return useQuery<Document[]>({
        queryKey: ['documents'],
        queryFn: async () => {
            const result = await apiClient.listDocuments();
            if (!result.success) throw new Error(result.error);
            return result.data?.documents ?? [];
        },
        staleTime: 10_000,
    });
}

export function useDeleteDocument() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (documentName: string) => apiClient.deleteDocument(documentName),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            queryClient.invalidateQueries({ queryKey: ['health'] });
        },
    });
}
