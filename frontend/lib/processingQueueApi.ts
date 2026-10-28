import { API_BASE_URL } from './api';
import type { MovieItem } from './types';

export interface QueueItem {
  id: number; movie_key: string; title: string; year?: string; project_id: number | null;
  state: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED'; progress: number; step: string; error?: string;
}
async function request<T>(suffix = '', body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/processing-queue${suffix}`, {
    method: body === undefined ? 'GET' : 'POST', cache: 'no-store',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(20000),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Queue request failed');
  return data;
}
export const fetchQueue = () => request<QueueItem[]>();
export const enqueueMovie = (movie: MovieItem) => request<QueueItem>('', movie);
export const retryQueueItem = (id: number) => request(`/${id}/retry`, {});
export const enqueueExistingProject = (id: number) => request<QueueItem>(`/project/${id}`, {});
