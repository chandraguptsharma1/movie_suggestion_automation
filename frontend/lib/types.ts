export interface MovieItem {
  tmdb_id?: number;
  title: string;
  year?: string;
  overview?: string;
  poster_url?: string | null;
  backdrop_url?: string | null;
  vote_average?: number;
  platform?: string;
  media_type?: string;
  genres?: string[];
  slot?: number;
  hook?: string;
  trailers_count?: number;
  trailers?: TrailerItem[];
}

export interface TrailerItem {
  key?: string;
  youtube_id?: string;
  url?: string;
  name?: string;
  type?: string;
  official?: boolean;
  movie_title?: string;
  movie_slot?: number;
}

export interface AudienceReview {
  author: string;
  rating?: number | null;
  snippet: string;
}

export interface ScriptData {
  hook: string;
  movie_spotlights: Array<{
    slot: number;
    title: string;
    duration_sec: number;
    story_premise: string;
    why_to_watch: string;
    script_lines: string;
  }>;
  outro: string;
  full_script: string;
  hinglish_script?: string;
  youtube_title?: string;
  youtube_description?: string;
  tags?: string[];
  hashtags?: string[];
  thumbnail_text?: string;
  bgm_style?: string;
}

export interface Project {
  id: number;
  job_code: string;
  title: string;
  notes?: string;
  movie_count: number;
  movies_json: MovieItem[];
  trailers_json: TrailerItem[];
  audience_reviews_json: Record<string, AudienceReview[]>;
  script_text?: string;
  script_data_json?: ScriptData;
  voice_audio_path?: string;
  voice_data_json?: {
    speaker: string;
    duration_seconds: number;
    chunks_count: number;
    pace: number;
  };
  thumbnail_path?: string;
  thumbnail_data_json?: {
    layout?: 'poster_focus' | 'cinema' | 'classic';
    video_end_card?: { path: string; starts_at_seconds: number; duration_seconds: number };
    top_text?: string;
    bottom_text?: string;
    rating_text?: string;
    width?: number;
    height?: number;
    source_url?: string;
  };
  source_videos_json?: Array<{
    label: string;
    movie_title: string;
    url: string;
    local_path: string;
    movie_slot?: number;
    source_label?: string;
    is_fallback?: boolean;
  }>;
  scenes_json?: SceneItem[];
  final_video_path?: string;
  bgm_data_json?: {
    enabled?: boolean; style?: string; volume?: number; ducking?: boolean;
    custom_path?: string; custom_name?: string; custom_credit?: string;
    label?: string; attribution?: string; license?: string;
  };
  status: string;
  progress_percent: number;
  created_at: string;
  updated_at: string;
}

export interface SceneItem {
  slot: number;
  movie_title: string;
  source_video_path?: string;
  start: string;
  end: string;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
  scene_type: string;
  visual_energy: string;
  reason: string;
  source_label?: string;
  trailer_index?: number;
  selection_method?: string;
  quality_checked?: boolean;
}

export interface SuggestionCategory {
  id: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  default_query: string;
}
