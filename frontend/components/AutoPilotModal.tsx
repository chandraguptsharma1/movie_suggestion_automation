"use client";

import React, { useState, useEffect, useRef } from "react";
import { AutoPilotFlow } from "@/components/AutoPilotFlow";
import { Project } from "@/lib/types";
import { fetchProject, triggerAutoPilot } from "@/lib/api";
import {
  Sparkles,
  Zap,
  Film,
  FileText,
  Mic,
  ImageIcon,
  Clapperboard,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Play,
  ArrowRight,
  Youtube,
  ExternalLink,
} from "lucide-react";

interface AutoPilotModalProps {
  isOpen: boolean;
  project: Project | null;
  onClose: () => void;
  onCompleted: (updated: Project) => void;
  onNavigateTab: (tab: "video" | "thumbnail" | "script") => void;
}


export function AutoPilotModal({
  isOpen,
  project,
  onClose,
  onCompleted,
  onNavigateTab,
}: AutoPilotModalProps) {
  const [progressPercent, setProgressPercent] = useState(15);
  const [statusMessage, setStatusMessage] = useState("Initializing Auto-Pilot engine...");
  const [isRunning, setIsRunning] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadInfo, setUploadInfo] = useState<{
    uploaded?: boolean;
    video_id?: string;
    youtube_url?: string;
    studio_url?: string;
    channel_title?: string;
    state?: string;
    error?: string;
  } | null>(null);

  const runningRef = useRef(false);

  useEffect(() => {
    if (isOpen && project && !runningRef.current) {
      startPipeline();
    }
  }, [isOpen, project?.id]);

  const startPipeline = async () => {
    if (!project || runningRef.current) return;
    runningRef.current = true;
    setIsRunning(true);
    setIsDone(false);
    setError(null);
    setUploadInfo(null);
    setProgressPercent(15);
    setStatusMessage("Checking and downloading trailers for every movie...");

    // Advance only when the backend has actually reached the next stage.
    let polling = false;
    let finished = false;
    const progressTimer = setInterval(async () => {
      if (polling) return;
      polling = true;
      try {
        const latest = await fetchProject(project.id);
        if (finished) return;
        const pct = latest.progress_percent;
        setProgressPercent(pct);
        if (latest.notes) {
          setStatusMessage(latest.notes.replace(/^(Cinematic )?Auto-Pilot: /, ""));
        }
      } catch {
        // The pipeline response remains authoritative if polling temporarily fails.
      } finally {
        polling = false;
      }
    }, 1500);

    try {
      const res = await triggerAutoPilot(project.id, {
        pipeline_mode: "cinematic",
        auto_upload: true,
      });
      finished = true;
      clearInterval(progressTimer);

      if (res.youtube_upload) {
        setUploadInfo(res.youtube_upload);
      }

      setProgressPercent(100);
      setStatusMessage(
        res.youtube_upload?.uploaded
          ? `Uploaded as Private Review to ${res.youtube_upload.channel_title || "YouTube"}!`
          : "1-Click Short generated successfully!"
      );
      setIsDone(true);
      onCompleted(res.project);
    } catch (err: any) {
      finished = true;
      clearInterval(progressTimer);
      setError(err.message || "Auto-Pilot generation failed. Please try again.");
    } finally {
      finished = true;
      clearInterval(progressTimer);
      runningRef.current = false;
      setIsRunning(false);
    }
  };

  if (!isOpen || !project) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl rounded-3xl glass-panel p-6 sm:p-8 my-8 shadow-2xl border border-white/[0.1] text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between pb-5 border-b border-white/[0.08]">
          <div className="flex items-center gap-3.5">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-amber-500 via-rose-500 to-indigo-600 shadow-lg shadow-amber-950/50">
              <Zap className="h-6 w-6 text-white animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-black text-white tracking-tight">1-Click Auto-Pilot Shorts Engine</h2>
                <span className="rounded-full bg-amber-500/20 px-2.5 py-0.5 text-[10px] font-black text-amber-300 border border-amber-500/30">
                  AUTONOMOUS
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {project.title} • Verified trailers, script, voice, thumbnail & video composition
              </p>
            </div>
          </div>

          {!isRunning && (
            <button
              onClick={onClose}
              className="rounded-full p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mt-4 rounded-2xl bg-red-500/10 border border-red-500/20 p-4 text-xs font-semibold text-red-400 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 shrink-0 text-red-400 mt-0.5" />
            <div className="flex-1">
              <p>{error}</p>
              <button
                onClick={startPipeline}
                className="mt-2 text-xs font-bold text-red-300 underline hover:text-white"
              >
                Retry Auto-Pilot
              </button>
            </div>
          </div>
        )}

        {/* Progress Bar & Status */}
        <div className="mt-6 rounded-2xl bg-slate-900/60 border border-white/[0.06] p-4">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="font-bold text-slate-300 flex items-center gap-2">
              {isRunning && <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />}
              {statusMessage}
            </span>
            <span className="font-black text-amber-400">{progressPercent}%</span>
          </div>

          <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-amber-500 via-rose-500 to-pink-500 transition-all duration-700 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Connected production flow uses actual backend status. */}
        <div className="mt-5"><AutoPilotFlow progress={progressPercent} message={statusMessage} state={error ? "FAILED" : isDone ? "COMPLETED" : isRunning ? "RUNNING" : "QUEUED"} showPublishing /></div>

        {/* Completion Footer */}
        {isDone && (
          <div className="mt-6 flex flex-col gap-4 border-t border-white/[0.08] pt-5 animate-in fade-in duration-300">
            {/* YouTube Auto-Upload Banner */}
            {uploadInfo?.uploaded ? (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl bg-gradient-to-r from-red-950/40 via-red-900/20 to-slate-900/40 border border-red-500/30 p-4 shadow-lg shadow-red-950/30">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-600 text-white shadow-md shadow-red-900/50">
                    <Youtube className="h-5 w-5 fill-current" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-black text-white">
                        Uploaded to {uploadInfo.channel_title || "YouTube"}
                      </span>
                      <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[9px] font-black text-emerald-300 border border-emerald-500/30 uppercase">
                        Private Review
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Short is ready for your review in YouTube Studio before going public
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {uploadInfo.youtube_url && (
                    <a
                      href={uploadInfo.youtube_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 rounded-xl bg-red-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-red-500 transition shadow-md shadow-red-950/40"
                    >
                      <Youtube className="h-3.5 w-3.5 fill-current" />
                      <span>Watch Short</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                  {uploadInfo.studio_url && (
                    <a
                      href={uploadInfo.studio_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 rounded-xl bg-slate-800 px-3 py-1.5 text-xs font-bold text-slate-200 hover:bg-slate-700 hover:text-white transition border border-white/[0.08]"
                    >
                      <span>Studio</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              </div>
            ) : uploadInfo?.error ? (
              <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 px-3.5 py-2 text-[11px] text-amber-300 flex items-center justify-between">
                <span>YouTube Auto-Upload: {uploadInfo.error}</span>
                <span className="text-[10px] text-slate-400">Local video ready below</span>
              </div>
            ) : null}

            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>Full YouTube Short Ready to Publish!</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateTab("thumbnail");
                  }}
                  className="flex items-center gap-1.5 rounded-2xl bg-slate-800 px-4 py-2 text-xs font-bold text-slate-200 hover:bg-slate-700 transition"
                >
                  <ImageIcon className="h-3.5 w-3.5" />
                  <span>Thumbnail</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onNavigateTab("video");
                  }}
                  className="flex items-center gap-1.5 rounded-2xl bg-gradient-to-r from-rose-600 via-pink-600 to-amber-500 px-5 py-2 text-xs font-bold text-white shadow-lg shadow-rose-950/50 hover:scale-[1.02] active:scale-95 transition glow-rose"
                >
                  <Play className="h-3.5 w-3.5 fill-current" />
                  <span>Watch Short</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
