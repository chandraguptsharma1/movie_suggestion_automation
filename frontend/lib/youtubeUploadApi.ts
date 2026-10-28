import { API_BASE_URL } from './api';

export interface UploadJob {
  movie_id: number;
  state: string;
  progress: number;
  running: boolean;
  can_resume: boolean;
  video_id?: string;
  title: string;
  channel_title?: string;
  youtube_url?: string;
  studio_url?: string;
  thumbnail_url?: string;
  thumbnail_state: string;
  thumbnail_error?: string;
  thumbnail_updated_at?: string;
  youtube_thumbnail_url?: string;
  uploaded_video_ending_unchanged?: boolean;
  processed?: boolean;
  restriction_detected?: boolean;
  error?: string;
  checked_at?: string;
  publish_at?: string;
  youtube_status?: {
    privacy?: string;
    processing_status?: string;
    upload_status?: string;
    rejection_reason?: string;
    failure_reason?: string;
    region_restriction?: { allowed?: string[]; blocked?: string[] };
  };
}

export interface UploadPreflight {
  ready: boolean;
  warnings: string[];
  media: { duration_seconds: number; width: number; height: number; has_audio: boolean; size_bytes: number };
}

export interface UploadAccount { client_secret_present: boolean; is_authenticated: boolean; channel_title?: string; error?: string }
export interface PublishingAutomation {
  project_id: number; state: string; message: string; next_check: number; updated_at: number;
  evidence?: { copyright_status: string; thumbnail_matches: boolean; observed_at: string } | null;
}
async function automationRequest<T>(id: string | number, payload?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/publishing-automation/${id}`, {
    method: payload === undefined ? 'GET' : 'POST', cache: 'no-store',
    headers: payload === undefined ? {} : { 'Content-Type': 'application/json' },
    body: payload === undefined ? undefined : JSON.stringify(payload), signal: AbortSignal.timeout(20000),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Automatic upload could not be updated');
  return result;
}
export const getPublishingAutomation = (id: string | number) => automationRequest<{ automation: PublishingAutomation | null }>(id);
export const enablePublishingAutomation = (id: string | number, metadata: {
  title: string; description: string; tags: string[]; category_id: string; made_for_kids: boolean;
}) => automationRequest<PublishingAutomation>(id, metadata);
export const getUploadAccount = () => request<UploadAccount>('account');

async function request<T>(id: string | number, suffix = '', body?: unknown): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90000);
  try {
    const response = await fetch(`${API_BASE_URL}/youtube-upload/${id}${suffix}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
      cache: 'no-store',
    });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : JSON.stringify(result.detail || 'YouTube request failed'));
    return result;
  } finally {
    clearTimeout(timeout);
  }
}

export const getUploadJob = (id: string | number) => request<{ job: UploadJob | null }>(id);
export const checkUploadFile = (id: string | number) => request<UploadPreflight>(id, '/preflight');
export const uploadToYouTube = (id: string | number, metadata: {
  title: string; description: string; tags: string[]; category_id: string; made_for_kids: boolean;
}) => request<UploadJob>(id, '', metadata);
export const resumeYouTubeUpload = (id: string | number) => request<UploadJob>(id, '/resume', {});
export const refreshYouTubeChecks = (id: string | number) => request<UploadJob>(id, '/refresh', {});
export const retryYouTubeThumbnail = (id: string | number) => request<UploadJob>(id, '/thumbnail', {});
export interface SchedulePlan {
  publish_at: string; publish_at_ist: string; timezone: string; daily_time: string;
  checked_videos: number; latest_occupied_date: string | null;
}
export const getYouTubeSchedule = (id: string | number) => request<SchedulePlan>(id, '/schedule-preview');
export const publishYouTubeUpload = (id: string | number, body: {
  studio_review_confirmed: boolean; thumbnail_review_confirmed: boolean; publish_at?: string;
}) => request<UploadJob>(id, '/publish', body);

export interface YouTubeMetadata { title: string; description: string; hashtags: string[]; tags: string[]; category: string; scheduledAt: string }
export async function connectYouTube(projectId: string | number) {
  const res = await fetch(`${API_BASE_URL}/youtube/oauth/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project_id: Number(projectId) }) });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'YouTube connect failed');
  return data as { auth_url: string; redirect_uri: string };
}

export async function disconnectYouTube() {
  const response = await fetch(`${API_BASE_URL}/youtube/oauth/disconnect`, { method: 'POST' });
  if (!response.ok) throw new Error('Disconnect failed');
}
