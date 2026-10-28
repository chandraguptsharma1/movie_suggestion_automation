"use client";

import React, { useState, useEffect } from "react";
import { Project } from "@/lib/types";
import { composeVideo, getVideoStreamUrl } from "@/lib/api";
import { BackgroundMusicControls, savedMusic } from './BackgroundMusicControls';
import {
  Clapperboard,
  Download,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Smartphone,
  Scissors,
  ZoomIn,
  Sliders,
  Sparkles,
} from "lucide-react";

interface VideoComposerProps {
  project: Project;
  onProjectUpdated: (updated: Project) => void;
}

export function VideoComposer({ project, onProjectUpdated }: VideoComposerProps) {
  const [isComposing, setIsComposing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [videoKey, setVideoKey] = useState(0);

  // Layout & Crop Controls
  const [cropBlackBars, setCropBlackBars] = useState<boolean>(true);
  const [foregroundZoom, setForegroundZoom] = useState<number>(1.70);
  const [foregroundWidth, setForegroundWidth] = useState<number>(1220);
  const [compositionResult, setCompositionResult] = useState<any>(null);
  const [music, setMusic] = useState(() => savedMusic(project));
  useEffect(() => { setMusic(savedMusic(project)); }, [project.id]);

  const downloadedVideos = project.source_videos_json || [];
  const scenes = project.scenes_json || [];
  const hasVoice = !!project.voice_audio_path;
  const hasClips = downloadedVideos.length > 0;
  const hasScenes = scenes.length > 0;
  const hasThumbnail = !!project.thumbnail_path;
  const hasFinalVideo = !!project.final_video_path;
  const videoUrl = hasFinalVideo ? getVideoStreamUrl(project.id) : null;

  const handleCompose = async () => {
    if (!hasVoice) {
      setError("Please generate voiceover first in the Sarvam Voice tab.");
      return;
    }
    if (!hasClips) {
      setError("Please download at least one trailer clip first in the Trailers tab.");
      return;
    }
    if (!hasThumbnail) {
      setError('Generate or upload a thumbnail first. It will appear for 2 seconds at the end.');
      return;
    }

    setIsComposing(true);
    setError(null);
    try {
      const res = await composeVideo(project.id, {
        crop_black_bars: cropBlackBars,
        foreground_zoom: foregroundZoom,
        foreground_width: foregroundWidth,
        include_bgm: music.enabled,
        bgm_style: music.style,
        bgm_volume: music.volume,
        bgm_ducking: music.ducking,
      });
      if (res.composition) {
        setCompositionResult(res.composition);
      }
      onProjectUpdated(res.project);
      setVideoKey((k) => k + 1);
    } catch (err: any) {
      setError(err.message || "Failed to render shorts video.");
    } finally {
      setIsComposing(false);
    }
  };

  const effectiveWidth = Math.round(foregroundWidth * foregroundZoom);

  return (
    <div className="flex min-w-0 flex-col gap-6 rounded-3xl glass-panel p-4 sm:p-7 shadow-xl">
      {/* Studio Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-white/[0.08]">
        <div className="flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-rose-600 to-indigo-600 shadow-lg shadow-rose-950/40">
            <Clapperboard className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-black text-white tracking-tight flex items-center gap-2">
              9:16 Shorts Video Composer (FFmpeg)
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Renders vertical YouTube Shorts (1080x1920) with black area cut, dynamic foreground zoom, and ambient background blur.
            </p>
          </div>
        </div>

        <button
          onClick={handleCompose}
            disabled={isComposing || !hasVoice || !hasClips || !hasThumbnail}
          className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-rose-600 via-pink-600 to-amber-500 px-6 py-2.5 text-xs font-bold text-white shadow-lg shadow-rose-950/50 hover:scale-[1.02] active:scale-95 disabled:opacity-50 transition glow-rose"
        >
          {isComposing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>FFmpeg Rendering Video...</span>
            </>
          ) : (
            <>
              <Clapperboard className="h-4 w-4" />
              <span>{hasFinalVideo ? "Re-compose Video" : "Compose 9:16 Video"}</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-xs font-semibold text-red-400">
          {error}
        </div>
      )}
      <p className="text-xs text-slate-400">{hasThumbnail ? 'The project thumbnail is automatically added as the last 2 seconds, so you can select that frame in YouTube Shorts.' : 'Generate or upload a thumbnail before composing the Short.'}</p>

      {/* Assembly Readiness Checklist */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div
          className={`flex items-center gap-3.5 rounded-2xl p-4 border ${
            hasClips
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              : "bg-amber-500/10 border-amber-500/20 text-amber-400"
          }`}
        >
          {hasClips ? <CheckCircle2 className="h-5 w-5 shrink-0" /> : <AlertCircle className="h-5 w-5 shrink-0" />}
          <div>
            <div className="text-xs font-extrabold text-white">
              {hasClips ? `${downloadedVideos.length} Trailers Downloaded` : "Trailers Missing"}
            </div>
            <div className="text-[11px] opacity-80 mt-0.5">
              {hasClips ? "Ready for scene extraction" : "Download clips in Step 2"}
            </div>
          </div>
        </div>

        <div
          className={`flex items-center gap-3.5 rounded-2xl p-4 border ${
            hasScenes
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              : "bg-cyan-500/10 border-cyan-500/20 text-cyan-400"
          }`}
        >
          {hasScenes ? <CheckCircle2 className="h-5 w-5 shrink-0" /> : <AlertCircle className="h-5 w-5 shrink-0" />}
          <div>
            <div className="text-xs font-extrabold text-white">
              {hasScenes ? `${scenes.length} Gemini Scenes Trimmed` : "Full Trailers (No Cuts)"}
            </div>
            <div className="text-[11px] opacity-80 mt-0.5">
              {hasScenes ? "Exact hook & action cuts" : "Use Step 3 for AI scene cuts"}
            </div>
          </div>
        </div>

        <div
          className={`flex items-center gap-3.5 rounded-2xl p-4 border ${
            hasVoice
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              : "bg-amber-500/10 border-amber-500/20 text-amber-400"
          }`}
        >
          {hasVoice ? <CheckCircle2 className="h-5 w-5 shrink-0" /> : <AlertCircle className="h-5 w-5 shrink-0" />}
          <div>
            <div className="text-xs font-extrabold text-white">
              {hasVoice ? "Sarvam Voiceover Ready" : "Voiceover Missing"}
            </div>
            <div className="text-[11px] opacity-80 mt-0.5">
              {hasVoice
                ? `${project.voice_data_json?.duration_seconds || 0}s Hindi Audio`
                : "Generate voice in Step 5"}
            </div>
          </div>
        </div>
      </div>

      {/* Cinematic Size, Zoom & Black Area Cut Settings */}
      <div className="rounded-2xl bg-slate-900/60 p-5 border border-white/[0.08] flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div className="flex items-center gap-2">
            <Sliders className="h-4 w-4 text-rose-400" />
            <h3 className="text-xs font-extrabold text-white uppercase tracking-wider">
              Cinematic Framing: Size, Zoom & Letterbox Cut
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            Effective Width: <strong className="text-rose-400">{effectiveWidth}px</strong> on 1080x1920
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Black Bar Cut Toggle */}
          <div className="flex flex-col gap-2">
            <label className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <Scissors className="h-3.5 w-3.5 text-amber-400" />
              <span>Black Area Cut (Letterbox)</span>
            </label>
            <button
              type="button"
              onClick={() => setCropBlackBars(!cropBlackBars)}
              className={`flex items-center justify-between rounded-xl px-3.5 py-2.5 text-xs font-bold transition border ${
                cropBlackBars
                  ? "bg-rose-500/20 border-rose-500/40 text-rose-300 shadow-sm"
                  : "bg-slate-950 border-white/10 text-slate-400 hover:text-white"
              }`}
            >
              <span>{cropBlackBars ? "Auto-Cut Enabled" : "Full Frame (No Crop)"}</span>
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  cropBlackBars ? "bg-rose-400 shadow-rose-400/50 shadow" : "bg-slate-600"
                }`}
              />
            </button>
            <p className="text-[10px] text-slate-500 leading-tight">
              Removes top/bottom black bars using FFmpeg cropdetect or 13% safe widescreen crop.
            </p>
          </div>

          {/* Foreground Zoom Slider */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs font-bold text-slate-300">
              <span className="flex items-center gap-1.5">
                <ZoomIn className="h-3.5 w-3.5 text-rose-400" />
                <span>Foreground Zoom</span>
              </span>
              <span className="font-mono text-rose-400 font-extrabold">{foregroundZoom.toFixed(2)}x</span>
            </div>
            <input
              type="range"
              min="1.20"
              max="2.00"
              step="0.05"
              value={foregroundZoom}
              onChange={(e) => setForegroundZoom(parseFloat(e.target.value))}
              className="h-2 w-full appearance-none rounded-lg bg-slate-950 accent-rose-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>1.20x (Subtle)</span>
              <span>1.70x (Recommended)</span>
              <span>2.00x (Full)</span>
            </div>
          </div>

          {/* Foreground Base Width */}
          <div className="flex flex-col gap-2">
            <label className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
              <span>Base Width Presets</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setForegroundWidth(1220)}
                className={`rounded-xl px-2.5 py-2 text-xs font-bold transition border ${
                  foregroundWidth === 1220
                    ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-300"
                    : "bg-slate-950 border-white/10 text-slate-400 hover:text-white"
                }`}
              >
                1220px (Widescreen)
              </button>
              <button
                type="button"
                onClick={() => setForegroundWidth(1020)}
                className={`rounded-xl px-2.5 py-2 text-xs font-bold transition border ${
                  foregroundWidth === 1020
                    ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-300"
                    : "bg-slate-950 border-white/10 text-slate-400 hover:text-white"
                }`}
              >
                1020px (Standard)
              </button>
            </div>
            <p className="text-[10px] text-slate-500 leading-tight">
              1220px gives maximum cinematic punch when black bars are cropped.
            </p>
          </div>
        </div>

        {/* Composition Result Badge */}
        {compositionResult && (
          <div className="mt-2 rounded-xl bg-slate-950/90 p-3 border border-emerald-500/20 flex flex-wrap items-center justify-between gap-2 text-xs">
            <span className="text-emerald-400 font-bold flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4" />
              Composition Render Complete
            </span>
            <div className="flex items-center gap-3 text-[11px] text-slate-400 font-mono">
              <span>Crop Method: <strong className="text-white">{compositionResult.crop_info?.crop_method}</strong></span>
              <span>Effective Width: <strong className="text-white">{compositionResult.layout?.effective_width}px</strong></span>
              <span>Y-Center: <strong className="text-white">{compositionResult.layout?.overlay_y}px</strong></span>
            </div>
          </div>
        )}
      </div>

      <BackgroundMusicControls key={project.id} project={project} value={music} onChange={setMusic} onProjectUpdated={onProjectUpdated} disabled={isComposing} />

      {/* Phone Screen Player Mockup */}
      <div className="flex min-w-0 flex-col items-center justify-center p-2 sm:p-6">
        <div className="relative w-full max-w-64 rounded-[40px] bg-slate-900 p-3 shadow-2xl border-4 border-slate-800 ring-1 ring-white/10">
          {/* Notch */}
          <div className="absolute top-4 left-1/2 -translate-x-1/2 h-3.5 w-20 bg-slate-950 rounded-full z-20 flex items-center justify-center">
            <div className="h-1.5 w-1.5 rounded-full bg-slate-800 mr-2" />
            <div className="h-1 w-6 rounded-full bg-slate-800" />
          </div>

          <div className="relative aspect-[9/16] w-full rounded-[30px] overflow-hidden bg-black shadow-inner flex items-center justify-center">
            {hasFinalVideo && videoUrl ? (
              <video
                key={videoKey}
                controls
                src={videoUrl}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="text-center text-slate-500 p-6">
                <Smartphone className="mx-auto h-10 w-10 opacity-30 mb-2 text-rose-400" />
                <p className="text-xs font-bold text-slate-400">9:16 Shorts Mockup</p>
                <p className="text-[10px] text-slate-600 mt-1">
                  Click "Compose 9:16 Video" to render your YouTube Short.
                </p>
              </div>
            )}
          </div>
        </div>

        {hasFinalVideo && videoUrl && (
          <div className="mt-5 flex justify-center">
            <a
              href={videoUrl}
              download="final_shorts.mp4"
              className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-2.5 text-xs font-bold text-white shadow-lg hover:scale-105 active:scale-95 transition"
            >
              <Download className="h-4 w-4" />
              <span>Download Rendered 9:16 Video (MP4)</span>
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
