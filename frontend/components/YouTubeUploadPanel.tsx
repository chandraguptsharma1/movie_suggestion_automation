"use client";

import { useEffect, useRef, useState } from 'react';
import { ExternalLink, LoaderCircle } from 'lucide-react';
import { API_BASE_URL } from '@/lib/api';
import { DownloadThumbnailButton } from './DownloadThumbnailButton';
import {
  getUploadJob, getUploadAccount, getPublishingAutomation, enablePublishingAutomation,
  connectYouTube, type UploadJob, type UploadAccount, type PublishingAutomation, type YouTubeMetadata,
} from '@/lib/youtubeUploadApi';

export function YouTubeUploadPanel({ movieId, metadata, ready = true, onPublishedChange }: {
  movieId: string | number; metadata: YouTubeMetadata; ready?: boolean; onPublishedChange?: (done: boolean) => void;
}) {
  const [job, setJob] = useState<UploadJob | null>(null);
  const [account, setAccount] = useState<UploadAccount | null>(null);
  const [automation, setAutomation] = useState<PublishingAutomation | null>(null);
  const [error, setError] = useState('');
  const [connecting, setConnecting] = useState(false);
  const metadataRef = useRef(metadata);
  metadataRef.current = metadata;
  const callbackOrigin = useRef('');

  async function connect() {
    const popup = window.open('', 'youtube-account-connect', 'width=600,height=760');
    try {
      const result = await connectYouTube(movieId);
      callbackOrigin.current = new URL(result.redirect_uri).origin;
      if (!popup) throw new Error('Allow popups to connect your YouTube channel.');
      popup.location.href = result.auth_url;
      setConnecting(true);
    } catch (err) { popup?.close(); setError(err instanceof Error ? err.message : 'Connection failed'); }
  }

  useEffect(() => {
    let active = true, pending = false;
    setJob(null); setAutomation(null); setAccount(null); setError('');
    async function refresh() {
      if (pending) return;
      pending = true;
      try {
        const [upload, auto, auth] = await Promise.all([getUploadJob(movieId), getPublishingAutomation(movieId), getUploadAccount()]);
        if (!active) return;
        setJob(upload.job); setAutomation(auto.automation); setAccount(auth);
        if (auth.is_authenticated) setConnecting(false);
        if (ready && !auto.automation) {
          const current = metadataRef.current;
          const hashtags = current.hashtags.filter(tag => !current.description.includes(tag)).join(' ');
          const queued = await enablePublishingAutomation(movieId, {
            title: current.title, description: [current.description, hashtags].filter(Boolean).join('\n\n'),
            tags: current.tags, category_id: '24', made_for_kids: false,
          });
          if (active) setAutomation(queued);
        }
        if (active) setError('');
      } catch (err) { if (active) setError(err instanceof Error ? err.message : 'Automatic upload status unavailable'); }
      finally { pending = false; }
    }
    void refresh();
    const timer = setInterval(() => void refresh(), 10000);
    const receive = (event: MessageEvent) => {
      if (event.origin === callbackOrigin.current && event.data?.type === 'youtube-connected') void refresh();
    };
    window.addEventListener('message', receive);
    return () => { active = false; clearInterval(timer); window.removeEventListener('message', receive); };
  }, [movieId, ready]);

  useEffect(() => { onPublishedChange?.(job?.state === 'PUBLISHED' || job?.state === 'SCHEDULED'); }, [job?.state, onPublishedChange]);
  const button = 'inline-flex min-h-10 items-center gap-2 rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm font-semibold text-white';
  const held = automation?.state === 'HELD' || job?.restriction_detected;
  return <section className="space-y-4 rounded-xl border border-teal-400/20 bg-slate-900 p-4">
    <div>
      <h4 className="font-bold text-white">Automatic YouTube publishing</h4>
      <p className="mt-1 text-sm text-slate-400">Private upload → automatic recheck → Studio copyright &amp; thumbnail verification → next available 6:30 PM IST.</p>
    </div>
    {account?.is_authenticated && <p className="text-sm text-slate-300">Connected channel: <strong>{account.channel_title}</strong> · Entertainment · Not made for kids</p>}
    {account && !account.is_authenticated && <div className="space-y-2 rounded-lg bg-amber-500/10 p-3 text-sm text-amber-200">
      <p>{account.error || 'Connect your YouTube channel once. The queue will continue automatically.'}</p>
      <button className={button} disabled={!account.client_secret_present || connecting} onClick={() => void connect()}>Connect YouTube</button>
    </div>}
    <div role="status" className={`space-y-2 rounded-lg p-3 text-sm ${held ? 'bg-rose-500/10 text-rose-200' : 'bg-teal-400/5 text-slate-200'}`}>
      <p className="font-bold">{automation?.state.replaceAll('_', ' ') || (ready ? 'Adding to automatic upload queue…' : 'Waiting for video export')}</p>
      <p>{automation?.message || 'Video ready hone par upload automatically start hoga.'}</p>
      {job?.running && <progress aria-label="YouTube upload progress" value={job.progress} max={100} className="w-full accent-teal-400" />}
      {job?.video_id && <p>Upload complete · {job.youtube_status?.processing_status || 'YouTube processing pending'}</p>}
      {job?.publish_at && <p className="font-semibold">Scheduled: {new Date(job.publish_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST</p>}
      {automation?.evidence && <p>Studio: {automation.evidence.copyright_status} · Thumbnail: {automation.evidence.thumbnail_matches ? 'verified' : 'verification pending'}</p>}
      {automation?.next_check && automation.state !== 'HELD' ? <p className="text-xs text-slate-400">Background recheck: {new Date(automation.next_check * 1000).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST</p> : null}
    </div>
    {job?.video_id && <div className="flex flex-wrap gap-2">
      <a href={job.studio_url} target="_blank" rel="noreferrer" className={button}><ExternalLink className="h-4 w-4" />Open Studio</a>
      <a href={job.youtube_url} target="_blank" rel="noreferrer" className={button}>View video</a>
      <DownloadThumbnailButton url={`${API_BASE_URL}${job.thumbnail_url}`} filename={`uploaded-thumbnail-${movieId}.jpg`} />
    </div>}
    <p className="text-xs text-slate-400">Backend aur Studio monitor chalu rakhein. Pending checks, claims, blocks ya unverified thumbnail par video schedule nahi hogi. Baad mein aane wale claims bhi monitor honge.</p>
    {connecting && <p className="flex items-center gap-2 text-sm text-amber-200"><LoaderCircle className="h-4 w-4 animate-spin" />Channel connection pending…</p>}
    {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
  </section>;
}
