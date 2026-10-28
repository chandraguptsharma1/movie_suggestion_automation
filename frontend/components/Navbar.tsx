"use client";

import React, { useEffect, useState } from "react";
import { API_BASE_URL } from '@/lib/api';
import { Clapperboard, Plus, Radio, Menu } from "lucide-react";

interface NavbarProps {
  onNewProject: () => void;
  projectCount: number;
  onOpenSidebar: () => void;
}

export function Navbar({ onNewProject, onOpenSidebar }: NavbarProps) {
  const [connected, setConnected] = useState<boolean | null>(null);
  useEffect(() => {
    let active = true, pending = false;
    async function check() {
      if (pending) return;
      pending = true;
      try {
        const response = await fetch(`${API_BASE_URL}/health`, {cache:'no-store', signal:AbortSignal.timeout(5000)});
        const data = response.ok ? await response.json() : null;
        if (active) setConnected(data?.status === 'healthy');
      } catch { if (active) setConnected(false); }
      finally { pending = false; }
    }
    void check(); const timer = setInterval(() => void check(), 30000);
    return () => { active = false; clearInterval(timer); };
  }, []);
  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.08] bg-slate-950/80 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-[1920px] items-center justify-between gap-2 px-3 sm:px-4">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3.5">
          <div className="relative hidden h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-tr from-rose-600 via-rose-500 to-amber-500 ring-1 ring-white/15 min-[400px]:flex">
            <Clapperboard className="h-4 w-4 text-white" />
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <span className="truncate font-bold text-sm text-white tracking-tight">
                Movie Studio
              </span>
              <span className="hidden xl:inline rounded-full bg-rose-500/10 px-2.5 py-0.5 text-[11px] font-bold text-rose-400 border border-rose-500/20">
                CREATOR DASHBOARD
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span role="status" className={`flex items-center gap-1 text-[10px] ${connected ? 'text-emerald-400' : connected === false ? 'text-amber-300' : 'text-slate-500'}`}>
                <Radio className="h-2.5 w-2.5" />
                {connected ? 'Backend connected' : connected === false ? 'Backend offline' : 'Connecting…'}
              </span>
              <span className="hidden md:inline">•</span>
              <span className="hidden md:inline text-[10px]">Shorts &amp; movie reviews</span>
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button type="button" onClick={onOpenSidebar} aria-label="Open navigation" className="flex min-h-11 items-center gap-2 rounded-xl border border-white/10 px-3 text-xs font-bold text-slate-200 lg:hidden"><Menu className="h-4 w-4" /><span className="hidden min-[380px]:inline">Pages</span></button>
          <button
            onClick={onNewProject}
            className="group relative flex min-h-9 items-center gap-1.5 overflow-hidden rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-rose-500"
          >
            <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
            <Plus className="relative z-10 h-4 w-4" />
            <span className="relative z-10"><span className="sm:hidden">Add movie</span><span className="hidden sm:inline">Add Movie to Queue</span></span>
          </button>
        </div>
      </div>
    </header>
  );
}
