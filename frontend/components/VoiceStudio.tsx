"use client";

import React, { useState } from "react";
import { Project } from "@/lib/types";
import { generateVoice, getVoiceAudioUrl } from "@/lib/api";
import { Mic, Volume2, Play, Download, Loader2, Sparkles, User, AudioLines, Flame, Radio } from "lucide-react";

interface VoiceStudioProps {
  project: Project;
  onProjectUpdated: (updated: Project) => void;
}

const SPEAKERS = [
  {
    id: "vipul_hi_social",
    label: "Vipul",
    badge: "High Energy Creator",
    desc: "Top recommendation for fast-paced viral YouTube Shorts and hook retention.",
    tagColor: "text-rose-400 bg-rose-500/10 border-rose-500/20",
  },
  {
    id: "aditya_hi_conversational",
    label: "Aditya",
    badge: "Conversational Storyteller",
    desc: "Smooth, friendly Indian delivery with natural excitement.",
    tagColor: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  },
  {
    id: "sunny_hi_reels",
    label: "Sunny",
    badge: "Punchy Reels",
    desc: "Fast, punchy, and modern delivery crafted for Instagram Reels & TikTok.",
    tagColor: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  },
  {
    id: "shubh_hi_stories_dramatic",
    label: "Shubh",
    badge: "Dramatic Suspense",
    desc: "Deep, intense tone tailored for psychological thrillers and horror films.",
    tagColor: "text-purple-400 bg-purple-500/10 border-purple-500/20",
  },
  {
    id: "simran_hi_conversation",
    label: "Simran",
    badge: "Expressive Female",
    desc: "Crystal-clear, vibrant delivery with engaging emotional shifts.",
    tagColor: "text-pink-400 bg-pink-500/10 border-pink-500/20",
  },
];

export function VoiceStudio({ project, onProjectUpdated }: VoiceStudioProps) {
  const [selectedSpeaker, setSelectedSpeaker] = useState("vipul_hi_social");
  const [pace, setPace] = useState(1.05);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioKey, setAudioKey] = useState(0);

  const hasAudio = !!project.voice_audio_path;
  const audioUrl = hasAudio ? getVoiceAudioUrl(project.id) : null;

  const handleGenerate = async () => {
    if (!project.script_text) {
      setError("Please generate or enter a script before generating voiceover.");
      return;
    }
    setIsGenerating(true);
    setError(null);
    try {
      const res = await generateVoice(project.id, selectedSpeaker, pace);
      onProjectUpdated(res.project);
      setAudioKey((prev) => prev + 1);
    } catch (err: any) {
      setError(err.message || "Failed to generate voice.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex min-w-0 flex-col gap-6 rounded-3xl glass-panel p-4 sm:p-7 shadow-xl">
      {/* Studio Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-white/[0.08]">
        <div className="flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-rose-600 to-pink-500 shadow-lg shadow-rose-950/40">
            <Mic className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-black text-white tracking-tight flex items-center gap-2">
              Sarvam AI Neural Hindi Voice Studio
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Bulbul model with native Hindi Devanagari neural pronunciation
            </p>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGenerating || !project.script_text}
          className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-rose-600 via-pink-600 to-amber-500 px-6 py-2.5 text-xs font-bold text-white shadow-lg shadow-rose-950/50 hover:scale-[1.02] active:scale-95 disabled:opacity-50 transition glow-rose"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Generating Neural Audio...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              <span>{hasAudio ? "Regenerate Voiceover" : "Generate Neural Voice"}</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-xs font-semibold text-red-400">
          {error}
        </div>
      )}

      {/* Speaker Selector Cards */}
      <div>
        <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
          Choose Hindi Neural Voice
        </label>
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {SPEAKERS.map((s) => {
            const isSelected = selectedSpeaker === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => setSelectedSpeaker(s.id)}
                className={`flex flex-col items-start rounded-2xl p-4 text-left transition-all border ${
                  isSelected
                    ? "bg-rose-500/15 border-rose-500 shadow-lg shadow-rose-950/20 ring-1 ring-rose-500/50"
                    : "glass-card hover:border-white/15"
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-2">
                    <div
                      className={`h-8 w-8 rounded-xl flex items-center justify-center font-bold text-xs ${
                        isSelected ? "bg-rose-600 text-white" : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      <User className="h-4 w-4" />
                    </div>
                    <span className="text-xs font-extrabold text-white">{s.label}</span>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[9px] font-bold border ${s.tagColor}`}
                  >
                    {s.badge}
                  </span>
                </div>
                <p className="mt-2.5 text-[11px] text-slate-400 leading-relaxed">{s.desc}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Pace Controller */}
      <div className="rounded-3xl bg-slate-950/80 border border-white/[0.06] p-5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-slate-300 uppercase tracking-wider">
            Speech Rate / Speaking Pace
          </span>
          <span className="font-black text-rose-400 bg-rose-500/10 px-2.5 py-0.5 rounded-lg border border-rose-500/20">
            {pace}x Speed
          </span>
        </div>
        <input
          type="range"
          min="0.90"
          max="1.25"
          step="0.05"
          value={pace}
          onChange={(e) => setPace(parseFloat(e.target.value))}
          className="mt-3 w-full accent-rose-500 cursor-pointer"
        />
        <div className="flex justify-between text-[11px] text-slate-500 mt-1 font-medium">
          <span>0.90x (Relaxed Story)</span>
          <span className="text-amber-400 font-bold">1.05x (Optimal Viral Shorts Pace)</span>
          <span>1.25x (Fast Reels)</span>
        </div>
      </div>

      {/* Live Audio Player Card */}
      {hasAudio && audioUrl ? (
        <div className="rounded-3xl bg-gradient-to-r from-rose-950/40 via-purple-950/20 to-amber-950/30 border border-rose-500/30 p-6 flex flex-col gap-4 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <AudioLines className="h-4 w-4" />
              </div>
              <div>
                <span className="text-xs font-extrabold text-white">Generated Hindi Neural Audio</span>
                <p className="text-[10px] text-slate-400">Speaker: {project.voice_data_json?.speaker}</p>
              </div>
            </div>

            <span className="text-xs font-bold text-amber-400 bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/20">
              Duration: {project.voice_data_json?.duration_seconds}s
            </span>
          </div>

          <audio
            key={audioKey}
            controls
            src={audioUrl}
            className="w-full mt-1 rounded-xl accent-rose-500 shadow"
          />

          <div className="flex justify-end pt-2 border-t border-white/[0.06]">
            <a
              href={audioUrl}
              download="voice.mp3"
              className="flex items-center gap-2 rounded-xl bg-slate-900 border border-white/[0.08] px-4 py-2 text-xs font-bold text-rose-300 hover:text-white hover:bg-slate-800 transition"
            >
              <Download className="h-4 w-4" />
              <span>Download MP3 Audio</span>
            </a>
          </div>
        </div>
      ) : (
        <div className="text-center p-8 rounded-3xl bg-slate-950/40 border border-white/[0.04] text-slate-500">
          <AudioLines className="mx-auto h-8 w-8 opacity-30 mb-2" />
          <p className="text-xs font-medium">Audio not generated yet.</p>
          <p className="text-[11px] text-slate-600 mt-0.5">
            Click "Generate Neural Voice" to produce high-retention audio.
          </p>
        </div>
      )}
    </div>
  );
}
