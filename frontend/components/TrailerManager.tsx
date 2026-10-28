"use client";

import React, { useState } from "react";
import { Project, MovieItem, TrailerItem } from "@/lib/types";
import { downloadTrailer, downloadAllTrailers, uploadTrailerClip, generateAllMotionTeasers } from "@/lib/api";
import { Film, Download, CheckCircle2, Loader2, PlayCircle, ExternalLink, Video, Upload, Sparkles } from "lucide-react";

interface TrailerManagerProps {
  project: Project;
  onProjectUpdated: (updated: Project) => void;
}

export function TrailerManager({ project, onProjectUpdated }: TrailerManagerProps) {
  const [downloadingUrl, setDownloadingUrl] = useState<string | null>(null);
  const [isDownloadingAll, setIsDownloadingAll] = useState(false);
  const [isGeneratingTeasers, setIsGeneratingTeasers] = useState(false);
  const [uploadingMovie, setUploadingMovie] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const movies = project.movies_json || [];
  const downloadedVideos = project.source_videos_json || [];

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, movieTitle: string) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingMovie(movieTitle);
    setError(null);
    try {
      const res = await uploadTrailerClip(project.id, file, movieTitle, `${movieTitle} clip`);
      onProjectUpdated(res.project);
    } catch (err: any) {
      setError(err.message || "Failed uploading clip");
    } finally {
      setUploadingMovie(null);
      e.target.value = "";
    }
  };

  const handleGenerateTeasers = async () => {
    setIsGeneratingTeasers(true);
    setError(null);
    try {
      const res = await generateAllMotionTeasers(project.id);
      if (res.project) {
        onProjectUpdated(res.project);
      }
      if (res.errors && res.errors.length > 0 && (!res.downloaded || res.downloaded.length === 0)) {
        setError(res.errors.join("; "));
      }
    } catch (err: any) {
      setError(err.message || "Failed generating cinematic teasers.");
    } finally {
      setIsGeneratingTeasers(false);
    }
  };

  const handleDownloadSingle = async (trailer: TrailerItem, movieTitle: string) => {
    if (!trailer.url) return;
    setDownloadingUrl(trailer.url);
    setError(null);
    try {
      const res = await downloadTrailer(project.id, {
        youtube_url: trailer.url,
        movie_title: movieTitle,
        label: trailer.name || "trailer",
      });
      onProjectUpdated(res.project);
    } catch (err: any) {
      setError(err.message || "Failed downloading trailer.");
    } finally {
      setDownloadingUrl(null);
    }
  };

  const handleDownloadAll = async () => {
    setIsDownloadingAll(true);
    setError(null);
    try {
      const res = await downloadAllTrailers(project.id);
      if (res.project) {
        onProjectUpdated(res.project);
      }
      if (res.errors && res.errors.length > 0 && (!res.downloaded || res.downloaded.length === 0)) {
        setError(`Notice: ${res.errors.join("; ")}`);
      }
    } catch (err: any) {
      setError(err.message || "Failed downloading trailers.");
    } finally {
      setIsDownloadingAll(false);
    }
  };

  return (
    <div className="flex min-w-0 flex-col gap-6 rounded-3xl glass-panel p-4 sm:p-7 shadow-xl">
      {/* Studio Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-white/[0.08]">
        <div className="flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-rose-600 to-amber-500 shadow-lg shadow-rose-950/40">
            <Video className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-black text-white tracking-tight flex items-center gap-2">
              Trailers & Source Video Studio
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              100% Reliable Cloud Motion Teasers or YouTube Downloads for 9:16 Shorts composition.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleGenerateTeasers}
            disabled={isGeneratingTeasers || isDownloadingAll}
            className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-amber-500 via-rose-600 to-pink-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-rose-950/50 hover:scale-[1.02] active:scale-95 disabled:opacity-50 transition"
          >
            {isGeneratingTeasers ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Creating 9:16 Teasers...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>Instant Teasers (100% Reliable)</span>
              </>
            )}
          </button>

          <button
            onClick={handleDownloadAll}
            disabled={isDownloadingAll || isGeneratingTeasers}
            className="flex items-center gap-2 rounded-2xl bg-slate-900 border border-white/10 px-4 py-2.5 text-xs font-bold text-slate-300 hover:bg-slate-800 active:scale-95 disabled:opacity-50 transition"
          >
            {isDownloadingAll ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin text-rose-400" />
                <span>Downloading YouTube...</span>
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                <span>Download up to 3 trailers / movie</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-xs font-semibold text-red-400">
          {error}
        </div>
      )}

      {/* Movies Trailer Deck */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {movies.map((movie, mIdx) => {
          const trailers = movie.trailers || [];
          const isDownloaded = downloadedVideos.some(
            (v) => v.movie_title.toLowerCase() === movie.title.toLowerCase()
          );

          return (
            <div
              key={mIdx}
              className="flex flex-col rounded-3xl bg-slate-950/80 border border-white/[0.08] p-4 gap-3.5 shadow-lg"
            >
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.04]">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="h-12 w-8 rounded-xl bg-slate-800 overflow-hidden shrink-0 shadow">
                    {movie.poster_url && (
                      <img src={movie.poster_url} alt={movie.title} className="h-full w-full object-cover" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <span className="text-[10px] font-bold text-rose-400 uppercase">Slot #{mIdx + 1}</span>
                    <h3 className="text-xs font-black text-white truncate">{movie.title}</h3>
                    <p className="text-[10px] text-slate-400">{movie.year} • ★ {movie.vote_average}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <label className="cursor-pointer flex items-center gap-1.5 text-[10px] font-bold text-slate-300 bg-slate-900 hover:bg-slate-800 px-2.5 py-1 rounded-xl border border-white/[0.08] transition">
                    {uploadingMovie === movie.title ? (
                      <Loader2 className="h-3 w-3 animate-spin text-rose-400" />
                    ) : (
                      <Upload className="h-3 w-3 text-rose-400" />
                    )}
                    <span>{uploadingMovie === movie.title ? "Uploading..." : "Upload Clip"}</span>
                    <input
                      type="file"
                      accept="video/*"
                      disabled={uploadingMovie === movie.title}
                      onChange={(e) => handleFileUpload(e, movie.title)}
                      className="hidden"
                    />
                  </label>

                  {isDownloaded ? (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Ready
                    </span>
                  ) : (
                    <span className="text-[10px] font-semibold text-slate-500 bg-slate-900 px-2 py-0.5 rounded-md">
                      Not Downloaded
                    </span>
                  )}
                </div>
              </div>

              {/* Trailer entries */}
              <div className="flex flex-col gap-2">
                {trailers.length === 0 ? (
                  <div className="p-3 text-center text-xs text-slate-500 bg-slate-900/40 rounded-2xl">
                    No official trailer found on TMDB
                  </div>
                ) : (
                  trailers.slice(0, 3).map((t, tIdx) => {
                    const isBusy = downloadingUrl === t.url;

                    return (
                      <div
                        key={tIdx}
                        className="flex items-center justify-between rounded-2xl bg-slate-900/60 border border-white/[0.04] p-3 text-xs hover:border-white/[0.1] transition"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <PlayCircle className="h-4 w-4 text-rose-500 shrink-0" />
                          <span className="truncate text-slate-200 font-medium text-xs">
                            {t.name || `${movie.title} Trailer`}
                          </span>
                          {t.official && (
                            <span className="rounded-full bg-rose-500/15 px-2 py-0.5 text-[9px] font-black text-rose-400 border border-rose-500/20 shrink-0">
                              Official
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {t.url && (
                            <a
                              href={t.url}
                              target="_blank"
                              rel="noreferrer"
                              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                              title="Watch on YouTube"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                          )}
                          <button
                            onClick={() => handleDownloadSingle(t, movie.title)}
                            disabled={isBusy}
                            className="flex items-center gap-1.5 rounded-xl bg-slate-800 px-3 py-1.5 text-xs font-bold text-slate-200 hover:bg-slate-700 disabled:opacity-50 transition"
                          >
                            {isBusy ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin text-rose-400" />
                            ) : (
                              <Download className="h-3.5 w-3.5" />
                            )}
                            <span>Download</span>
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
