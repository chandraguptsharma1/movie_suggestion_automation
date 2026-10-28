"use client";

import React, { useState, useEffect } from "react";
import { Project, SceneItem } from "@/lib/types";
import { API_BASE_URL, selectScenes, updateScenes } from "@/lib/api";
import {
  Sparkles,
  Clapperboard,
  Scissors,
  Clock,
  Trash2,
  Plus,
  Save,
  CheckCircle2,
  AlertCircle,
  Play,
  Film,
  Zap,
  Info,
} from "lucide-react";

interface SceneSelectorProps {
  project: Project;
  onProjectUpdated: (project: Project) => void;
}

export function SceneSelector({ project, onProjectUpdated }: SceneSelectorProps) {
  const [scenes, setScenes] = useState<SceneItem[]>(project.scenes_json || []);
  const [isSelecting, setIsSelecting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [previewScene, setPreviewScene] = useState<number | null>(null);

  useEffect(() => {
    setScenes(project.scenes_json || []);
  }, [project.scenes_json]);

  const movies = project.movies_json || [];
  const sourceVideos = project.source_videos_json || [];
  const hasTrailers = sourceVideos.length > 0;

  const handleSelectScenes = async () => {
    try {
      setIsSelecting(true);
      setError(null);
      setSuccessMsg(null);
      const res = await selectScenes(project.id);
      if (res.success) {
        setScenes(res.scenes);
        onProjectUpdated(res.project);
        setSuccessMsg(`Selected ${res.scenes.length} scenes from ${new Set(res.scenes.map(s => s.source_video_path)).size} trailers.`);
      }
    } catch (err: any) {
      setError(err.message || "Failed to select scenes with Gemini.");
    } finally {
      setIsSelecting(false);
    }
  };

  const handleSaveScenes = async () => {
    try {
      setIsSaving(true);
      setError(null);
      setSuccessMsg(null);
      const res = await updateScenes(project.id, scenes);
      if (res.success) {
        onProjectUpdated(res.project);
        setSuccessMsg("Scene timeline changes saved successfully!");
      }
    } catch (err: any) {
      setError(err.message || "Failed to save scene changes.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateScene = (index: number, field: keyof SceneItem, value: any) => {
    setScenes((prev) => {
      const next = [...prev];
      const target = { ...next[index], [field]: value };
      if (field === "source_video_path") {
        target.selection_method = "manual";
        target.quality_checked = false;
        target.source_label = sourceVideos.find(v => v.local_path === value)?.source_label;
      }

      if (field === "start_seconds" || field === "end_seconds") {
        const st = field === "start_seconds" ? Number(value) : target.start_seconds;
        const en = field === "end_seconds" ? Number(value) : target.end_seconds;
        target.duration_seconds = Math.max(0.5, Number((en - st).toFixed(2)));
        const timestamp = (seconds: number) => new Date(Math.max(0, seconds) * 1000).toISOString().slice(11, 23);
        target.start = timestamp(st);
        target.end = timestamp(en);
      }

      next[index] = target;
      return next;
    });
  };

  const handleDeleteScene = (index: number) => {
    setScenes((prev) => prev.filter((_, i) => i !== index));
  };

  const handleAddSceneForMovie = (slot: number, movieTitle: string) => {
    const newScene: SceneItem = {
      slot,
      movie_title: movieTitle,
      start: "00:00:15.000",
      end: "00:00:19.000",
      start_seconds: 15.0,
      end_seconds: 19.0,
      duration_seconds: 4.0,
      scene_type: "action_peak",
      visual_energy: "high",
      reason: `Custom scene clip for ${movieTitle}`,
      source_video_path: sourceVideos.find(v => v.movie_slot === slot || v.movie_title.trim().toLowerCase() === movieTitle.trim().toLowerCase())?.local_path,
    };
    setScenes((prev) => [...prev, newScene]);
  };

  const totalFootageDuration = scenes
    .reduce((acc, s) => acc + (s.duration_seconds || 0), 0)
    .toFixed(1);

  const getSceneTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "hook":
        return "bg-rose-500/15 text-rose-400 border-rose-500/30";
      case "action_peak":
        return "bg-amber-500/15 text-amber-400 border-amber-500/30";
      case "danger_suspense":
        return "bg-purple-500/15 text-purple-400 border-purple-500/30";
      case "story_setup":
        return "bg-cyan-500/15 text-cyan-400 border-cyan-500/30";
      default:
        return "bg-slate-500/15 text-slate-400 border-slate-500/30";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Top Banner / Actions */}
      <div className="rounded-3xl glass-panel p-6 shadow-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border border-white/[0.08]">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-rose-600 to-amber-500 shadow-lg shadow-rose-950/40">
              <Clapperboard className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-black text-white">Gemini Scene Selector</h2>
              <p className="text-xs text-slate-400">
                Analyze all downloaded trailers, alternate sources, and filter obvious black or repeated shots to match voiceover length.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          {scenes.length > 0 && (
            <button
              onClick={handleSaveScenes}
              disabled={isSaving}
              className="flex-1 md:flex-none flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-2.5 text-xs font-bold text-slate-200 border border-white/10 hover:border-white/25 hover:text-white transition disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              <span>{isSaving ? "Saving..." : "Save Timings"}</span>
            </button>
          )}

          <button
            onClick={handleSelectScenes}
            disabled={isSelecting || !hasTrailers}
            className={`flex-1 md:flex-none flex items-center justify-center gap-2 rounded-2xl px-5 py-2.5 text-xs font-black text-white shadow-xl transition glow-rose ${
              !hasTrailers
                ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-white/[0.05]"
                : "bg-gradient-to-r from-rose-600 via-pink-600 to-amber-500 shadow-rose-950/60 hover:scale-105 active:scale-95"
            }`}
          >
            <Sparkles className={`h-4 w-4 ${isSelecting ? "animate-spin" : ""}`} />
            <span>{isSelecting ? "Analyzing with Gemini..." : scenes.length > 0 ? "Re-Select Scenes" : "AI Pick Scenes with Gemini"}</span>
          </button>
        </div>
      </div>

      {/* Warning if trailers not downloaded */}
      {!hasTrailers && (
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4 flex items-center gap-3 text-amber-300 text-xs">
          <AlertCircle className="h-5 w-5 shrink-0 text-amber-400" />
          <div className="flex-1">
            <span className="font-bold">Trailers Not Downloaded Yet: </span>
            Please go to Step 2 (Trailers & Clips) and download the movie trailers so Gemini can inspect them and choose high-energy footage clips.
          </div>
        </div>
      )}

      {/* Messages */}
      {error && (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 flex items-center gap-3 text-rose-300 text-xs">
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 flex items-center gap-3 text-emerald-300 text-xs">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Metrics Bar */}
      {hasTrailers && <div className="rounded-2xl glass-panel p-4 space-y-2 text-xs text-slate-300">
        <p className="font-bold text-white">Trailer coverage: {new Set(scenes.map(s => s.source_video_path)).size} / {sourceVideos.length} used</p>
        {sourceVideos.map((source, index) => <p key={source.local_path}>
          {index + 1}. {source.source_label || source.label || source.movie_title} — {scenes.filter(s => s.source_video_path === source.local_path).length} clips
        </p>)}
        {scenes.some(s => s.selection_method === "temporal_fallback") && <p className="text-amber-300">Some clips use time-distributed fallback because visual AI analysis was unavailable or returned too little footage. Preview them before composing.</p>}
      </div>}
      {scenes.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="rounded-2xl glass-panel p-4 border border-white/[0.08] flex flex-col gap-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Total Scenes</span>
            <span className="text-xl font-black text-white">{scenes.length} Clips</span>
          </div>
          <div className="rounded-2xl glass-panel p-4 border border-white/[0.08] flex flex-col gap-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Footage Duration</span>
            <span className="text-xl font-black text-rose-400">{totalFootageDuration}s</span>
          </div>
          <div className="rounded-2xl glass-panel p-4 border border-white/[0.08] flex flex-col gap-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Movies Covered</span>
            <span className="text-xl font-black text-amber-400">
              {new Set(scenes.map((s) => s.slot)).size} / {movies.length}
            </span>
          </div>
          <div className="rounded-2xl glass-panel p-4 border border-white/[0.08] flex flex-col gap-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Pacing Style</span>
            <span className="text-xl font-black text-cyan-400">High Energy Shorts</span>
          </div>
        </div>
      )}

      {/* Scenes Grouped by Movie */}
      <div className="flex flex-col gap-5">
        {movies.map((movie, idx) => {
          const slot = idx + 1;
          const movieScenes = scenes.filter((s) => s.slot === slot);
          const hasSource = sourceVideos.some(
            (v) => v.movie_title.toLowerCase() === movie.title.toLowerCase() || sourceVideos.length > idx
          );

          return (
            <div
              key={idx}
              className="rounded-3xl glass-panel p-5 border border-white/[0.08] flex flex-col gap-4 shadow-xl"
            >
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
                <div className="flex items-center gap-3">
                  <span className="rounded-xl bg-black/80 px-2.5 py-1 text-xs font-black text-rose-400 border border-white/10">
                    Slot #{slot}
                  </span>
                  <div>
                    <h3 className="font-extrabold text-white text-sm">{movie.title}</h3>
                    <p className="text-[11px] text-slate-400 font-medium">
                      {movieScenes.length} scenes selected •{" "}
                      {movieScenes.reduce((acc, s) => acc + (s.duration_seconds || 0), 0).toFixed(1)}s footage
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => handleAddSceneForMovie(slot, movie.title)}
                  className="flex items-center gap-1.5 rounded-xl bg-slate-900/90 px-3 py-1.5 text-xs font-bold text-slate-300 border border-white/[0.08] hover:text-white hover:border-white/20 transition"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Clip</span>
                </button>
              </div>

              {movieScenes.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500 flex flex-col items-center justify-center gap-2">
                  <Film className="h-8 w-8 text-slate-600 opacity-60" />
                  <span>No scenes selected for this movie yet. Click "AI Pick Scenes with Gemini" above.</span>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {movieScenes.map((sc) => {
                    const sceneIndex = scenes.findIndex((s) => s === sc);
                    return (
                      <div
                        key={sceneIndex}
                        className="rounded-2xl bg-slate-950/80 p-4 border border-white/[0.06] flex flex-col justify-between gap-3 shadow-md hover:border-white/15 transition"
                      >
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center justify-between">
                            <span
                              className={`rounded-lg px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider border ${getSceneTypeColor(
                                sc.scene_type
                              )}`}
                            >
                              {sc.scene_type.replace("_", " ")}
                            </span>
                            <button
                              onClick={() => handleDeleteScene(sceneIndex)}
                              className="text-slate-500 hover:text-rose-400 transition p-1"
                              title="Remove Scene"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>

                          <p className="text-xs text-slate-300 font-medium line-clamp-2 leading-relaxed">
                            {sc.reason || "High energy scene chosen for viral Shorts pacing"}
                          </p>
                          <label className="text-[10px] font-bold text-slate-400">Source trailer
                            <select aria-label={`Source trailer for scene ${sceneIndex + 1}`} value={sc.source_video_path || ""}
                              onChange={e => handleUpdateScene(sceneIndex, "source_video_path", e.target.value)}
                              className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900 p-2 text-xs text-white">
                              <option value="" disabled>Choose trailer</option>
                              {sourceVideos.filter(v => v.movie_slot === sc.slot || v.movie_title.trim().toLowerCase() === sc.movie_title.trim().toLowerCase()).map(v =>
                                <option key={v.local_path} value={v.local_path}>{v.source_label || v.label || v.movie_title}</option>)}
                            </select>
                          </label>
                          <p className="text-[10px] text-slate-500">{sc.selection_method === "temporal_fallback" ? "Time-distributed fallback" : sc.selection_method === "gemini_video" ? "Gemini video analysis" : "Saved / manual scene"}</p>
                          <button type="button" onClick={() => setPreviewScene(previewScene === sceneIndex ? null : sceneIndex)} className="flex items-center gap-1 text-xs font-semibold text-cyan-400">
                            <Play className="h-3 w-3" /> {previewScene === sceneIndex ? "Hide preview" : "Preview this clip"}
                          </button>
                          {previewScene === sceneIndex && sc.source_video_path && <video controls autoPlay muted playsInline preload="metadata"
                            key={`${sc.source_video_path}-${sc.start_seconds}`}
                            src={`${API_BASE_URL}/projects/${project.id}/source-video/${sourceVideos.findIndex(v => v.local_path === sc.source_video_path)}`}
                            onLoadedMetadata={e => { e.currentTarget.currentTime = sc.start_seconds; }}
                            onTimeUpdate={e => { if (e.currentTarget.currentTime >= sc.end_seconds) e.currentTarget.pause(); }}
                            className="w-full rounded-lg bg-black" />}
                        </div>

                        {/* Timing Controls */}
                        <div className="pt-2 border-t border-white/[0.06] flex flex-col gap-2">
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                              <label className="text-[10px] text-slate-400 font-bold block mb-1">
                                Start (sec)
                              </label>
                              <input
                                type="number"
                                step="0.5"
                                value={sc.start_seconds}
                                onChange={(e) =>
                                  handleUpdateScene(sceneIndex, "start_seconds", parseFloat(e.target.value) || 0)
                                }
                                className="w-full rounded-xl bg-slate-900 border border-white/10 px-2.5 py-1 text-xs text-white font-mono focus:border-rose-500 focus:outline-none"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 font-bold block mb-1">
                                End (sec)
                              </label>
                              <input
                                type="number"
                                step="0.5"
                                value={sc.end_seconds}
                                onChange={(e) =>
                                  handleUpdateScene(sceneIndex, "end_seconds", parseFloat(e.target.value) || 0)
                                }
                                className="w-full rounded-xl bg-slate-900 border border-white/10 px-2.5 py-1 text-xs text-white font-mono focus:border-rose-500 focus:outline-none"
                              />
                            </div>
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-slate-400 font-semibold pt-1">
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3 text-rose-400" />
                              {sc.duration_seconds}s clip
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {sc.start.split(".")[0]} → {sc.end.split(".")[0]}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
