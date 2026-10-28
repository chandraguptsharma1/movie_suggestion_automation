"use client";

import { useState } from 'react';
import { API_BASE_URL } from '@/lib/api';
import type { Project } from '@/lib/types';

export type MusicSettings = { enabled: boolean; style: string; volume: number; ducking: boolean };
export const savedMusic = (project: Project): MusicSettings => ({
  enabled: project.bgm_data_json?.style === 'none' ? false : project.bgm_data_json?.enabled ?? true,
  style: project.bgm_data_json?.style === 'none' ? 'suspense' : project.bgm_data_json?.style || 'suspense',
  volume: project.bgm_data_json?.volume ?? 0.15,
  ducking: project.bgm_data_json?.ducking ?? true,
});

export function BackgroundMusicControls({ project, value, onChange, onProjectUpdated, disabled }: {
  project: Project; value: MusicSettings; onChange: (value: MusicSettings) => void;
  onProjectUpdated: (project: Project) => void; disabled: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [credit, setCredit] = useState(project.bgm_data_json?.custom_credit || '');

  async function result(response: Response) {
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
    onProjectUpdated(data.project);
    return data;
  }

  async function save() {
    setBusy(true); setMessage('');
    try {
      await result(await fetch(`${API_BASE_URL}/projects/${project.id}/bgm`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value),
      }));
      setMessage('Music settings saved for this project and Auto-Pilot. Re-compose to apply to the video.');
    } catch (err) { setMessage(err instanceof Error ? err.message : 'Music settings failed'); }
    finally { setBusy(false); }
  }

  async function upload(file?: File) {
    if (!file) return;
    setBusy(true); setMessage('');
    try {
      const form = new FormData(); form.append('file', file); form.append('credit', credit);
      const data = await result(await fetch(`${API_BASE_URL}/projects/${project.id}/bgm/upload`, { method: 'POST', body: form }));
      onChange({ enabled: true, style: 'custom', volume: data.music.volume, ducking: true });
      setMessage('Music uploaded. Preview and re-compose to apply it.');
    } catch (err) { setMessage(err instanceof Error ? err.message : 'Music upload failed'); }
    finally { setBusy(false); }
  }

  return (
    <fieldset disabled={disabled || busy} className="space-y-4 rounded-2xl border border-white/10 bg-slate-950/60 p-4 disabled:opacity-60">
      <legend className="px-2 text-sm font-bold text-white">Background music (YouTube Audio Library)</legend>
      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={value.enabled} onChange={e => onChange({ ...value, enabled: e.target.checked })} />
          Music enabled
        </label>
        <label className="flex w-full min-w-0 items-center gap-2 sm:w-auto">
          Style / Track
          <select
            aria-label="Music style"
            value={value.style}
            onChange={e => onChange({ ...value, style: e.target.value })}
            className="min-w-0 flex-1 rounded-lg border border-white/10 bg-slate-900 p-2 text-white"
          >
            <optgroup label="Top Recommended">
              <option value="suspense">Ticking Suspense (Ticking Beneath the Steel) · Default</option>
              <option value="mystery">Dark Mystery (Beneath The Floorboards)</option>
              <option value="epic">Dark Epic Cinematic (Beneath The Iron Sky)</option>
              <option value="ambient">Deep Tension (Before The Heavy Silence)</option>
            </optgroup>
            <optgroup label="Suspense & Thriller Pulse">
              <option value="concrete_heartbeat">Modern Rhythmic Pulse · Concrete Heartbeat</option>
              <option value="the_omen_of_impact">Action Tension · The Omen of Impact</option>
              <option value="winter_in_the_foundries">Industrial Suspense · Winter in the Foundries</option>
              <option value="the_heavy_weight_of_glass">Dramatic Tension · The Heavy Weight of Glass</option>
            </optgroup>
            <optgroup label="Crime & Mystery Investigation">
              <option value="midnight_on_the_pavement">Crime Noir · Midnight on the Pavement</option>
              <option value="the_midnight_inquiry">Detective Investigation · The Midnight Inquiry</option>
              <option value="trenchcoat_shadow">Classic Noir · Trenchcoat Shadow</option>
              <option value="a_broken_alibi">Suspense Whodunit · A Broken Alibi</option>
              <option value="beyond_the_gilded_gates">Grand Mystery · Beyond the Gilded Gates</option>
            </optgroup>
            <optgroup label="Ambient & Emotional Drama">
              <option value="orbits_over_water">Ethereal Ambient · Orbits Over Water</option>
              <option value="beyond_the_ridge">Adventure Drama · Beyond the Ridge</option>
              <option value="the_meridian_unfolds">Cinematic Odyssey · The Meridian Unfolds</option>
              <option value="sidewalks_and_secret_songs">Emotional Storytelling · Sidewalks & Secret Songs</option>
              <option value="where_giants_roam">Fantasy Tension · Where Giants Roam</option>
            </optgroup>
            <optgroup label="Light & Upbeat">
              <option value="a_case_for_lunch">Light Mystery · A Case for Lunch</option>
              <option value="sunday_morning_mischief">Upbeat Mischief · Sunday Morning Mischief</option>
            </optgroup>
            <optgroup label="Custom">
              <option value="custom" disabled={!project.bgm_data_json?.custom_path}>My uploaded music</option>
            </optgroup>
          </select>
        </label>
      </div>
      <label className="block space-y-2 text-xs text-slate-300">
        <span className="flex justify-between">
          <span>Music level · default 15%</span>
          <output>{Math.round(value.volume * 100)}%</output>
        </span>
        <input
          aria-label="Music volume"
          type="range"
          min="0"
          max="0.5"
          step="0.01"
          value={value.volume}
          onChange={e => onChange({ ...value, volume: Number(e.target.value) })}
          className="w-full accent-rose-500"
        />
      </label>
      <label className="flex items-center gap-2 text-xs text-slate-300">
        <input type="checkbox" checked={value.ducking} onChange={e => onChange({ ...value, ducking: e.target.checked })} />
        Auto ducking — voice bolte waqt music smooth duck karein
      </label>
      {value.enabled && (
        <div className="space-y-1">
          <audio
            key={value.style + (project.bgm_data_json?.custom_path || '')}
            controls
            preload="none"
            src={`${API_BASE_URL}/projects/${project.id}/bgm/preview/${value.style}`}
            className="h-10 w-full"
          />
          <p className="text-[10px] text-slate-500">Track preview. Final video composition me selected volume aur auto ducking apply honge.</p>
        </div>
      )}
      <details className="space-y-3 text-xs text-slate-300">
        <summary className="cursor-pointer font-semibold">Upload my music · max 25 MB</summary>
        <p>Apna original ya licensed track use karein. Upload karne se rights verify nahi hote.</p>
        <input
          aria-label="Music credits"
          value={credit}
          onChange={e => setCredit(e.target.value)}
          placeholder="Credit / attribution required by your license (optional)"
          maxLength={2000}
          className="w-full rounded-lg border border-white/10 bg-slate-900 p-2 text-white"
        />
        <input
          aria-label="Upload background music"
          type="file"
          accept=".mp3,.wav,.m4a,.aac,.ogg,.flac"
          onChange={e => void upload(e.target.files?.[0])}
          className="max-w-full"
        />
      </details>
      <button
        type="button"
        onClick={() => void save()}
        className="rounded-xl border border-white/10 bg-slate-800 px-3 py-2 text-xs font-semibold text-white"
      >
        {busy ? 'Saving music…' : 'Save for Auto-Pilot'}
      </button>
      <p className="text-[10px] text-emerald-400">
        ✓ YouTube Audio Library music: 100% royalty-free for YouTube videos, no copyright claims.
      </p>
      {project.bgm_data_json?.attribution && (
        <div className="space-y-2">
          <pre className="whitespace-pre-wrap break-words rounded-lg bg-slate-900 p-3 text-[10px] text-slate-300">
            {project.bgm_data_json.attribution}
          </pre>
          <button
            type="button"
            className="text-xs font-bold text-cyan-400"
            onClick={() =>
              void navigator.clipboard
                .writeText(project.bgm_data_json?.attribution || '')
                .then(
                  () => setMessage('Music credit copied.'),
                  () => setMessage('Select and copy the credit text above.')
                )
            }
          >
            Copy music credit
          </button>
        </div>
      )}
      {message && <p role="status" className="text-xs text-amber-200">{message}</p>}
    </fieldset>
  );
}
