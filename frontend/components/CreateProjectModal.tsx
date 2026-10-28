"use client";

import React, { useState, useEffect } from "react";
import { MovieItem, SuggestionCategory, Project } from "@/lib/types";
import { fetchCategories, suggestMovies, searchMovies, createProject } from "@/lib/api";
import { X, Sparkles, Search, Plus, Trash2, Loader2, Star, Check, Film, Layers, Zap } from "lucide-react";

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (id: number, autoPilot?: boolean, project?: Project) => void;
  initialMovies?: MovieItem[];
}

export function CreateProjectModal({ isOpen, onClose, onProjectCreated, initialMovies }: CreateProjectModalProps) {
  const [categories, setCategories] = useState<SuggestionCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [suggestCount, setSuggestCount] = useState(3);

  // Manual search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<MovieItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Selected movies
  const [selectedMovies, setSelectedMovies] = useState<MovieItem[]>([]);
  const [projectTitle, setProjectTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const movies = initialMovies || [];
    setSelectedMovies(movies);
    setProjectTitle(movies.length === 1 ? `Movie Spotlight: ${movies[0].title}` : movies.length ? `Top ${movies.length}: ${movies.map(movie => movie.title).join(', ')}` : '');
    setNotes(''); setError(null); setSearchResults([]); setSearchQuery('');
  }, [isOpen, initialMovies]);

  useEffect(() => {
    if (isOpen) {
      fetchCategories()
        .then((cats) => {
          setCategories(cats);
          if (cats.length > 0) setSelectedCategory(cats[0].title);
        })
        .catch((err) => console.error("Could not fetch categories", err));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleAutoSuggest = async () => {
    if (!selectedCategory) return;
    setIsSuggesting(true);
    setError(null);
    try {
      const results = await suggestMovies(selectedCategory, suggestCount);
      setSelectedMovies(results);
      if (results.length === 1) {
        setProjectTitle(`Movie Spotlight: ${results[0].title}`);
      } else {
        setProjectTitle(`Top ${results.length}: ${selectedCategory}`);
      }
    } catch (err: any) {
      setError(err.message || "Failed to auto-suggest movies.");
    } finally {
      setIsSuggesting(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    setError(null);
    try {
      const res = await searchMovies(searchQuery);
      setSearchResults(res);
    } catch (err: any) {
      setError(err.message || "Search failed.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddMovie = (movie: MovieItem) => {
    if (selectedMovies.length >= 4) {
      setError("Recommended maximum 4 movies for high-retention 50-60s Shorts.");
      return;
    }
    if (selectedMovies.some((m) => m.title.toLowerCase() === movie.title.toLowerCase())) {
      setError("Movie is already added.");
      return;
    }
    const updated = [...selectedMovies, movie];
    setSelectedMovies(updated);
    if (!projectTitle || projectTitle.startsWith("Top ") || projectTitle.startsWith("Movie Spotlight:")) {
      if (updated.length === 1) {
        setProjectTitle(`Movie Spotlight: ${updated[0].title}`);
      } else {
        setProjectTitle(`Top ${updated.length} Shorts: ${updated.map((m) => m.title).join(", ")}`);
      }
    }
    setError(null);
  };

  const handleRemoveMovie = (index: number) => {
    const updated = selectedMovies.filter((_, i) => i !== index);
    setSelectedMovies(updated);
    if (updated.length > 0 && (!projectTitle || projectTitle.startsWith("Top ") || projectTitle.startsWith("Movie Spotlight:"))) {
      if (updated.length === 1) {
        setProjectTitle(`Movie Spotlight: ${updated[0].title}`);
      } else {
        setProjectTitle(`Top ${updated.length} Shorts: ${updated.map((m) => m.title).join(", ")}`);
      }
    }
  };

  const handleCreate = async (autoPilot: boolean = false) => {
    if (selectedMovies.length < 1) {
      setError("Please select at least 1 movie for your Shorts video.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const project = await createProject({
        title: projectTitle.trim() || undefined,
        movies: selectedMovies,
        notes: notes.trim(),
      });
      onProjectCreated(project.id, autoPilot, project);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to create project.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div role="dialog" aria-modal="true" aria-label="Create Shorts lineup" className="fixed inset-0 z-50 flex items-start justify-center bg-black/85 backdrop-blur-md p-3 sm:p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full min-w-0 max-w-4xl rounded-3xl glass-panel p-4 sm:p-8 my-3 sm:my-8 shadow-2xl border border-white/[0.1] text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between pb-5 border-b border-white/[0.08]">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-rose-500 to-amber-500 shadow-lg shadow-rose-950/50">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-black text-white tracking-tight">Create Shorts Lineup</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Curate 1 to 4 movies for a viral 50-60 second YouTube Shorts review
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close create lineup"
            className="shrink-0 rounded-full p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-2xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-xs font-semibold text-red-400">
            {error}
          </div>
        )}

        {/* Section 1: AI Instant Curation */}
        <div className="mt-6 rounded-2xl bg-slate-900/50 border border-white/[0.06] p-3 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-rose-400">
              <Sparkles className="h-3.5 w-3.5" />
              Option 1: Instant AI Curated Themes
            </span>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>Movies Count:</span>
              {[1, 2, 3, 4].map((cnt) => (
                <button
                  key={cnt}
                  type="button"
                  onClick={() => setSuggestCount(cnt)}
                  className={`h-7 w-7 rounded-lg border text-xs font-extrabold transition ${
                    suggestCount === cnt
                      ? "bg-rose-600 border-rose-500 text-white shadow-md shadow-rose-950/40"
                      : "bg-slate-950/80 border-white/[0.08] text-slate-400 hover:border-white/20"
                  }`}
                >
                  {cnt}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            {categories.map((cat) => {
              const isSelected = selectedCategory === cat.title;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setSelectedCategory(cat.title)}
                  className={`flex min-w-0 flex-col items-start overflow-hidden p-3 rounded-2xl text-left transition border ${
                    isSelected
                      ? "bg-rose-500/15 border-rose-500 text-white shadow-lg shadow-rose-950/30 ring-1 ring-rose-500/50"
                      : "bg-slate-950/60 border-white/[0.06] text-slate-300 hover:border-white/15 hover:bg-slate-900/60"
                  }`}
                >
                  <div className="flex min-w-0 max-w-full items-center gap-2">
                    <span className="text-base">{cat.icon}</span>
                    <span className="min-w-0 text-xs font-bold truncate">{cat.title}</span>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-400 line-clamp-1">{cat.description}</p>
                </button>
              );
            })}
          </div>

          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={handleAutoSuggest}
              disabled={isSuggesting}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-rose-600 via-pink-600 to-amber-500 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-rose-950/50 hover:scale-[1.02] active:scale-95 disabled:opacity-50 transition"
            >
              {isSuggesting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>AI Curating Best Movies...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Auto-Suggest Lineup</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Section 2: Search TMDB manually */}
        <div className="mt-6">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Option 2: Search Movies on TMDB
          </span>
          <form onSubmit={handleSearch} className="mt-2 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search movie title (e.g. Shutter Island, Inception, Prisoners)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-2xl glass-input py-2.5 pl-10 pr-4 text-xs font-medium text-white placeholder-slate-500 focus:outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={isSearching}
              className="rounded-2xl bg-slate-800 px-5 py-2.5 text-xs font-bold text-white hover:bg-slate-700 transition"
            >
              {isSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
            </button>
          </form>

          {searchResults.length > 0 && (
            <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2.5 max-h-48 overflow-y-auto p-1">
              {searchResults.slice(0, 8).map((movie, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 rounded-2xl bg-slate-950/80 border border-white/[0.06] p-2 hover:border-white/15 transition"
                >
                  <div className="h-12 w-9 rounded-lg bg-slate-900 overflow-hidden shrink-0 shadow">
                    {movie.poster_url && (
                      <img src={movie.poster_url} alt={movie.title} className="h-full w-full object-cover" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-slate-200 truncate">{movie.title}</p>
                    <p className="text-[10px] text-slate-400">{movie.year} • ★ {movie.vote_average}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleAddMovie(movie)}
                    className="p-1.5 rounded-xl bg-rose-500/20 text-rose-300 hover:bg-rose-500 hover:text-white transition"
                    title="Add movie"
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Section 3: Selected Movies Deck */}
        <div className="mt-6 border-t border-white/[0.08] pt-5">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <span className="text-sm font-bold text-white flex items-center gap-2">
              <Layers className="h-4 w-4 text-amber-400" />
              Selected Lineup ({selectedMovies.length} of 4)
            </span>
            <span className="text-xs font-medium text-slate-400">
              {selectedMovies.length >= 1 ? "Ready for script generation" : "Select at least 1 movie"}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            {selectedMovies.map((movie, idx) => (
              <div
                key={idx}
                className="group relative flex flex-col rounded-2xl bg-slate-950/90 border border-white/[0.08] p-3 shadow-lg hover:border-rose-500/60 transition"
              >
                <div className="relative aspect-[2/3] w-full rounded-xl bg-slate-900 overflow-hidden shadow">
                  {movie.poster_url ? (
                    <img src={movie.poster_url} alt={movie.title} className="h-full w-full object-cover" />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center text-slate-600 text-xs">
                      No Poster
                    </div>
                  )}
                  <span className="absolute top-2 left-2 rounded-lg bg-black/80 px-2 py-0.5 text-[10px] font-black text-rose-400 border border-white/[0.1]">
                    Slot #{idx + 1}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleRemoveMovie(idx)}
                    className="absolute top-2 right-2 rounded-lg bg-black/80 p-1.5 text-slate-400 hover:text-red-400 transition"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                <h4 className="mt-2.5 text-xs font-bold text-slate-100 line-clamp-1">{movie.title}</h4>
                <p className="text-[10px] text-slate-400 font-medium">{movie.year} • ★ {movie.vote_average}</p>
                {movie.hook && (
                  <p className="mt-1 text-[10px] text-rose-300/80 line-clamp-2 leading-relaxed">
                    {movie.hook}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Project Name and Notes */}
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-bold text-slate-300">Project Title</label>
            <input
              type="text"
              value={projectTitle}
              onChange={(e) => setProjectTitle(e.target.value)}
              placeholder="e.g. Movie Spotlight: Inception or Top 3 Thrillers"
              className="mt-1.5 w-full rounded-2xl glass-input px-3.5 py-2.5 text-xs font-semibold text-white focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-slate-300">Creator Notes (Tone / Angle)</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. High energy, dark suspense, no spoilers..."
              className="mt-1.5 w-full rounded-2xl glass-input px-3.5 py-2.5 text-xs text-white focus:outline-none"
            />
          </div>
        </div>

        {/* Actions Footer */}
        <div className="mt-6 flex flex-wrap items-center justify-end gap-3 border-t border-white/[0.08] pt-5">
          <button
            type="button"
            onClick={onClose}
            className="rounded-2xl px-4 py-2.5 text-xs font-semibold text-slate-400 hover:text-white transition"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => handleCreate(false)}
            disabled={selectedMovies.length < 1 || isSubmitting}
            className="rounded-2xl bg-slate-900 border border-white/[0.1] px-4 py-2.5 text-xs font-bold text-slate-300 hover:bg-slate-800 transition"
          >
            Manual Setup
          </button>
          <button
            type="button"
            onClick={() => handleCreate(true)}
            disabled={selectedMovies.length < 1 || isSubmitting}
            className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-amber-500 via-rose-500 to-pink-500 px-6 py-2.5 text-xs font-black text-white shadow-lg shadow-rose-950/50 hover:scale-[1.02] active:scale-95 disabled:opacity-50 transition glow-rose"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Starting Auto-Pilot...</span>
              </>
            ) : (
              <>
                <Zap className="h-4 w-4 fill-current text-amber-200 animate-pulse" />
                <span>⚡ Auto-Pilot: Create & Generate Short</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
