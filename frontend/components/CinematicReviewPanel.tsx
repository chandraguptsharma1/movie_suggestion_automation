"use client";

import { useEffect, useState } from 'react';
import { API_BASE_URL, fetchProject } from '@/lib/api';
import type { Project } from '@/lib/types';

export function CinematicReviewPanel({ project, onOpen }: { project: Project; onOpen: (id: number) => void }) {
  const [result, setResult] = useState<Project | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const running = result?.status === 'CINEMATIC_RENDERING';
  useEffect(() => {
    if (!result || !running) return;
    let active = true, pending = false;
    const timer = setInterval(async () => {
      if (pending) return;
      pending = true;
      try { const next = await fetchProject(result.id); if (active) { setResult(next); setError(''); } }
      catch { if (active) setError('Progress connection interrupted. The render continues on the backend.'); }
      finally { pending = false; }
    }, 4000);
    return () => { active = false; clearInterval(timer); };
  }, [result?.id, running]);
  async function start() {
    setBusy(true); setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/projects/${project.id}/cinematic-review`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Cinematic review could not start');
      setResult(data);
    } catch (err) { setError(err instanceof Error ? err.message : 'Request failed'); }
    finally { setBusy(false); }
  }
  return <section className="rounded-2xl border border-amber-400/25 bg-amber-400/5 p-4 space-y-3">
    <div><h3 className="font-bold text-amber-200">Cinematic Review</h3>
      <p className="mt-1 text-sm text-slate-300">Story hook, narration-matched scenes, selective slow motion, transitions and bold centre-screen reveals. Hindi captions, music and cinematic colour treatment. Uses this movie’s prepared AI scenes and thumbnail to create a separate version.</p></div>
    <button type="button" onClick={() => void start()} disabled={busy || running || project.movie_count !== 1}
      className="rounded-xl bg-amber-400 px-4 py-2 text-sm font-bold text-slate-950 disabled:opacity-50">
      {busy ? 'Starting…' : running ? 'Creating cinematic review…' : 'Create cinematic version'}
    </button>
    {project.movie_count !== 1 && <p className="text-sm text-slate-400">Choose a single movie lineup for this mode.</p>}
    {result && <div role="status" className="space-y-2 text-sm text-slate-200">
      <p>{result.notes} · {result.progress_percent}%</p>
      {running && <progress aria-label="Cinematic render progress" value={result.progress_percent} max={100} className="w-full" />}
      {result.status === 'COMPLETED' && <button className="font-bold text-amber-200 underline" onClick={() => onOpen(Number(result.id))}>Open cinematic review</button>}
    </div>}
    {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
  </section>;
}
