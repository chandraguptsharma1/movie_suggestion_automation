from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class MovieItem(BaseModel):
    tmdb_id: Optional[int] = None
    title: str
    year: Optional[str] = ""
    overview: Optional[str] = ""
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    vote_average: Optional[float] = None
    platform: Optional[str] = "OTT"
    media_type: Optional[str] = "movie"
    genres: Optional[List[str]] = Field(default_factory=list)
    slot: Optional[int] = None
    trailers_count: Optional[int] = 0
    trailers: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class CreateProjectRequest(BaseModel):
    title: Optional[str] = None
    movies: List[MovieItem] = Field(..., min_length=1, max_length=7)
    notes: Optional[str] = ""
    script_text: Optional[str] = ""
    script_data: Optional[Dict[str, Any]] = None


class GenerateScriptRequest(BaseModel):
    creator_notes: Optional[str] = ""


class UpdateScriptRequest(BaseModel):
    script_text: str
    script_data: Optional[Dict[str, Any]] = None


class GenerateVoiceRequest(BaseModel):
    speaker: Optional[str] = "vipul_hi_social"
    pace: Optional[float] = 1.05


class DownloadTrailerRequest(BaseModel):
    youtube_url: str
    movie_title: Optional[str] = ""
    label: Optional[str] = ""


class GenerateCollageRequest(BaseModel):
    layout: Literal['poster_focus', 'cinema', 'classic'] = 'poster_focus'
    top_text: Optional[str] = "SUPER ADDICTIVE"
    bottom_text: Optional[str] = "MASTERPIECES!"
    rating_text: Optional[str] = "8.4/10"


class SuggestMoviesRequest(BaseModel):
    category: str
    count: Optional[int] = Field(default=3, ge=1, le=7)
