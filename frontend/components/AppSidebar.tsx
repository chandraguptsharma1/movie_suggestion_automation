"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Search, Layers, Clapperboard, Upload, X, ArrowUpRight, Clock3, MonitorPlay } from 'lucide-react';

const PAGES = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard, detail: 'Your studio overview' },
  { href: '/movies', label: 'Movie Search', icon: Search, detail: 'Browse by year & category' },
  { href: '/queue', label: 'Processing Queue', icon: Clock3, detail: 'One movie at a time' },
  { href: '/lineups', label: 'My Lineups', icon: Layers, detail: 'Saved movie projects' },
  { href: '/studio', label: 'Shorts Studio', icon: Clapperboard, detail: 'Create and edit your Short' },
  { href: '/long-videos', label: 'Long Videos', icon: MonitorPlay, detail: 'Plan a 7-movie review' },
  { href: '/uploads', label: 'YouTube Uploads', icon: Upload, detail: 'Upload, review & schedule' },
];

export function AppSidebar({ onClose, projectCount }: { onClose: () => void; projectCount: number }) {
  const pathname = usePathname();
  return <div className="flex h-full min-h-0 flex-col">
    <div className="flex items-center justify-between border-b border-white/[.06] px-4 py-3.5">
      <div><p className="text-[9px] font-semibold uppercase tracking-[.18em] text-slate-500">Creator workspace</p><h2 className="mt-1 text-sm font-bold text-white">Movie Studio</h2></div>
      <button type="button" onClick={onClose} aria-label="Close navigation" className="rounded-lg p-2 text-slate-300 hover:bg-white/10 lg:hidden"><X className="h-5 w-5" /></button>
    </div>
    <nav aria-label="Main navigation" className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
      {PAGES.map(page => {
        const active = pathname === page.href || (page.href !== '/' && pathname === `${page.href}/`);
        return <Link key={page.href} href={page.href} onClick={onClose} aria-current={active ? 'page' : undefined}
          className={`flex min-h-11 items-center gap-2.5 rounded-lg border px-2.5 py-2 transition ${active ? 'border-rose-400/20 bg-rose-500/10 text-rose-200' : 'border-transparent text-slate-400 hover:border-white/10 hover:bg-white/5 hover:text-white'}`}>
          <page.icon className="h-4 w-4 shrink-0" />
          <span className="min-w-0 flex-1"><span className="block text-xs font-medium">{page.label}</span><span className="mt-0.5 block truncate text-[10px] text-slate-500">{page.detail}</span></span>
          {page.href === '/lineups' ? <span className="rounded bg-slate-950 px-1.5 py-0.5 text-[10px] text-slate-300">{projectCount}</span> : active ? <ArrowUpRight className="h-3 w-3 shrink-0" /> : null}
        </Link>;
      })}
    </nav>
    <div className="m-2 rounded-lg border border-amber-400/10 bg-amber-400/5 p-3"><p className="flex items-center gap-1.5 text-[10px] font-medium text-amber-200"><Clock3 className="h-3 w-3" /> Daily publishing</p><p className="mt-1 text-base font-bold text-white">6:30 PM <span className="text-[10px] font-normal text-slate-400">IST</span></p><p className="mt-1 text-[10px] text-slate-500">Next available day, after Studio checks.</p></div>
  </div>;
}
