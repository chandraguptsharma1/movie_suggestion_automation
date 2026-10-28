"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { enqueueMovie, fetchQueue } from '@/lib/processingQueueApi';
import { Search, Film, Plus, Check, Loader2, SlidersHorizontal } from 'lucide-react';
import { discoverMovies, fetchMovieGenres, type MovieFilters } from '@/lib/api';
import type { MovieItem } from '@/lib/types';

const DEFAULT_FILTERS: MovieFilters = { query: '', year: '', genre_id: '', sort_by: 'popularity.desc' };
const movieKey = (movie: MovieItem) => `${movie.media_type || 'movie'}:${movie.tmdb_id || `${movie.title.trim().toLowerCase()}:${movie.year || ''}`}`;

export function MovieDiscovery() {
  const [filters, setFilters] = useState<MovieFilters>(DEFAULT_FILTERS);
  const [genres, setGenres] = useState<Array<{ id: number; name: string }>>([]);
  const [movies, setMovies] = useState<MovieItem[]>([]);
  const [queued, setQueued] = useState<Record<string, string>>({});
  const [adding, setAdding] = useState<string[]>([]);
  const pendingMovies = useRef(new Set<string>());
  const [nextPage, setNextPage] = useState<number | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectionError, setSelectionError] = useState('');
  const applied = useRef(DEFAULT_FILTERS);
  const request = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const load = useCallback(async (values: MovieFilters, page = 1, append = false) => {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    const version = ++generation.current;
    setLoading(true); setError('');
    if (!append) { setMovies([]); setNextPage(null); setTotal(null); }
    applied.current = values;
    try {
      const result = await discoverMovies(values, page, controller.signal);
      if (controller.signal.aborted || version !== generation.current) return;
      setMovies(previous => Array.from(new Map([...(append ? previous : []), ...result.results].map(movie => [movieKey(movie), movie])).values()));
      setNextPage(result.next_page); setTotal(result.total_results);
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'Movie search failed');
    } finally { if (version === generation.current) setLoading(false); }
  }, []);
  useEffect(() => {
    void load(DEFAULT_FILTERS);
    fetchQueue().then(items => setQueued(Object.fromEntries(items.map(item => [item.movie_key, item.state])))).catch(() => {});
    let active = true;
    fetchMovieGenres().then(values => { if (active) setGenres(values); })
      .catch(() => { if (active) setError('Categories could not load. Reopen the page to retry.'); });
    return () => { active = false; request.current?.abort(); };
  }, [load]);
  async function addMovie(movie: MovieItem) {
    const key = movieKey(movie);
    if (queued[key] || pendingMovies.current.has(key)) return;
    pendingMovies.current.add(key); setAdding(previous => [...previous, key]); setSelectionError('');
    try {
      const item = await enqueueMovie(movie);
      setQueued(previous => ({...previous, [key]: item.state}));
    } catch (err) { setSelectionError(err instanceof Error ? err.message : 'Could not queue movie'); }
    finally { pendingMovies.current.delete(key); setAdding(previous => previous.filter(value => value !== key)); }
  }
  const input = 'mt-1 w-full min-w-0 rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-400/20';
  return <div className="flex min-w-0 flex-col gap-4">
      <div className="min-w-0 rounded-2xl border border-white/10 bg-slate-900/60">
        <form onSubmit={event => { event.preventDefault(); void load({...filters}); }} className="grid grid-cols-1 items-end gap-3 border-b border-white/10 p-4 sm:grid-cols-2">
          <label className="block text-xs font-semibold text-slate-400">Movie name
            <input aria-label="Movie name" type="search" maxLength={100} placeholder="Search any movie…" value={filters.query} onChange={e => setFilters({...filters, query: e.target.value})} className={input} />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs font-semibold text-slate-400">Release year
              <select aria-label="Release year" value={filters.year} onChange={e => setFilters({...filters, year: e.target.value})} className={input}>
                <option value="">All years</option>{Array.from({length: new Date().getFullYear() - 1900 + 2}, (_, i) => new Date().getFullYear() + 1 - i).map(year => <option key={year} value={year}>{year}</option>)}
              </select>
            </label>
            <label className="text-xs font-semibold text-slate-400">Category / genre
              <select aria-label="Movie category" value={filters.genre_id} onChange={e => setFilters({...filters, genre_id: e.target.value})} className={input}>
                <option value="">All categories</option>{genres.map(genre => <option key={genre.id} value={genre.id}>{genre.name}</option>)}
              </select>
            </label>
          </div>
          <label className="block text-xs font-semibold text-slate-400">Browse order
            <select aria-label="Browse order" disabled={Boolean(filters.query.trim())} value={filters.sort_by} onChange={e => setFilters({...filters, sort_by: e.target.value as MovieFilters['sort_by']})} className={`${input} disabled:opacity-40`}>
              <option value="popularity.desc">Most popular</option><option value="vote_average.desc">Top rated · 100+ votes</option><option value="primary_release_date.desc">Newest releases</option>
            </select>
          </label>
          {filters.query.trim() && <p className="text-[11px] text-slate-500">Name searches use relevance order.</p>}
          <div className="flex gap-2">
            <button type="submit" className="flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-rose-600 text-sm font-bold text-white hover:bg-rose-500"><Search className="h-4 w-4" />Find movies</button>
            <button type="button" onClick={() => { setFilters(DEFAULT_FILTERS); void load(DEFAULT_FILTERS); }} className="rounded-xl border border-white/10 px-3 text-xs text-slate-300">Reset</button>
          </div>
        </form>
        <div className="grid grid-cols-1 gap-3 p-3 min-[480px]:grid-cols-2 xl:grid-cols-3">
          <p aria-live="polite" className="col-span-full px-1 text-xs text-slate-400">{loading ? 'Finding movies…' : `${movies.length} movies shown${total !== null ? ` · ${total.toLocaleString()} found` : ''}`}</p>
          {error && <div role="alert" className="col-span-full rounded-xl border border-rose-400/20 bg-rose-400/10 p-3 text-xs text-rose-200">{error}<button type="button" onClick={() => void load(applied.current)} className="ml-2 underline">Retry</button></div>}
          {!loading && !error && movies.length === 0 && <div className="col-span-full rounded-xl border border-dashed border-white/10 p-6 text-center text-sm text-slate-400"><SlidersHorizontal className="mx-auto mb-2 h-5 w-5" />No matches here. Try another year/category{nextPage ? ' or load more results.' : '.'}</div>}
          {movies.map(movie => {
            const checked = Boolean(queued[movieKey(movie)]);
            const pending = adding.includes(movieKey(movie));
            return <button key={movieKey(movie)} type="button" disabled={checked || pending} onClick={() => void addMovie(movie)} aria-label={`${checked ? 'Already queued' : 'Add to queue:'} ${movie.title} (${movie.year || 'year unknown'})`}
              className={`flex min-h-28 w-full items-start gap-3 rounded-xl border p-2 text-left transition ${checked ? 'border-rose-400/60 bg-rose-400/10' : 'border-white/5 bg-slate-950/40 hover:border-white/20'}`}>
              <div className="h-24 w-16 shrink-0 overflow-hidden rounded-lg bg-slate-800">{movie.poster_url ? <img src={movie.poster_url} alt="" loading="lazy" className="h-full w-full object-cover" /> : <Film className="m-auto mt-8 h-6 w-6 text-slate-500" />}</div>
              <div className="min-w-0 flex-1 py-1"><h3 className="line-clamp-2 text-sm font-bold text-slate-100">{movie.title}</h3><p className="mt-1 text-xs text-slate-400">{movie.year || 'TBA'} · <span className="text-amber-300">★ {movie.vote_average?.toFixed(1) || '—'}</span></p><p className="mt-1 line-clamp-2 text-[11px] text-slate-500">{movie.genres?.join(' · ') || 'Movie'}</p></div>
              <span className={`mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${checked ? 'bg-rose-500 text-white' : 'bg-white/5 text-slate-400'}`}>{pending ? <Loader2 className="h-3 w-3 animate-spin" /> : checked ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}</span>
            </button>;
          })}
          {loading && <Loader2 aria-label="Loading movies" className="col-span-full mx-auto h-5 w-5 animate-spin text-rose-300" />}
          {nextPage && <button type="button" disabled={loading} onClick={() => void load(applied.current, nextPage, true)} className="col-span-full min-h-11 w-full rounded-xl border border-white/10 text-xs font-bold text-slate-300 disabled:opacity-50">Load more movies</button>}
        </div>
      </div>
      <div className="sticky bottom-3 z-20 space-y-2 rounded-2xl border border-white/15 bg-slate-950/95 p-4 shadow-2xl backdrop-blur-xl">
        <p className="text-sm font-bold text-white">Single-movie auto queue</p>
        <p className="text-xs text-slate-400">Click a movie to queue it immediately. Each movie gets its own Cinematic Short; processing runs one by one.</p>
        {selectionError && <p role="alert" className="text-sm text-rose-300">{selectionError}</p>}
        <Link href="/queue" className="inline-flex rounded-xl bg-rose-600 px-4 py-2 text-sm font-bold text-white">View processing queue</Link>
      </div>
  </div>;
}
