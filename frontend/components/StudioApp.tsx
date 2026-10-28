"use client";

import React, { Suspense, useState, useEffect, useRef } from "react";
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Project, MovieItem } from "@/lib/types";
import { fetchProjects, fetchProject, deleteProject } from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { ProjectList } from "@/components/ProjectList";
import { AppSidebar } from '@/components/AppSidebar';
import { MovieDiscovery } from '@/components/MovieDiscovery';
import { ProcessingQueuePanel } from '@/components/ProcessingQueuePanel';
import { enqueueExistingProject } from '@/lib/processingQueueApi';
import { StudioDashboard } from '@/components/StudioDashboard';
import { LongVideoPlanner } from '@/components/LongVideoPlanner';
import { CreateProjectModal } from "@/components/CreateProjectModal";
import { ScriptEditor } from "@/components/ScriptEditor";
import { CinematicReviewPanel } from "@/components/CinematicReviewPanel";
import { VoiceStudio } from "@/components/VoiceStudio";
import { TrailerManager } from "@/components/TrailerManager";
import { SceneSelector } from "@/components/SceneSelector";
import { CollageThumbnailStudio } from "@/components/CollageThumbnailStudio";
import { VideoComposer } from "@/components/VideoComposer";
import { AutoPilotModal } from "@/components/AutoPilotModal";
import { YouTubeUploadStep } from "@/components/YouTubeUploadStep";
import {
  Film,
  FileText,
  Mic,
  Video,
  ImageIcon,
  Clapperboard,
  Scissors,
  Sparkles,
  Layers,
  ChevronRight,
  Clock,
  Star,
  CheckCircle2,
  ArrowRight,
  Zap,
  Upload,
} from "lucide-react";

const WORKFLOW_STEPS = [
  { id: "movies", stepNumber: 1, label: "1. Lineup Movies", icon: Film },
  { id: "trailers", stepNumber: 2, label: "2. Trailers & Clips", icon: Video },
  { id: "scenes", stepNumber: 3, label: "3. Gemini Scenes", icon: Scissors },
  { id: "script", stepNumber: 4, label: "4. Hindi Script", icon: FileText },
  { id: "voice", stepNumber: 5, label: "5. Sarvam Voice", icon: Mic },
  { id: "thumbnail", stepNumber: 6, label: "6. Thumbnail", icon: ImageIcon },
  { id: "video", stepNumber: 7, label: "7. 9:16 Video", icon: Clapperboard },
  { id: "upload", stepNumber: 8, label: "8. YouTube Upload", icon: Upload },
];

const LOCAL_STORAGE_KEY = "movie_studio_saved_projects";
const LOCAL_STORAGE_ACTIVE_KEY = "movie_studio_active_id";

function getStoredProjects(): Project[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter(project => Number.isSafeInteger(project?.id) && project.id > 0) : [];
  } catch {
    return [];
  }
}

function saveStoredProjects(projs: Project[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(projs));
  } catch {}
}

type StudioView = 'dashboard' | 'movies' | 'lineups' | 'studio' | 'uploads' | 'queue' | 'long-videos';

export function StudioApp({ view }: { view: StudioView }) {
  return <Suspense fallback={<div role="status" className="p-6 text-sm text-slate-400">Loading Movie Studio…</div>}><StudioAppContent view={view} /></Suspense>;
}

function StudioAppContent({ view }: { view: StudioView }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedId = Number(searchParams.get('project'));
  const requestedProjectId = Number.isSafeInteger(requestedId) && requestedId > 0 ? requestedId : null;
  const selectedIdRef = useRef<number | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [isLoadingProject, setIsLoadingProject] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [initialMovies, setInitialMovies] = useState<MovieItem[]>([]);
  const sidebarRef = useRef<HTMLElement>(null);
  const [isAutoPilotOpen, setIsAutoPilotOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"movies" | "trailers" | "scenes" | "script" | "voice" | "thumbnail" | "video" | "upload">("movies");
  const [error, setError] = useState<string | null>(null);

  // URL selection wins over the remembered project. Cache is a display aid;
  // it must never silently substitute a different movie.
  useEffect(() => {
    const cached = getStoredProjects();
    let savedId: number | null = null;
    try {
      const value = Number(localStorage.getItem(LOCAL_STORAGE_ACTIVE_KEY));
      if (Number.isSafeInteger(value) && value > 0) savedId = value;
    } catch {}
    const id = requestedProjectId ?? savedId ?? cached[0]?.id ?? null;
    if (selectedIdRef.current === id) return;
    selectedIdRef.current = id;
    setProjects(cached); setActiveProjectId(id);
    setIsLoadingProject(id !== null);
    setActiveProject(cached.find(project => project.id === id) || null);
  }, [requestedProjectId]);

  useEffect(() => {
    if (view !== 'studio' || !activeProject) return;
    const pending = sessionStorage.getItem('movie_studio_pending_autopilot');
    if (pending === String(activeProject.id)) {
      sessionStorage.removeItem('movie_studio_pending_autopilot');
      setIsAutoPilotOpen(true);
    }
  }, [activeProject, view]);

  useEffect(() => {
    if (!sidebarOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    sidebarRef.current?.querySelector<HTMLButtonElement>('button')?.focus();
    const closeOnResize = () => { if (window.innerWidth >= 1024) setSidebarOpen(false); };
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setSidebarOpen(false);
      if (event.key === 'Tab') {
        const controls = Array.from(sidebarRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input, select, a[href]') || [])
          .filter(element => element.getClientRects().length > 0);
        const first = controls[0], last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    window.addEventListener('resize', closeOnResize); document.addEventListener('keydown', keyboard);
    return () => { document.body.style.overflow = overflow; window.removeEventListener('resize', closeOnResize); document.removeEventListener('keydown', keyboard); previous?.focus(); };
  }, [sidebarOpen]);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoadingList(true);
    fetchProjects(controller.signal).then(serverList => {
      if (controller.signal.aborted) return;
      setProjects(serverList); saveStoredProjects(serverList);
      // Use a default only when there is no explicit/remembered selection.
      if (selectedIdRef.current === null && serverList.length) {
        const first = serverList[0];
        selectedIdRef.current = first.id;
        setActiveProjectId(first.id); setActiveProject(first);
      }
    }).catch(err => {
      if (!controller.signal.aborted) console.warn('Project list unavailable; retaining cached projects.', err);
    }).finally(() => { if (!controller.signal.aborted) setIsLoadingList(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (activeProjectId === null) return;
    const id = activeProjectId;
    const controller = new AbortController();
    setIsLoadingProject(true); setError(null);
    fetchProject(id, controller.signal).then(project => {
      if (controller.signal.aborted || selectedIdRef.current !== id) return;
      setActiveProject(project);
      localStorage.setItem(LOCAL_STORAGE_ACTIVE_KEY, String(id));
      setProjects(previous => {
        const updated = previous.some(item => item.id === id)
          ? previous.map(item => item.id === id ? project : item) : [project, ...previous];
        saveStoredProjects(updated);
        return updated;
      });
    }).catch(err => {
      if (controller.signal.aborted || selectedIdRef.current !== id) return;
      setError(err instanceof Error ? err.message : 'Could not open the selected project.');
      // Keep the exact selected project's cached view; never open Luck or create
      // a replacement project in response to a failed read request.
    }).finally(() => {
      if (!controller.signal.aborted && selectedIdRef.current === id) setIsLoadingProject(false);
    });
    return () => controller.abort();
  }, [activeProjectId]);

  const handleDeleteProject = async (id: number) => {
    try {
      await deleteProject(id);
    } catch (err: any) {
      console.warn("Server delete:", err);
    }
    const remaining = projects.filter((p) => p.id !== id);
    setProjects(remaining);
    saveStoredProjects(remaining);
    if (activeProjectId === id) {
      if (remaining.length > 0) {
        selectProject(remaining[0].id);
      } else {
        selectedIdRef.current = null;
        localStorage.removeItem(LOCAL_STORAGE_ACTIVE_KEY);
        setActiveProjectId(null);
        setActiveProject(null);
      }
    }
  };

  const handleProjectUpdated = (updated: Project) => {
    if (selectedIdRef.current === updated.id) setActiveProject(updated);
    setProjects((prev) => {
      const newList = prev.map((p) => (p.id === updated.id ? updated : p));
      saveStoredProjects(newList);
      return newList;
    });
  };

  const movies = activeProject?.movies_json || [];
  const primaryPoster = movies.find((m) => m.poster_url)?.poster_url || null;
  function selectProject(id: number) {
    selectedIdRef.current = id;
    localStorage.setItem(LOCAL_STORAGE_ACTIVE_KEY, String(id));
    setActiveProjectId(id);
    setActiveProject(projects.find(project => project.id === id) || null);
    setIsLoadingProject(true);
    setError(null); setIsAutoPilotOpen(false); setSidebarOpen(false);
  }
  function openProject(id: number) {
    selectProject(id);
    router.push(`/studio?project=${id}`);
  }
  const pageInfo = {
    dashboard: ['Dashboard', 'Your movies, projects and publishing workflow in one place.'],
    'long-videos': ['Long Videos', 'Plan a seven-movie cinematic review for your channel.'],
    movies: ['Movie Search', 'Select a movie to add it to the automatic processing queue. One movie per Short.'],
    queue: ['Processing Queue', 'Movies process automatically, one at a time.'],
    lineups: ['My Lineups', 'Open a saved project to continue creating your Short.'],
    studio: ['Shorts Studio', 'Trailers, scenes, script, voice, thumbnail and video — step by step.'],
    uploads: ['YouTube Uploads', 'Upload privately, review the thumbnail and copyright checks, then schedule.'],
  }[view];

  return (
    <div className="studio-shell min-h-screen bg-slate-950 flex flex-col text-slate-100">
      <Navbar onNewProject={() => router.push('/movies')} projectCount={projects.length} onOpenSidebar={() => setSidebarOpen(true)} />

      <main className="flex-1 mx-auto grid w-full max-w-[1920px] grid-cols-1 items-start gap-3 p-3 sm:p-4 lg:grid-cols-[208px_minmax(0,1fr)] xl:grid-cols-[220px_minmax(0,1fr)]">
        {/* Left Column: Projects Lineup List */}
        {sidebarOpen && <button aria-label="Close sidebar backdrop" onClick={() => setSidebarOpen(false)} className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden" />}
        <aside ref={sidebarRef} aria-label="Workspace navigation" role={sidebarOpen ? 'dialog' : undefined} aria-modal={sidebarOpen ? true : undefined}
          className={`${sidebarOpen ? 'flex' : 'hidden'} fixed inset-y-3 left-3 z-50 w-[min(300px,calc(100vw-24px))] flex-col overflow-hidden rounded-xl border border-white/10 bg-slate-900 shadow-2xl lg:sticky lg:top-[72px] lg:z-20 lg:flex lg:h-[calc(100dvh-88px)] lg:w-auto`}>
          <AppSidebar projectCount={projects.length} onClose={() => setSidebarOpen(false)} />
        </aside>

        {/* Right Column: Active Studio Workspace */}
        <section className="flex min-w-0 flex-col gap-3">
          <div className="flex flex-wrap items-end justify-between gap-3 py-0.5">
            <div>{view !== 'dashboard' && <p className="mb-1 text-[10px] text-slate-500">Workspace / {pageInfo[0]}</p>}<h1 className="text-xl font-bold tracking-tight text-white">{pageInfo[0]}</h1><p className="mt-1 max-w-2xl text-xs text-slate-400">{pageInfo[1]}</p></div>
            {(view === 'studio' || view === 'uploads') && projects.length > 0 && <label className="w-full text-xs font-semibold text-slate-400 sm:w-64">Active lineup
              <select aria-label="Active lineup" value={activeProjectId || ''} onChange={event => { const id = Number(event.target.value); selectProject(id); router.push(`/${view}?project=${id}`); }} className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900 p-3 text-sm text-white">
                {activeProjectId && !projects.some(project => project.id === activeProjectId) && <option value={activeProjectId}>Selected project #{activeProjectId}</option>}
                {projects.map(project => <option key={project.id} value={project.id}>{project.title}</option>)}
              </select>
            </label>}
          </div>
          {error && <p role="alert" className="rounded-xl border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-200">Selected project could not refresh: {error}</p>}
          {isLoadingProject && (view === 'studio' || view === 'uploads') && <p role="status" className="text-xs text-slate-400">Loading selected lineup…</p>}
          {view === 'dashboard' && <StudioDashboard projects={projects} onOpenProject={openProject} />}
          {view === 'long-videos' && <LongVideoPlanner projects={projects} />}
          {view === 'movies' && <MovieDiscovery />}
          {view === 'queue' && <ProcessingQueuePanel />}
          {view === 'lineups' && <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900/60"><ProjectList projects={projects} activeProjectId={activeProjectId} onSelectProject={openProject} onDeleteProject={handleDeleteProject} isLoading={isLoadingList} grid /></div>}
          {view === 'uploads' && (!isLoadingProject && activeProject && activeProject.id === (requestedProjectId ?? activeProjectId) ? <YouTubeUploadStep key={activeProject.id} project={activeProject} /> : <div className="rounded-2xl border border-white/10 p-8 text-slate-400">{isLoadingProject ? 'Loading selected lineup…' : 'Choose or create a lineup first.'} <Link href="/lineups" className="text-rose-300 underline">Open My Lineups</Link></div>)}
          {view === 'studio' && (!isLoadingProject && activeProject && activeProject.id === (requestedProjectId ?? activeProjectId) ? (
            <React.Fragment key={activeProject.id}>
              {/* Studio Hero Card with Ambient Poster Glow */}
              <div className="relative min-w-0 rounded-xl glass-panel p-3 overflow-hidden border border-white/[0.08] sm:p-4">
                {primaryPoster && (
                  <div
                    className="absolute -right-20 -top-20 w-96 h-96 opacity-15 blur-3xl pointer-events-none rounded-full"
                    style={{ backgroundImage: `url(${primaryPoster})`, backgroundSize: "cover" }}
                  />
                )}

                <div className="relative z-10 flex flex-wrap items-center justify-between gap-4">
                  <div className="flex flex-col gap-1.5">
                    <div className="flex min-w-0 flex-wrap items-center gap-2.5">
                      <span className="rounded-full bg-rose-500/15 px-3 py-0.5 text-xs font-black text-rose-400 border border-rose-500/30">
                        {activeProject.job_code}
                      </span>
                      <h2 className="break-words text-base sm:text-lg font-bold text-white tracking-tight">
                        {activeProject.title}
                      </h2>
                    </div>
                    {activeProject.notes && (
                      <p className="text-xs text-slate-400 font-medium">{activeProject.notes}</p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <button
                      disabled={activeProject.movie_count !== 1}
                      onClick={async () => {
                        try { await enqueueExistingProject(activeProject.id); router.push('/queue'); }
                        catch (err) { setError(err instanceof Error ? err.message : 'Could not queue movie'); }
                      }}
                      className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-amber-500 via-rose-500 to-pink-500 px-4 py-2 font-black text-white shadow-lg shadow-rose-950/50 hover:scale-105 active:scale-95 transition glow-rose"
                      title="Add this single movie to the sequential processing queue"
                    >
                      <Zap className="h-4 w-4 fill-current text-amber-200 animate-pulse" />
                      <span>⚡ Queue Auto-Pilot</span>
                    </button>
                    <span className="rounded-2xl bg-slate-900/90 px-3.5 py-2 font-bold text-slate-300 border border-white/[0.06]">
                      {activeProject.movie_count} {activeProject.movie_count === 1 ? "Movie" : "Movies"} Selected
                    </span>
                    <span className="rounded-2xl bg-rose-500/15 px-3.5 py-2 font-black text-rose-400 border border-rose-500/30">
                      {activeProject.progress_percent}% Complete
                    </span>
                  </div>
                </div>

                {/* Workflow Stepper Navigation */}
                <div aria-label="Workflow steps" className="relative z-10 mt-3 flex overflow-x-auto border-t border-white/[0.08] pb-2 pt-3">
                  {WORKFLOW_STEPS.map((step, index) => {
                    const Icon = step.icon;
                    const isActive = activeTab === step.id;
                    return (
                      <React.Fragment key={step.id}><button
                        onClick={() => setActiveTab(step.id as any)}
                        aria-current={isActive ? 'step' : undefined}
                        className={`flex min-w-[88px] flex-1 flex-col items-center justify-center gap-1.5 rounded-xl px-2 py-2.5 text-[10px] font-semibold transition-all border ${
                          isActive
                            ? "bg-rose-500/20 border-rose-500 text-rose-300 shadow-lg shadow-rose-950/30 ring-1 ring-rose-500/50"
                            : "bg-slate-950/60 border-white/[0.06] text-slate-400 hover:text-white hover:border-white/15"
                        }`}
                      >
                        <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${isActive ? 'bg-rose-400/15' : 'bg-slate-800/60'}`}><Icon className="h-4 w-4 shrink-0" /></span>
                        <span className="whitespace-nowrap">{step.label.replace(/^\d+\. /, '')}</span>
                      </button>{index < WORKFLOW_STEPS.length - 1 && <ChevronRight aria-hidden="true" className={`mx-1 h-3.5 w-3.5 shrink-0 self-center ${isActive ? 'text-rose-300' : 'text-slate-700'}`} />}</React.Fragment>
                    );
                  })}
                </div>
              </div>

              {/* Tab Workspace Panels */}
              {!activeProject.job_code.startsWith('CINE-') && <CinematicReviewPanel project={activeProject} onOpen={openProject} />}
              {activeTab === "movies" && (
                <div className="grid grid-cols-1 min-[440px]:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-5">
                  {movies.map((movie, idx) => (
                    <div
                      key={idx}
                      className="group flex flex-col rounded-3xl glass-panel overflow-hidden p-4 gap-3.5 shadow-xl hover:border-white/20 transition-all duration-300"
                    >
                      <div className="relative aspect-[2/3] w-full rounded-2xl bg-slate-950 overflow-hidden shadow-lg">
                        {movie.poster_url ? (
                          <img
                            src={movie.poster_url}
                            alt={movie.title}
                            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
                          />
                        ) : (
                          <div className="h-full w-full flex items-center justify-center text-slate-600 text-xs">
                            No Poster Found
                          </div>
                        )}
                        <span className="absolute top-2.5 left-2.5 rounded-xl bg-black/85 px-2.5 py-1 text-xs font-black text-rose-400 border border-white/[0.1] shadow">
                          Slot #{idx + 1}
                        </span>
                        {movie.vote_average && (
                          <span className="absolute top-2.5 right-2.5 rounded-xl bg-black/85 px-2.5 py-1 text-xs font-extrabold text-amber-300 border border-white/[0.1] flex items-center gap-1 shadow">
                            <Star className="h-3 w-3 fill-amber-300" />
                            {movie.vote_average}
                          </span>
                        )}
                      </div>

                      <div className="flex flex-col flex-1 justify-between">
                        <div>
                          <h3 className="font-extrabold text-sm text-white line-clamp-1 group-hover:text-rose-400 transition">
                            {movie.title}
                          </h3>
                          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
                            {movie.year || "N/A"} • {movie.genres?.slice(0, 2).join(", ") || "Feature Film"}
                          </p>
                          {movie.overview && (
                            <p className="text-xs text-slate-300 mt-2 line-clamp-3 leading-relaxed">
                              {movie.overview}
                            </p>
                          )}
                        </div>

                        <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400 font-semibold">
                          <span>{movie.trailers_count || 0} Trailers Available</span>
                          <span className="text-rose-400 flex items-center gap-1">
                            Ready
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "trailers" && (
                <TrailerManager project={activeProject} onProjectUpdated={handleProjectUpdated} />
              )}

              {activeTab === "scenes" && (
                <SceneSelector project={activeProject} onProjectUpdated={handleProjectUpdated} />
              )}

              {activeTab === "script" && (
                <ScriptEditor project={activeProject} onProjectUpdated={handleProjectUpdated} />
              )}

              {activeTab === "voice" && (
                <VoiceStudio project={activeProject} onProjectUpdated={handleProjectUpdated} />
              )}

              {activeTab === "thumbnail" && (
                <CollageThumbnailStudio project={activeProject} onProjectUpdated={handleProjectUpdated} />
              )}

              {activeTab === "video" && (
                <VideoComposer project={activeProject} onProjectUpdated={handleProjectUpdated} />
              )}
              {activeTab === "upload" && <YouTubeUploadStep key={activeProject.id} project={activeProject} />}
            </React.Fragment>
          ) : (
            <div className="flex flex-col items-center justify-center rounded-3xl glass-panel p-6 sm:p-16 text-center text-slate-500 min-h-[460px] shadow-2xl">
              <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-tr from-rose-600 to-amber-500 shadow-xl shadow-rose-950/50 mb-4 glow-rose">
                <Sparkles className="h-8 w-8 text-white" />
              </div>
              <h2 className="text-xl font-black text-white">{activeProjectId ? 'Opening selected lineup' : 'Choose a movie lineup'}</h2>
              <p className="text-xs text-slate-400 max-w-md mt-1.5 leading-relaxed">
                {isLoadingProject ? 'Loading the project you selected…' : error ? 'The selected project could not load. Choose it again from My Lineups or retry the page.' : 'Open a saved lineup or create a new Short from Movie Search.'}
              </p>
              <Link href="/lineups" className="mt-4 text-sm font-bold text-rose-300 underline">Open My Lineups</Link>
              <button
                onClick={() => router.push('/movies')}
                className="mt-6 flex items-center gap-2 rounded-2xl bg-gradient-to-r from-rose-600 via-pink-600 to-amber-500 px-6 py-3 text-xs font-bold text-white shadow-xl shadow-rose-950/60 hover:scale-105 active:scale-95 transition glow-rose"
              >
                <span>Add a Movie to Queue</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          ))}
        </section>
      </main>

      <CreateProjectModal
        isOpen={isModalOpen}
        initialMovies={initialMovies}
        onClose={() => setIsModalOpen(false)}
        onProjectCreated={(id, autoPilot, created) => {
          if (created) {
            const updated = [created, ...getStoredProjects().filter(project => project.id !== id)];
            saveStoredProjects(updated); setProjects(updated); setActiveProject(created);
          }
          selectedIdRef.current = id;
          localStorage.setItem(LOCAL_STORAGE_ACTIVE_KEY, String(id));
          setActiveProjectId(id);
          if (autoPilot) {
            sessionStorage.setItem('movie_studio_pending_autopilot', String(id));
          }
          router.push(`/studio?project=${id}`);
        }}
      />

      <AutoPilotModal
        isOpen={isAutoPilotOpen}
        project={activeProject}
        onClose={() => setIsAutoPilotOpen(false)}
        onCompleted={(updated) => {
          handleProjectUpdated(updated);
        }}
        onNavigateTab={(tab) => {
          setActiveTab(tab);
          if (view !== 'studio' && activeProjectId) router.push(`/studio?project=${activeProjectId}`);
        }}
      />
    </div>
  );
}
