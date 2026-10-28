import { MovieItem, Project, SceneItem, SuggestionCategory } from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api";

export const MEDIA_BASE_URL =
  process.env.NEXT_PUBLIC_MEDIA_URL || "http://localhost:8001";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errMessage = `HTTP Error ${res.status}`;
    try {
      const errData = await res.json();
      if (errData.detail) {
        errMessage = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // Ignore JSON parse error
    }
    throw new Error(errMessage);
  }

  return res.json();
}

// Categories & AI suggestions
export async function fetchCategories(): Promise<SuggestionCategory[]> {
  return request<SuggestionCategory[]>("/suggestions/categories");
}

export async function suggestMovies(category: string, count: number = 3): Promise<MovieItem[]> {
  return request<MovieItem[]>("/suggestions/suggest", {
    method: "POST",
    body: JSON.stringify({ category, count }),
  });
}

export async function searchMovies(query: string, mediaType: string = "movie"): Promise<MovieItem[]> {
  const params = new URLSearchParams({ query, media_type: mediaType });
  return request<MovieItem[]>(`/suggestions/search?${params.toString()}`);
}

export interface MovieFilters {
  query: string; year: string; genre_id: string;
  sort_by: 'popularity.desc' | 'vote_average.desc' | 'primary_release_date.desc';
}
export interface MovieSearchPage { results: MovieItem[]; next_page: number | null; total_results: number | null; sort: string }
export const fetchMovieGenres = () => request<Array<{ id: number; name: string }>>('/suggestions/movie-genres');
export function discoverMovies(filters: MovieFilters, page = 1, signal?: AbortSignal) {
  const params = new URLSearchParams({ page: String(page), sort_by: filters.sort_by });
  if (filters.query.trim()) params.set('query', filters.query.trim());
  if (filters.year) params.set('year', filters.year);
  if (filters.genre_id) params.set('genre_id', filters.genre_id);
  return request<MovieSearchPage>(`/suggestions/discover?${params}`, { signal });
}

// Projects CRUD
export async function fetchProjects(signal?: AbortSignal): Promise<Project[]> {
  return request<Project[]>("/projects", { signal });
}

export async function fetchProject(id: number, signal?: AbortSignal): Promise<Project> {
  return request<Project>(`/projects/${id}`, { signal });
}

export async function createProject(payload: {
  title?: string;
  movies: MovieItem[];
  notes?: string;
  script_text?: string;
  script_data?: any;
}): Promise<Project> {
  return request<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteProject(id: number): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/projects/${id}`, {
    method: "DELETE",
  });
}

// Audience reviews
export async function fetchAudienceReviews(projectId: number): Promise<{ success: boolean; project: Project }> {
  return request<{ success: boolean; project: Project }>(`/projects/${projectId}/reviews`, {
    method: "POST",
  });
}

// Script
export async function generateScript(projectId: number, creatorNotes: string = ""): Promise<{ success: boolean; project: Project }> {
  return request<{ success: boolean; project: Project }>(`/projects/${projectId}/generate-script`, {
    method: "POST",
    body: JSON.stringify({ creator_notes: creatorNotes }),
  });
}

export async function updateScript(projectId: number, scriptText: string, scriptData?: any): Promise<{ success: boolean; project: Project }> {
  return request<{ success: boolean; project: Project }>(`/projects/${projectId}/script`, {
    method: "PUT",
    body: JSON.stringify({ script_text: scriptText, script_data: scriptData }),
  });
}

// Voice
export async function generateVoice(projectId: number, speaker: string = "vipul_hi_social", pace: number = 1.05): Promise<{ success: boolean; project: Project }> {
  return request<{ success: boolean; project: Project }>(`/projects/${projectId}/generate-voice`, {
    method: "POST",
    body: JSON.stringify({ speaker, pace }),
  });
}

export function getVoiceAudioUrl(projectId: number): string {
  return `${API_BASE_URL}/projects/${projectId}/voice-audio?t=${Date.now()}`;
}

// Trailers
export async function downloadTrailer(projectId: number, payload: { youtube_url: string; movie_title?: string; label?: string }): Promise<{ success: boolean; project: Project }> {
  return request<{ success: boolean; project: Project }>(`/projects/${projectId}/download-trailer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function downloadAllTrailers(projectId: number): Promise<{ success: boolean; project: Project; errors?: string[]; downloaded?: any[] }> {
  return request<{ success: boolean; project: Project; errors?: string[]; downloaded?: any[] }>(`/projects/${projectId}/download-all-trailers`, {
    method: "POST",
  });
}

export async function generateAllMotionTeasers(projectId: number): Promise<{ success: boolean; project: Project; errors?: string[]; downloaded?: any[] }> {
  return request<{ success: boolean; project: Project; errors?: string[]; downloaded?: any[] }>(`/projects/${projectId}/generate-all-motion-teasers`, {
    method: "POST",
  });
}

export async function uploadTrailerClip(
  projectId: number,
  file: File,
  movieTitle: string = "",
  label: string = ""
): Promise<{ success: boolean; downloaded: any; project: Project }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("movie_title", movieTitle);
  formData.append("label", label);

  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/upload-clip`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Upload failed (${res.status}): ${errorText}`);
  }
  return res.json();
}

// Gemini Scene Extraction
export async function selectScenes(projectId: number): Promise<{ success: boolean; scenes: SceneItem[]; project: Project }> {
  return request<{ success: boolean; scenes: SceneItem[]; project: Project }>(`/projects/${projectId}/select-scenes`, {
    method: "POST",
  });
}

export async function updateScenes(projectId: number, scenes: SceneItem[]): Promise<{ success: boolean; scenes: SceneItem[]; project: Project }> {
  return request<{ success: boolean; scenes: SceneItem[]; project: Project }>(`/projects/${projectId}/scenes`, {
    method: "PUT",
    body: JSON.stringify({ scenes }),
  });
}

// Thumbnails
export async function generateCollageThumbnail(
  projectId: number,
  payload: { top_text?: string; bottom_text?: string; rating_text?: string; layout?: 'poster_focus' | 'cinema' | 'classic' }
): Promise<{ success: boolean; project: Project }> {
  return request<{ success: boolean; project: Project }>(`/projects/${projectId}/generate-collage`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function setPosterThumbnail(projectId: number, posterUrl: string): Promise<{ success: boolean; project: Project }> {
  return request<{ success: boolean; project: Project }>(`/projects/${projectId}/set-poster-thumbnail`, {
    method: "POST",
    body: JSON.stringify({ poster_url: posterUrl }),
  });
}

export async function updateThumbnailEnding(projectId: number): Promise<{ success: boolean; project: Project }> {
  return request(`/projects/${projectId}/update-thumbnail-ending`, { method: 'POST' });
}

export function getThumbnailImageUrl(projectId: number): string {
  return `${API_BASE_URL}/projects/${projectId}/thumbnail-image?t=${Date.now()}`;
}

// Video Composition
export async function composeVideo(
  projectId: number,
  options?: {
    crop_black_bars?: boolean;
    foreground_zoom?: number;
    foreground_width?: number;
    include_bgm?: boolean;
    bgm_style?: string;
    bgm_volume?: number;
    bgm_ducking?: boolean;
  }
): Promise<{ success: boolean; project: Project; composition?: any }> {
  return request<{ success: boolean; project: Project; composition?: any }>(`/projects/${projectId}/compose-video`, {
    method: "POST",
    body: JSON.stringify(options || {}),
  });
}

export function getVideoStreamUrl(projectId: number): string {
  return `${API_BASE_URL}/projects/${projectId}/video-stream?t=${Date.now()}`;
}

// 1-Click Auto-Pilot End-to-End Pipeline
export interface AutoPilotResult {
  success: boolean;
  project: Project;
  video_path: string;
  thumbnail_path: string;
  voice_path: string;
  script: string;
  youtube_upload?: {
    uploaded?: boolean;
    video_id?: string;
    youtube_url?: string;
    studio_url?: string;
    channel_title?: string;
    state?: string;
    error?: string;
  };
}

export async function triggerAutoPilot(
  projectId: number,
  options?: {
    speaker?: string;
    pace?: number;
    bgm_style?: string;
    pipeline_mode?: string;
    auto_upload?: boolean;
  }
): Promise<AutoPilotResult> {
  return request(`/projects/${projectId}/auto-pilot`, {
    method: "POST",
    body: JSON.stringify(options || {}),
  });
}

export async function quickAutoGenerate(payload: {
  movie_titles?: string[];
  category?: string;
  count?: number;
  speaker?: string;
  pace?: number;
  bgm_style?: string;
  pipeline_mode?: string;
  auto_upload?: boolean;
}): Promise<AutoPilotResult> {
  return request("/projects/quick-auto-generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
