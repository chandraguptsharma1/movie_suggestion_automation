"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowUpRight, Film, Clapperboard, MonitorPlay, Clock3, CheckCircle2, ListVideo, RefreshCw } from 'lucide-react';
import { API_BASE_URL } from '@/lib/api';
import { fetchQueue, type QueueItem } from '@/lib/processingQueueApi';
import type { Project } from '@/lib/types';
import type { PublishingAutomation } from '@/lib/youtubeUploadApi';

type Release = PublishingAutomation & { publish_at?: string; title?: string };
const panel = 'rounded-xl border border-white/[.08] bg-slate-900/60';
const activeStates = ['QUEUED', 'RUNNING'];

async function loadPublishing(): Promise<Release[]> {
  const response = await fetch(`${API_BASE_URL}/publishing-automation`, {cache:'no-store', signal:AbortSignal.timeout(10000)});
  if (!response.ok) throw new Error('Publishing status unavailable');
  const items: Release[] = await response.json();
  return Promise.all(items.map(async item => {
    if (item.state !== 'SCHEDULED') return item;
    try {
      const upload = await fetch(`${API_BASE_URL}/youtube-upload/${item.project_id}`, {cache:'no-store',signal:AbortSignal.timeout(10000)});
      if (!upload.ok) return item;
      const {job} = await upload.json();
      return {...item, publish_at: job?.publish_at, title: job?.title};
    } catch { return item; }
  }));
}

export function StudioDashboard({ projects, onOpenProject }: { projects: Project[]; onOpenProject: (id: number) => void }) {
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [releases, setReleases] = useState<Release[] | null>(null);
  const [notice, setNotice] = useState('');
  const [checked, setChecked] = useState<Date | null>(null);
  useEffect(() => {
    let active = true, pending = false;
    async function refresh() {
      if (pending) return;
      pending = true;
      const results = await Promise.allSettled([
        fetchQueue(),
        loadPublishing(),
      ]);
      if (active) {
        setQueue(results[0].status === 'fulfilled' ? results[0].value : null);
        setReleases(results[1].status === 'fulfilled' ? results[1].value : null);
        setNotice(results.some(result => result.status === 'rejected') ? 'Live status unavailable. Saved projects are still shown; check the backend connection.' : '');
        if (results.every(result => result.status === 'fulfilled')) setChecked(new Date());
      }
      pending = false;
    }
    void refresh(); const timer = setInterval(() => void refresh(), 15000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  const ready = projects.filter(project => project.status === 'COMPLETED' && project.final_video_path);
  const working = queue?.filter(item => activeStates.includes(item.state)) || [];
  const scheduled = releases?.filter(item => item.state === 'SCHEDULED')
    .sort((a,b) => (a.publish_at ? Date.parse(a.publish_at) : Infinity) - (b.publish_at ? Date.parse(b.publish_at) : Infinity)) || [];
  const waiting = releases?.filter(item => !['SCHEDULED', 'PUBLISHED'].includes(item.state)) || [];
  const needsAttention = (queue?.filter(item => item.state === 'FAILED').length || 0) +
    (releases?.filter(item => ['HELD', 'ATTENTION', 'RETRY_PENDING'].includes(item.state)).length || 0);
  const stats = [
    { label: 'Saved projects', value: projects.length, icon: Film, detail: 'Your workspace', color: 'text-slate-300' },
    { label: 'Videos ready', value: ready.length, icon: CheckCircle2, detail: 'Local exports', color: 'text-teal-300' },
    { label: 'In processing', value: queue ? working.length : '—', icon: ListVideo, detail: 'One movie at a time', color: 'text-amber-300' },
    { label: 'Scheduled', value: releases ? scheduled.length : '—', icon: Clock3, detail: '6:30 PM IST releases', color: 'text-violet-300' },
  ];
  return <div className="space-y-3">
    {notice && <p role="status" className="rounded-lg border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-xs text-amber-200">{notice}</p>}
    <div className="grid grid-cols-2 gap-2.5 xl:grid-cols-4">{stats.map(stat => <div key={stat.label} title={stat.detail} className={`${panel} flex items-start justify-between gap-2 p-3`}>
      <div><p className="text-xs text-slate-400">{stat.label}</p><p className="mt-1 text-2xl font-bold leading-none tracking-tight text-white">{stat.value}</p></div>
      <span className={`rounded-lg bg-white/[.04] p-2 ${stat.color}`}><stat.icon className="h-4 w-4" /></span>
    </div>)}</div>

    <div className="grid gap-3 md:grid-cols-2">
      <Link href="/movies" className={`${panel} group flex min-w-0 items-center gap-3 p-3 transition hover:border-rose-400/40`}>
        <span className="rounded-xl bg-rose-500/10 p-2.5 text-rose-300"><Clapperboard className="h-5 w-5" /></span>
        <div className="min-w-0 flex-1"><p className="font-semibold text-white">Create a Short <span className="ml-1.5 text-[10px] font-normal text-slate-500">9:16</span></p><p className="mt-1 text-xs text-slate-400">Select a movie. Auto-Pilot handles the queue.</p></div><ArrowUpRight className="h-4 w-4 shrink-0 text-slate-500 group-hover:text-rose-300" />
      </Link>
      <Link href="/long-videos" className="group flex min-w-0 items-center gap-3 rounded-xl border border-violet-400/20 bg-gradient-to-r from-violet-500/10 to-slate-900 p-3 transition hover:border-violet-400/50">
        <span className="rounded-xl bg-violet-400/10 p-2.5 text-violet-300"><MonitorPlay className="h-5 w-5" /></span>
        <div className="min-w-0 flex-1"><p className="font-semibold text-white">Plan a long video <span className="ml-1.5 text-[10px] font-normal text-violet-300">16:9</span></p><p className="mt-1 text-xs text-slate-400">Build your 7-movie review lineup.</p></div><ArrowUpRight className="h-4 w-4 shrink-0 text-violet-300" />
      </Link>
    </div>

    <div className="grid items-start gap-3 xl:grid-cols-[minmax(0,1fr)_280px] 2xl:grid-cols-[minmax(0,1fr)_320px]">
      <section className={`${panel} min-w-0 overflow-hidden`}>
        <div className="flex items-center justify-between border-b border-white/[.06] px-4 py-3"><h2 className="text-sm font-semibold text-white">Recent projects <span className="ml-1 text-xs font-normal text-slate-500">{projects.length}</span></h2><Link href="/lineups" className="text-xs text-slate-400 hover:text-white">View all →</Link></div>
        <div className="grid grid-cols-[minmax(0,1fr)_88px_24px] gap-3 bg-slate-950/30 px-4 py-2 text-[10px] font-medium uppercase tracking-wider text-slate-500 sm:grid-cols-[minmax(0,1fr)_100px_88px_24px]"><span>Project / movie</span><span className="hidden sm:block">Progress</span><span>Status</span><span /></div>
        {projects.slice(0, 7).map(project => <button key={project.id} onClick={() => onOpenProject(project.id)} className="grid w-full grid-cols-[minmax(0,1fr)_88px_24px] items-center gap-3 border-t border-white/[.045] px-4 py-1 text-left transition hover:bg-white/[.025] sm:grid-cols-[minmax(0,1fr)_100px_88px_24px]">
          <span className="flex min-w-0 items-center gap-2.5"><span className="flex h-8 w-6 shrink-0 items-center justify-center overflow-hidden rounded bg-slate-800">{project.movies_json?.[0]?.poster_url ? <img src={project.movies_json[0].poster_url} alt="" className="h-full w-full object-cover" /> : <Film className="h-3 w-3 text-slate-500" />}</span><span className="min-w-0"><span className="block truncate text-xs font-semibold text-slate-200">{project.movies_json?.[0]?.title || project.title}</span><span className="mt-0.5 block truncate text-[10px] text-slate-500">{project.job_code} · {project.movie_count} {project.movie_count === 1 ? 'movie' : 'movies'}</span></span></span>
          <span className="hidden items-center gap-2 sm:flex"><span className="h-1 flex-1 overflow-hidden rounded-full bg-slate-800"><span className={`block h-full rounded-full ${project.status === 'COMPLETED' ? 'bg-teal-400/70' : 'bg-rose-400/70'}`} style={{width: `${Math.min(100, Math.max(0, project.progress_percent))}%`}} /></span><span className="text-[10px] tabular-nums text-slate-500">{project.progress_percent}%</span></span>
          <span className={`w-fit max-w-full truncate rounded px-2 py-1 text-[10px] font-medium ${project.status === 'COMPLETED' ? 'bg-teal-400/10 text-teal-300' : /ERROR|FAILED|REQUIRED/.test(project.status) ? 'bg-amber-400/10 text-amber-200' : 'bg-slate-800 text-slate-400'}`}>{project.status === 'COMPLETED' ? 'Ready' : project.status.replaceAll('_', ' ').toLowerCase()}</span><ArrowUpRight className="h-3.5 w-3.5 text-slate-500" />
        </button>)}
        {!projects.length && <div className="px-4 py-10 text-center"><Film className="mx-auto mb-2 h-5 w-5 text-slate-600" /><p className="text-xs text-slate-400">Your projects will appear here.</p><Link href="/movies" className="mt-2 inline-block text-xs text-rose-300">Find your first movie →</Link></div>}
      </section>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
        <section className={`${panel} p-3.5`}>
          <div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-white">Publishing</h2><span className="rounded bg-violet-400/10 px-1.5 py-0.5 text-[10px] text-violet-200">18:30 IST</span></div>
          <p className="mt-1 text-[11px] text-slate-500">Next available day after Studio review.</p>
          <div className="mt-3 space-y-2.5">{scheduled.slice(0, 3).map(release => {
            const project = projects.find(item => item.id === release.project_id);
            return <Link key={release.project_id} href={`/uploads?project=${release.project_id}`} className="flex items-center gap-2.5 rounded-lg bg-slate-950/50 p-2 hover:bg-slate-800/50"><span className="h-1.5 w-1.5 shrink-0 rounded-full bg-violet-300" /><span className="min-w-0 flex-1"><span className="block truncate text-xs text-slate-200">{project?.movies_json?.[0]?.title || `Project #${release.project_id}`}</span><span className="mt-0.5 block text-[10px] text-slate-500">{release.publish_at ? new Date(release.publish_at).toLocaleDateString('en-IN', {day:'numeric',month:'short',timeZone:'Asia/Kolkata'}) : 'Date unavailable'} · 6:30 PM IST</span></span><ArrowUpRight className="h-3 w-3 text-slate-600" /></Link>;
          })}{!scheduled.length && <p className="py-2 text-xs text-slate-500">{releases ? 'No scheduled videos yet.' : 'Waiting for publishing status…'}</p>}</div>
          <div className="mt-3 flex justify-between border-t border-white/[.06] pt-2.5 text-[11px] text-slate-400"><span>{releases ? waiting.length : '—'} awaiting checks</span><Link href="/uploads" className="text-violet-300">Open uploads →</Link></div>
        </section>
        <section className={`${panel} p-3.5`}>
          <div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-white">Processing queue</h2><Link href="/queue" aria-label="Open processing queue"><ArrowUpRight className="h-3.5 w-3.5 text-slate-500" /></Link></div>
          {working.length ? <div className="mt-3 space-y-2">{working.slice(0, 2).map(item => <div key={item.id} className="flex items-center justify-between gap-2 text-xs"><span className="truncate text-slate-300">{item.title}</span><span className="shrink-0 text-amber-300">{item.state === 'RUNNING' ? `${item.progress}%` : 'Queued'}</span></div>)}</div> : <p className="mt-2 text-xs text-slate-500">{queue ? 'Queue is clear. Ready for the next movie.' : 'Waiting for queue status…'}</p>}
          {needsAttention > 0 && <Link href="/queue" className="mt-3 block rounded-lg bg-amber-400/5 px-2 py-1.5 text-xs text-amber-200">{needsAttention} {needsAttention === 1 ? 'item needs' : 'items need'} attention →</Link>}
        </section>
      </div>
    </div>
    <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-[10px] text-slate-500"><span>Private upload → Studio checks → scheduled release</span><span className="flex items-center gap-1.5"><RefreshCw className="h-3 w-3" />{checked ? `Updated ${checked.toLocaleTimeString('en-IN', {hour:'2-digit',minute:'2-digit',timeZone:'Asia/Kolkata'})} IST` : 'Connecting to live status'}</span></div>
  </div>;
}
