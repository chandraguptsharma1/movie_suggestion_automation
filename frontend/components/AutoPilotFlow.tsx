"use client";

import { Fragment } from 'react';
import { Film, ImageIcon, Scissors, Mic, Clapperboard, ArrowRight, Check, Loader2, AlertCircle, Upload, ShieldCheck, CalendarClock } from 'lucide-react';

const stages = [
  { label: 'Trailers', detail: 'Find & download', icon: Film },
  { label: 'Thumbnail', detail: 'Poster & end card', icon: ImageIcon },
  { label: 'AI scenes', detail: 'Choose the shots', icon: Scissors },
  { label: 'Script & voice', detail: 'Hindi narration', icon: Mic },
  { label: 'Video render', detail: 'Captions & music', icon: Clapperboard },
];

// Cinematic rendering reports its own progress range. Prefer the real stage
// message so narration/rendering cannot jump back to the trailer icon.
export function getAutoPilotStage(progress: number, message: string) {
  if (/rendering paced|captions and music|ffmpeg|auto-upload|ready locally|completed|video is ready/i.test(message)) return 4;
  if (/narration|recording|composing cinematic|hindi script|voice|tts/i.test(message)) return 3;
  if (/scene|high-energy/i.test(message)) return 2;
  if (/thumbnail|end card/i.test(message)) return 1;
  if (/trailer|footage|initializ/i.test(message)) return 0;
  return progress >= 85 ? 4 : progress >= 60 ? 3 : progress >= 45 ? 2 : progress >= 30 ? 1 : 0;
}

export function AutoPilotFlow({ progress = 0, message = '', state = 'QUEUED', showPublishing = false }: {
  progress?: number; message?: string; state?: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED'; showPublishing?: boolean;
}) {
  const current = getAutoPilotStage(progress, message);
  return <div className="min-w-0">
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[10px]">
      <span className="font-semibold uppercase tracking-widest text-slate-400">Auto-Pilot flow</span>
      <span className={state === 'FAILED' ? 'text-rose-300' : state === 'RUNNING' ? 'text-amber-200' : 'text-slate-500'}>
        {state === 'COMPLETED' ? 'Video ready' : state === 'RUNNING' ? `${stages[current].label} · ${progress}%` : state === 'FAILED' ? 'Needs attention' : 'Waiting to start'}
      </span>
    </div>
    <ol aria-label="Auto-Pilot production flow" className="flex min-w-0 flex-col sm:flex-row">
      {stages.map((stage, index) => {
        const done = state === 'COMPLETED' || (state !== 'QUEUED' && index < current);
        const active = state !== 'COMPLETED' && state !== 'QUEUED' && index === current;
        const failed = active && state === 'FAILED';
        const Icon = stage.icon;
        const status = done ? 'Done' : failed ? 'Failed' : active ? 'Running' : 'Pending';
        return <li key={stage.label} aria-current={active ? 'step' : undefined} className="flex min-w-0 flex-col sm:flex-1 sm:flex-row sm:items-center">
          <div className={`flex min-w-0 flex-1 items-center gap-2 rounded-xl border p-2.5 sm:flex-col sm:gap-1.5 sm:px-1.5 sm:text-center ${done ? 'border-teal-400/25 bg-teal-400/[.06]' : failed ? 'border-rose-400/50 bg-rose-500/10' : active ? 'border-amber-400/50 bg-amber-400/[.08] shadow-[0_0_18px_-8px_#fbbf24]' : 'border-white/[.06] bg-slate-950/40'}`}>
            <span className={`relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${done ? 'bg-teal-400/15 text-teal-300' : failed ? 'bg-rose-400/15 text-rose-300' : active ? 'bg-amber-400/15 text-amber-200' : 'bg-slate-800/60 text-slate-500'}`}>
              <Icon className="h-4 w-4" />
              {active && !failed && <span className="absolute inset-0 rounded-xl ring-1 ring-amber-300/40 motion-safe:animate-pulse" />}
              {done && <Check aria-hidden="true" className="absolute -right-1 -top-1 h-3.5 w-3.5 rounded-full bg-teal-300 p-0.5 text-slate-950" />}
            </span>
            <span className="min-w-0 flex-1"><span className={`block text-[11px] font-semibold ${done ? 'text-teal-200' : active ? 'text-white' : 'text-slate-400'}`}>{stage.label}</span><span className="mt-0.5 block text-[9px] text-slate-500">{stage.detail}</span></span>
            <span className={`flex items-center gap-1 text-[9px] ${done ? 'text-teal-300' : failed ? 'text-rose-300' : active ? 'text-amber-200' : 'text-slate-600'}`}>{active && (failed ? <AlertCircle className="h-2.5 w-2.5" /> : <Loader2 className="h-2.5 w-2.5 motion-safe:animate-spin" />)}{status}</span>
          </div>
          {index < stages.length - 1 && <ArrowRight aria-hidden="true" className={`my-1 h-4 w-4 shrink-0 self-center rotate-90 sm:mx-1 sm:my-0 sm:rotate-0 ${done ? 'text-teal-400/70' : active ? 'text-amber-300 motion-safe:animate-pulse' : 'text-slate-700'}`} />}
        </li>;
      })}
    </ol>
    {showPublishing && <div className="mt-3 border-t border-white/[.06] pt-3">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-slate-400">{[
        {label:'Private upload',icon:Upload}, {label:'Copyright & cover check',icon:ShieldCheck}, {label:'6:30 PM IST schedule',icon:CalendarClock},
      ].map((step,index) => <Fragment key={step.label}>{index > 0 && <ArrowRight aria-hidden="true" className="h-3 w-3 text-slate-600" />}<span className="flex items-center gap-1.5"><step.icon className="h-3 w-3" />{step.label}</span></Fragment>)}</div>
      <p className="mt-1.5 text-[9px] text-slate-500">Publishing continues separately. Scheduling waits for verified Studio checks and the correct cover.</p>
    </div>}
  </div>;
}
