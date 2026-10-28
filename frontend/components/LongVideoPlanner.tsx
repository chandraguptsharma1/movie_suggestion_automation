"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { MonitorPlay, Check, ArrowUp, ArrowDown, Save, Film } from 'lucide-react';
import type { Project } from '@/lib/types';

const DRAFT_KEY = 'movie_studio_long_video_draft_v1';
const identity = (project: Project) => `${project.movies_json?.[0]?.media_type || 'movie'}:${project.movies_json?.[0]?.tmdb_id || project.movies_json?.[0]?.title}`;

export function LongVideoPlanner({ projects }: { projects: Project[] }) {
  const [selected, setSelected] = useState<number[]>([]);
  const [title, setTitle] = useState('7 Hollywood movies for your next watchlist');
  const [saved, setSaved] = useState('');
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);
  // Reuse one prepared project per movie, preferring the newest export.
  const available = Array.from(new Map([...projects].sort((a, b) => b.id - a.id)
    .filter(project => project.movie_count === 1 && project.status === 'COMPLETED' && project.final_video_path)
    .map(project => [identity(project), project] as const).reverse()).values()).sort((a, b) => b.id - a.id);
  useEffect(() => {
    try {
      const draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null');
      if (draft) {
        if (typeof draft.title === 'string') setTitle(draft.title);
        if (Array.isArray(draft.project_ids)) setSelected([...new Set<number>(draft.project_ids.filter((id: unknown) => Number.isSafeInteger(id)))].slice(0, 7));
        if (typeof draft.saved_at === 'string') setSaved(draft.saved_at);
      }
    } catch { setError('Saved draft could not be opened. You can create a new lineup.'); }
    setLoaded(true);
  }, []);
  function change(ids: number[]) { setSelected(ids); setSaved(''); setError(''); }
  function move(index: number, offset: number) {
    const next = [...selected]; [next[index], next[index + offset]] = [next[index + offset], next[index]]; change(next);
  }
  function save() {
    if (selected.length !== 7 || !title.trim() || selected.some(id => !available.some(project => project.id === id))) {
      setError('Choose 7 available movie projects and add a title before saving.'); return;
    }
    try {
      const stamp = new Date().toISOString();
      localStorage.setItem(DRAFT_KEY, JSON.stringify({title: title.trim(), project_ids: selected, format: 'long_review', aspect_ratio: '16:9', target_minutes: '8–10', saved_at: stamp}));
      setSaved(stamp); setError('');
    } catch { setError('Draft could not be saved. Browser storage may be full or unavailable.'); }
  }
  return <div className="space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-violet-400/20 bg-violet-400/5 p-4">
      <div className="flex items-center gap-3"><span className="rounded-xl bg-violet-400/10 p-2.5 text-violet-300"><MonitorPlay className="h-5 w-5" /></span><div><h2 className="font-semibold text-white">7-movie cinematic review</h2><p className="mt-1 text-xs text-slate-400">16:9 Full HD · 8–10 minute target · Hindi narration</p></div></div>
      <span className="rounded-md border border-violet-300/20 px-2 py-1 text-[11px] text-violet-200">Lineup planning</span>
    </div>
    <div className="grid items-start gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
      <section className="min-w-0 overflow-hidden rounded-xl border border-white/[.08] bg-slate-900/60">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[.06] p-3"><div><h2 className="text-sm font-semibold text-white">Your prepared movies</h2><p className="mt-1 text-[11px] text-slate-500">Choose the movies to include in this review.</p></div><button disabled={!loaded || available.length < 7} onClick={() => change(available.slice(0, 7).map(project => project.id).reverse())} className="rounded-lg border border-white/10 px-2.5 py-2 text-xs text-violet-200 hover:bg-white/5 disabled:opacity-40">Use latest 7 ready</button></div>
        <div className="grid gap-2 p-3 sm:grid-cols-2">{available.map(project => {
          const movie = project.movies_json[0], chosen = selected.includes(project.id);
          return <button key={project.id} aria-pressed={chosen} disabled={!chosen && selected.length === 7} onClick={() => change(chosen ? selected.filter(id => id !== project.id) : [...selected, project.id])} className={`flex min-w-0 items-center gap-2.5 rounded-lg border p-2 text-left transition disabled:opacity-40 ${chosen ? 'border-violet-400/40 bg-violet-400/10' : 'border-white/[.06] bg-slate-950/40 hover:border-white/20'}`}>
            <span className="flex h-14 w-9 shrink-0 items-center justify-center overflow-hidden rounded bg-slate-800">{movie.poster_url ? <img src={movie.poster_url} alt="" className="h-full w-full object-cover" /> : <Film className="h-4 w-4 text-slate-500" />}</span>
            <span className="min-w-0 flex-1"><span className="block truncate text-xs font-semibold text-slate-200">{movie.title}</span><span className="mt-1 block text-[11px] text-slate-500">{movie.year || 'Year unavailable'} · Export ready</span></span><span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${chosen ? 'border-violet-400 bg-violet-500 text-white' : 'border-slate-600'}`}>{chosen && <Check className="h-3 w-3" />}</span>
          </button>;
        })}</div>
        {!available.length && <div className="p-8 text-center text-xs text-slate-400">Your completed single-movie projects will appear here.<Link href="/movies" className="mt-2 block text-violet-300">Find movies →</Link></div>}
      </section>
      <section className="rounded-xl border border-white/[.08] bg-slate-900/60 p-3.5">
        <div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-white">Review lineup</h2><span className="text-xs tabular-nums text-violet-300">{selected.length} / 7</span></div>
        <label className="mt-3 block text-[11px] text-slate-400">Video title<input aria-label="Long video title" maxLength={100} value={title} onChange={event => {setTitle(event.target.value); setSaved('');}} className="mt-1 w-full rounded-lg border border-white/10 bg-slate-950 px-2.5 py-2 text-xs text-slate-200" /></label>
        <ol className="mt-3 space-y-1.5">{selected.map((id, index) => <li key={id} className="flex items-center gap-2 rounded-lg bg-slate-950/60 p-2">
          <span className="text-[11px] tabular-nums text-slate-500">{index + 1}</span><span className="min-w-0 flex-1 truncate text-xs text-slate-200">{available.find(project => project.id === id)?.movies_json[0]?.title || `Unavailable project #${id}`}</span>
          <button aria-label={`Move movie ${index + 1} up`} disabled={index === 0} onClick={() => move(index, -1)} className="rounded p-1 text-slate-400 hover:bg-white/5 disabled:opacity-20"><ArrowUp className="h-3 w-3" /></button>
          <button aria-label={`Move movie ${index + 1} down`} disabled={index === selected.length - 1} onClick={() => move(index, 1)} className="rounded p-1 text-slate-400 hover:bg-white/5 disabled:opacity-20"><ArrowDown className="h-3 w-3" /></button>
        </li>)}</ol>
        {!selected.length && <p className="my-4 rounded-lg border border-dashed border-white/10 p-4 text-center text-xs text-slate-500">Select 7 movies to plan the review.</p>}
        <button disabled={!loaded || selected.length !== 7 || !title.trim()} onClick={save} className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-3 py-2.5 text-xs font-semibold text-white hover:bg-violet-500 disabled:opacity-40"><Save className="h-3.5 w-3.5" />Save lineup draft</button>
        {saved && <p role="status" className="mt-2 text-xs text-teal-300">Lineup saved on this browser.</p>}
        {error && <p role="alert" className="mt-2 text-xs text-rose-300">{error}</p>}
        <p className="mt-3 border-t border-white/[.06] pt-3 text-[11px] leading-relaxed text-slate-500">This saves your movie order. Script generation and long-video rendering are the next stage; saving does not start production or upload.</p>
      </section>
    </div>
  </div>;
}
