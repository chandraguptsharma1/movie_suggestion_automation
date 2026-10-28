"use client";

import { useState } from 'react';
import { Download } from 'lucide-react';

export function DownloadThumbnailButton({ url, filename, className }: { url: string; filename: string; className?: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function download() {
    setBusy(true); setError('');
    try {
      const response = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(30000) });
      if (!response.ok) throw new Error('Thumbnail download failed. Please retry.');
      const blob = await response.blob();
      if (!blob.type.startsWith('image/')) throw new Error('Thumbnail image unavailable. Generate it first.');
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl; link.download = filename;
      document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (err) { setError(err instanceof Error ? err.message : 'Download failed'); }
    finally { setBusy(false); }
  }
  return <div>
    <button type="button" disabled={busy} onClick={() => void download()} className={className || 'inline-flex items-center gap-2 rounded-lg border border-white/20 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50'}>
      <Download className="h-4 w-4" />{busy ? 'Downloading…' : 'Download thumbnail'}
    </button>
    {error && <p role="alert" className="mt-2 text-sm text-rose-300">{error}</p>}
  </div>;
}
