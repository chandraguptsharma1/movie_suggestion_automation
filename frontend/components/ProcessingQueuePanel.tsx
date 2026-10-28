"use client";
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchQueue, retryQueueItem, type QueueItem } from '@/lib/processingQueueApi';
import { AutoPilotFlow } from '@/components/AutoPilotFlow';

export function ProcessingQueuePanel() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<number | null>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let active = true, pending = false;
    async function refresh() {
      if (pending) return;
      pending = true;
      try { const next = await fetchQueue(); if (active) { setItems(next); setLoaded(true); setError(''); } }
      catch (err) { if (active) setError(err instanceof Error ? err.message : 'Queue unavailable'); }
      finally { pending = false; }
    }
    void refresh(); const timer = setInterval(() => void refresh(), 4000);
    return () => { active = false; clearInterval(timer); };
  }, []);
  const current = items.find(item => item.state === 'RUNNING') || items.find(item => item.state === 'QUEUED') || items.at(-1);
  return <section className="space-y-4 rounded-2xl border border-white/10 bg-slate-900/60 p-4 sm:p-6">
    <div><h2 className="text-xl font-bold text-white">Processing queue</h2>
      <p className="mt-2 text-sm text-slate-400">One movie → one Cinematic Short. Select movies in Movie Search; each starts automatically after the previous one finishes. Keep the backend running.</p>
      <p className="mt-1 text-xs text-slate-500">Failed movies stay here for retry; the next movie continues. Publishing follows after the video is ready.</p></div>
    <div className="rounded-xl border border-white/[.08] bg-slate-950/50 p-3 sm:p-4">
      {current && <p className="mb-3 truncate text-xs font-semibold text-slate-200">{current.title} {current.year && `(${current.year})`}</p>}
      <AutoPilotFlow progress={current?.progress} message={current?.step} state={current?.state} showPublishing />
    </div>
    <Link href="/movies" className="inline-block rounded-xl bg-rose-600 px-4 py-2 text-sm font-bold text-white">Add movies</Link>
    {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
    {!loaded && !error && <p className="text-slate-400">Loading queue…</p>}
    {loaded && !items.length && <p className="rounded-xl border border-dashed border-white/15 p-6 text-slate-400">Queue is empty. Select a movie to start automatically.</p>}
    <div className="space-y-3">{items.map((item, index) => <article key={item.id} className="min-w-0 rounded-xl border border-white/10 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-bold text-white">{index + 1}. {item.title} {item.year && `(${item.year})`}</h3><span className={`rounded-full px-3 py-1 text-xs font-bold ${item.state === 'FAILED' ? 'bg-rose-500/15 text-rose-300' : item.state === 'COMPLETED' ? 'bg-teal-500/15 text-teal-200' : 'bg-amber-500/15 text-amber-200'}`}>{item.state === 'COMPLETED' ? 'VIDEO READY' : item.state}</span></div>
      {item.state === 'RUNNING' && <><p className="mt-2 text-sm text-slate-300">{item.step}</p><progress aria-label={`${item.title} processing`} value={item.progress} max={100} className="mt-3 w-full accent-rose-500" /></>}
      {item.error && <p className="mt-2 break-words text-sm text-rose-300">{item.error}</p>}
      <div className="mt-3 flex flex-wrap gap-4 text-sm font-semibold">
        {item.project_id && <Link className="text-rose-300 underline" href={`/studio?project=${item.project_id}`}>Open movie</Link>}
        {item.state === 'FAILED' && <button disabled={busy === item.id} className="text-amber-200 underline disabled:opacity-50" onClick={async () => {
          setBusy(item.id); setError('');
          try { await retryQueueItem(item.id); setItems(await fetchQueue()); }
          catch (err) { setError(err instanceof Error ? err.message : 'Retry failed'); }
          finally { setBusy(null); }
        }}>Retry this movie</button>}
      </div>
    </article>)}</div>
  </section>;
}
