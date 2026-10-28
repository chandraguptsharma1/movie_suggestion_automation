"use client";

import { DownloadThumbnailButton } from "./DownloadThumbnailButton";
import React, { useState } from "react";
import { Project } from "@/lib/types";
import { generateCollageThumbnail, setPosterThumbnail, getThumbnailImageUrl, updateThumbnailEnding } from "@/lib/api";
import { ImageIcon, Sparkles, Loader2, Star, Check, Smartphone, Palette } from "lucide-react";

interface CollageThumbnailStudioProps {
  project: Project;
  onProjectUpdated: (updated: Project) => void;
}

const HOOK_PRESETS = [
  { top: "SUPER ADDICTIVE", bottom: "MASTERPIECES!" },
  { top: "TOP 3 THRILLERS", bottom: "MIND BLOWING!" },
  { top: "EDGE OF THE SEAT", bottom: "MUST WATCH!" },
  { top: "CRAZY TWISTS", bottom: "UNPREDICTABLE!" },
];

export function CollageThumbnailStudio({ project, onProjectUpdated }: CollageThumbnailStudioProps) {
  const [topText, setTopText] = useState(
    project.thumbnail_data_json?.top_text ||
      project.script_data_json?.thumbnail_text?.split(" ")[0] ||
      "SUPER ADDICTIVE"
  );
  const [bottomText, setBottomText] = useState(
    project.thumbnail_data_json?.bottom_text || "MASTERPIECES!"
  );
  const [ratingText, setRatingText] = useState(
    project.thumbnail_data_json?.rating_text || "★ 8.4/10"
  );
  const [isGenerating, setIsGenerating] = useState(false);
  const [layout, setLayout] = useState<'poster_focus' | 'cinema' | 'classic'>(project.thumbnail_data_json?.layout || 'poster_focus');
  const [isUpdatingEnding, setIsUpdatingEnding] = useState(false);
  const [isSettingPoster, setIsSettingPoster] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imgKey, setImgKey] = useState(0);

  const hasThumbnail = !!project.thumbnail_path;
  const thumbUrl = hasThumbnail ? getThumbnailImageUrl(project.id) : null;
  const movies = project.movies_json || [];

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const res = await generateCollageThumbnail(project.id, {
        top_text: topText.trim(),
        bottom_text: bottomText.trim(),
        rating_text: ratingText.trim(),
        layout,
      });
      onProjectUpdated(res.project);
      setImgKey((k) => k + 1);
    } catch (err: any) {
      setError(err.message || "Failed to generate collage thumbnail.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleUsePoster = async (posterUrl: string) => {
    setIsSettingPoster(true);
    setError(null);
    try {
      const res = await setPosterThumbnail(project.id, posterUrl);
      onProjectUpdated(res.project);
      setImgKey((k) => k + 1);
    } catch (err: any) {
      setError(err.message || "Failed to set poster thumbnail.");
    } finally {
      setIsSettingPoster(false);
    }
  };

  return (
    <div className="flex min-w-0 flex-col gap-6 rounded-3xl glass-panel p-4 sm:p-7 shadow-xl">
      {/* Studio Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-white/[0.08]">
        <div className="flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-amber-500 via-yellow-500 to-rose-500 shadow-lg shadow-amber-950/40">
            <ImageIcon className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-black text-white tracking-tight flex items-center gap-2">
              Poster Thumbnail Studio
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Large movie posters, readable titles and two fresh 9:16 designs
            </p>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-amber-500 via-rose-500 to-red-600 px-6 py-2.5 text-xs font-bold text-white shadow-lg shadow-rose-950/50 hover:scale-[1.02] active:scale-95 disabled:opacity-50 transition glow-amber"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Rendering thumbnail...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              <span>Generate thumbnail</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-xs font-semibold text-red-400">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left: Customization Controls */}
        <div className="lg:col-span-7 flex flex-col gap-5">
          <div className="grid gap-2 sm:grid-cols-3" aria-label="Thumbnail design">
            {([{id: 'poster_focus', title: 'Poster Spotlight', detail: 'Full poster · large title'},
               {id: 'cinema', title: 'Cinema Cover', detail: 'Edge-to-edge art · gold hook'},
               {id: 'classic', title: 'Classic Collage', detail: 'Small tilted poster cards'}] as const).map(option => (
              <button key={option.id} type="button" aria-pressed={layout === option.id} onClick={() => setLayout(option.id)}
                className={`rounded-xl border p-3 text-left ${layout === option.id ? 'border-amber-400 bg-amber-400/10' : 'border-white/10 bg-slate-950'}`}>
                <span className="block text-sm font-bold text-white">{option.title}</span>
                <span className="text-xs text-slate-400">{option.detail}</span>
              </button>
            ))}
          </div>
          {/* Preset Buttons */}
          <div>
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Palette className="h-3.5 w-3.5 text-amber-400" />
              Viral Hook Presets
            </label>
            <div className="mt-2.5 flex flex-wrap gap-2">
              {HOOK_PRESETS.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setTopText(p.top);
                    setBottomText(p.bottom);
                  }}
                  className="rounded-xl bg-slate-900 border border-white/[0.06] px-3 py-1.5 text-[11px] font-bold text-slate-300 hover:border-amber-400/50 hover:text-white transition"
                >
                  {p.top} • {p.bottom}
                </button>
              ))}
            </div>
          </div>

          {/* Banner Text Editors */}
          <div className="rounded-3xl bg-slate-950/80 border border-white/[0.08] p-5 flex flex-col gap-4">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Hook Banner Typography (English Only)
            </span>

            <div>
              <label className="text-xs font-semibold text-slate-400">Main hook</label>
              <input
                type="text"
                value={topText}
                onChange={(e) => setTopText(e.target.value.toUpperCase())}
                placeholder="e.g. SUPER ADDICTIVE"
                className="mt-1.5 w-full rounded-2xl glass-input px-4 py-2.5 text-xs font-black tracking-wider text-white uppercase focus:border-amber-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400">Secondary hook (Cinema / Classic)</label>
              <input
                type="text"
                value={bottomText}
                onChange={(e) => setBottomText(e.target.value.toUpperCase())}
                placeholder="e.g. MASTERPIECES!"
                className="mt-1.5 w-full rounded-2xl glass-input px-4 py-2.5 text-xs font-black tracking-wider text-amber-400 uppercase focus:border-amber-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400">Star Rating Badge</label>
              <input
                type="text"
                value={ratingText}
                onChange={(e) => setRatingText(e.target.value)}
                placeholder="e.g. ★ 8.4/10"
                className="mt-1.5 w-full rounded-2xl glass-input px-4 py-2.5 text-xs font-bold text-yellow-400 focus:border-amber-400 focus:outline-none"
              />
            </div>
          </div>

          {/* Individual Poster Picker */}
          <div className="rounded-3xl bg-slate-950/80 border border-white/[0.08] p-5">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Or Use Single Movie Poster as Thumbnail:
            </span>
            <div className="mt-3 flex gap-3 overflow-x-auto pb-2">
              {movies.map((m, idx) => (
                <div
                  key={idx}
                  onClick={() => m.poster_url && handleUsePoster(m.poster_url)}
                  className="group relative h-28 w-20 rounded-2xl bg-slate-900 border border-white/[0.08] overflow-hidden shrink-0 cursor-pointer hover:border-amber-400 hover:scale-105 transition-all shadow-md"
                >
                  {m.poster_url && (
                    <img src={m.poster_url} alt={m.title} className="h-full w-full object-cover" />
                  )}
                  <span className="absolute bottom-0 inset-x-0 bg-black/85 py-1 text-center text-[10px] font-black text-slate-200 group-hover:text-amber-400 truncate px-1">
                    Slot #{idx + 1}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Realistic Phone Viewport Mockup */}
        <div className="lg:col-span-5 flex flex-col items-center justify-center">
          <div className="relative w-full max-w-64 rounded-[40px] bg-slate-900 p-3 shadow-2xl border-4 border-slate-800 ring-1 ring-white/10">
            {/* Notch */}
            <div className="absolute top-4 left-1/2 -translate-x-1/2 h-3.5 w-20 bg-slate-950 rounded-full z-20 flex items-center justify-center">
              <div className="h-1.5 w-1.5 rounded-full bg-slate-800 mr-2" />
              <div className="h-1 w-6 rounded-full bg-slate-800" />
            </div>

            {/* Screen Viewport */}
            <div className="relative aspect-[9/16] w-full rounded-[30px] overflow-hidden bg-black shadow-inner flex items-center justify-center">
              {hasThumbnail && thumbUrl ? (
                <img
                  key={imgKey}
                  src={thumbUrl}
                  alt="Movie poster thumbnail design"
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="text-center text-slate-500 p-6">
                  <Smartphone className="mx-auto h-10 w-10 opacity-30 mb-2 text-amber-400" />
                  <p className="text-xs font-bold text-slate-400">9:16 Shorts Viewport</p>
                  <p className="text-[10px] text-slate-600 mt-1">
                    Choose a design and generate its preview.
                  </p>
                </div>
              )}
            </div>
          </div>

          {hasThumbnail && thumbUrl && (
            <div className="mt-4 flex justify-center">
              <DownloadThumbnailButton url={thumbUrl} filename={`shorts-thumbnail-${project.id}.jpg`} />
            </div>
          )}
          {hasThumbnail && project.final_video_path && <div className="mt-4 max-w-sm space-y-2 text-center">
            <button type="button" disabled={isUpdatingEnding || isGenerating} onClick={async () => {
              setIsUpdatingEnding(true); setError(null);
              try { const result = await updateThumbnailEnding(project.id); onProjectUpdated(result.project); }
              catch (err) { setError(err instanceof Error ? err.message : 'Could not update ending'); }
              finally { setIsUpdatingEnding(false); }
            }} className="rounded-xl border border-teal-400/40 bg-teal-400/10 px-4 py-2 text-sm font-bold text-teal-200 disabled:opacity-50">
              {isUpdatingEnding ? 'Updating video ending…' : 'Update video ending with this design'}
            </button>
            <p className="text-xs text-slate-400">Replaces the local ending card. Existing YouTube uploads keep their original video frames; use the Upload tab to apply the new image.</p>
          </div>}
        </div>
      </div>
    </div>
  );
}
