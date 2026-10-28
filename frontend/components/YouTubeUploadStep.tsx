"use client";

import { DownloadThumbnailButton } from "./DownloadThumbnailButton";
import { getThumbnailImageUrl } from "@/lib/api";
import { useState } from 'react';
import type { Project } from '@/lib/types';
import { YouTubeUploadPanel } from './YouTubeUploadPanel';

export function YouTubeUploadStep({ project }: { project: Project }) {
  const script = project.script_data_json;
  const [title, setTitle] = useState(script?.youtube_title || project.title);
  const [description, setDescription] = useState(script?.youtube_description || '');
  const [tags, setTags] = useState((script?.tags || []).join(', '));
  const field = 'w-full rounded-xl border border-white/10 bg-slate-950 p-3 text-sm text-white';
  return <div className="space-y-5 rounded-3xl glass-panel p-5">
    <div><h2 className="text-lg font-bold text-white">YouTube upload &amp; checks</h2>
      <p className="mt-1 text-xs text-slate-400">Final MP4 uploads privately first. Ending-frame thumbnail is set separately; publish after Studio review.</p></div>
    {!project.final_video_path && <p className="rounded-xl bg-amber-500/10 p-3 text-sm text-amber-200">Pehle thumbnail ke saath final Short compose karein.</p>}
    <label className="block space-y-2 text-xs text-slate-300">Title · maximum 100 characters<input aria-label="YouTube title" className={field} maxLength={100} value={title} onChange={e => setTitle(e.target.value)} /></label>
    <label className="block space-y-2 text-xs text-slate-300">Description<textarea aria-label="YouTube description" className={field} rows={7} value={description} onChange={e => setDescription(e.target.value)} /></label>
    <label className="block space-y-2 text-xs text-slate-300">Tags · comma separated<input aria-label="YouTube tags" className={field} value={tags} onChange={e => setTags(e.target.value)} /></label>
    {project.thumbnail_path && <DownloadThumbnailButton url={getThumbnailImageUrl(project.id)} filename={`shorts-thumbnail-${project.id}.jpg`} />}
    <YouTubeUploadPanel movieId={project.id} ready={Boolean(project.final_video_path && project.status === 'COMPLETED')} metadata={{ title, description, tags: tags.split(',').map(t => t.trim()).filter(Boolean),
      hashtags: script?.hashtags || [], category: 'Film & Animation', scheduledAt: '' }} />
  </div>;
}
