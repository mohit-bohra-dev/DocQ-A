import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import type { HealthStatus } from '../types';

export function useHealth() {
    return useQuery<HealthStatus | undefined>({
        queryKey: ['health'],
        queryFn: async () => {
            const result = await apiClient.checkHealth();
            if (!result.success) throw new Error(result.error);
            return result.data;
        },
        refetchInterval: 30_000,
        retry: 1,
        staleTime: 15_000,
    });
}
