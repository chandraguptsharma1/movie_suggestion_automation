"use client";

import React, { useState } from "react";
import { Project } from "@/lib/types";
import { generateScript, updateScript } from "@/lib/api";
import {
  Sparkles,
  Copy,
  Check,
  Save,
  Loader2,
  FileText,
  Clock,
  Flame,
  Film,
  Send,
  Eye,
} from "lucide-react";

interface ScriptEditorProps {
  project: Project;
  onProjectUpdated: (updated: Project) => void;
}

export function ScriptEditor({ project, onProjectUpdated }: ScriptEditorProps) {
  const [scriptText, setScriptText] = useState(project.script_text || "");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"script" | "packaging">("script");
  const [error, setError] = useState<string | null>(null);

  const scriptData = project.script_data_json;

  // Word count & duration estimate
  const words = scriptText.trim() ? scriptText.trim().split(/\s+/).length : 0;
  const estimatedSeconds = Math.round((words / 140) * 60);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const res = await generateScript(project.id, project.notes || "");
      onProjectUpdated(res.project);
      setScriptText(res.project.script_text || "");
    } catch (err: any) {
      setError(err.message || "Failed to generate script.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const res = await updateScript(project.id, scriptText);
      onProjectUpdated(res.project);
    } catch (err: any) {
      setError(err.message || "Failed to save script.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(scriptText);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <div className="flex min-w-0 flex-col gap-6 rounded-3xl glass-panel p-4 sm:p-7 shadow-xl">
      {/* Studio Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-white/[0.08]">
        <div className="flex items-center gap-3.5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-amber-500 to-rose-600 shadow-lg shadow-amber-950/40">
            <FileText className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-black text-white tracking-tight flex items-center gap-2">
              Viral Hindi Script Studio
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Native Devanagari Hindi for flawless Sarvam AI neural speech synthesis
            </p>
          </div>
        </div>

        {/* Metrics Chip */}
        {scriptText && (
          <div className="flex items-center gap-2 rounded-2xl bg-slate-900/80 px-3.5 py-1.5 border border-white/[0.06] text-xs">
            <span className="text-slate-400">{words} Words</span>
            <span className="text-slate-600">•</span>
            <span className="flex items-center gap-1 font-bold text-amber-400">
              <Clock className="h-3 w-3" />
              ~{estimatedSeconds}s Duration (Ideal 50-60s)
            </span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-amber-500 via-rose-500 to-red-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-rose-950/40 hover:scale-[1.02] active:scale-95 disabled:opacity-50 transition glow-rose"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Writing Hindi Script...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>{scriptText ? "Regenerate Script" : "Generate Script"}</span>
              </>
            )}
          </button>

          {scriptText && (
            <>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 rounded-2xl bg-slate-900 px-4 py-2.5 text-xs font-bold text-slate-200 border border-white/[0.08] hover:bg-slate-800 transition"
              >
                {isCopied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{isCopied ? "Copied!" : "Copy"}</span>
              </button>

              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-1.5 rounded-2xl bg-emerald-500/10 px-4 py-2.5 text-xs font-bold text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition"
              >
                {isSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                <span>Save</span>
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-xs font-semibold text-red-400">
          {error}
        </div>
      )}

      {/* View Switcher */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab("script")}
          className={`rounded-xl px-4 py-2 text-xs font-bold transition border ${
            activeTab === "script"
              ? "bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-sm"
              : "bg-slate-950/60 text-slate-400 border-white/[0.04] hover:text-white"
          }`}
        >
          Spoken Script & Breakdown
        </button>
        <button
          onClick={() => setActiveTab("packaging")}
          className={`rounded-xl px-4 py-2 text-xs font-bold transition border ${
            activeTab === "packaging"
              ? "bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-sm"
              : "bg-slate-950/60 text-slate-400 border-white/[0.04] hover:text-white"
          }`}
        >
          YouTube Packaging & SEO
        </button>
      </div>

      {activeTab === "script" ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Full Spoken Textarea */}
          <div className="lg:col-span-7 flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Full Spoken Teleprompter Text
              </span>
              <span className="text-[10px] text-slate-500">Devanagari Hindi format</span>
            </div>
            <textarea
              rows={16}
              value={scriptText}
              onChange={(e) => setScriptText(e.target.value)}
              placeholder="Script will appear here after clicking 'Generate Script'..."
              className="w-full rounded-3xl bg-slate-950/90 border border-white/[0.08] p-5 font-sans text-sm text-slate-100 leading-relaxed focus:border-rose-500 focus:outline-none shadow-inner"
            />
          </div>

          {/* Right: Structural Breakdown Cards */}
          <div className="lg:col-span-5 flex flex-col gap-3 rounded-3xl bg-slate-950/60 border border-white/[0.06] p-5 max-h-[460px] overflow-y-auto">
            <span className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
              <Flame className="h-3.5 w-3.5 text-rose-500" />
              Shorts Retention Architecture
            </span>

            {scriptData?.hook && (
              <div className="rounded-2xl bg-rose-500/10 border border-rose-500/20 p-3.5">
                <span className="text-[10px] font-black uppercase tracking-wider text-rose-400">
                  🔥 Viral Hook (0 to 5 sec)
                </span>
                <p className="mt-1 text-xs text-rose-100 font-semibold leading-relaxed">
                  {scriptData.hook}
                </p>
              </div>
            )}

            {scriptData?.movie_spotlights?.map((sp, idx) => (
              <div
                key={idx}
                className="rounded-2xl bg-slate-900/80 border border-white/[0.06] p-3.5 flex flex-col gap-1.5"
              >
                <div className="flex items-center justify-between text-[10px]">
                  <span className="font-extrabold uppercase text-amber-300">
                    Movie #{sp.slot}: {sp.title}
                  </span>
                  <span className="font-bold text-slate-400">{sp.duration_sec}s</span>
                </div>
                {sp.story_premise && (
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-slate-400">Story:</strong> {sp.story_premise}
                  </p>
                )}
                {sp.why_to_watch && (
                  <p className="text-[11px] text-amber-300/90 font-medium leading-relaxed">
                    <strong className="text-amber-400">Reason to Watch:</strong> {sp.why_to_watch}
                  </p>
                )}
              </div>
            ))}

            {scriptData?.outro && (
              <div className="rounded-2xl bg-emerald-500/10 border border-emerald-500/20 p-3.5">
                <span className="text-[10px] font-black uppercase tracking-wider text-emerald-400">
                  ⚡ Outro Call-To-Action (55 to 60 sec)
                </span>
                <p className="mt-1 text-xs text-emerald-100 font-semibold leading-relaxed">
                  {scriptData.outro}
                </p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* YouTube Packaging */
        <div className="flex flex-col gap-4 rounded-3xl bg-slate-950/80 border border-white/[0.06] p-6">
          <div>
            <label className="text-xs font-bold text-slate-300">YouTube Shorts Title</label>
            <input
              type="text"
              readOnly
              value={scriptData?.youtube_title || ""}
              className="mt-1.5 w-full rounded-2xl glass-input px-4 py-2.5 text-xs font-semibold text-white"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-slate-300">YouTube Description & Hashtags</label>
            <textarea
              rows={4}
              readOnly
              value={scriptData?.youtube_description || ""}
              className="mt-1.5 w-full rounded-2xl glass-input p-4 text-xs font-medium text-white leading-relaxed"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-300">Thumbnail Hook Banner Text</label>
              <div className="mt-1.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 px-4 py-3 text-xs font-black text-amber-300 uppercase tracking-wide">
                {scriptData?.thumbnail_text || "TOP MASTERPIECES"}
              </div>
            </div>
            <div>
              <label className="text-xs font-bold text-slate-300">Recommended Audio Atmosphere</label>
              <div className="mt-1.5 rounded-2xl bg-slate-900 border border-white/[0.06] px-4 py-3 text-xs text-slate-300 font-medium">
                {scriptData?.bgm_style || "Fast Dark Synthwave / Suspense Pulse"}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
