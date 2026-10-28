"use client";

import React, { useState } from "react";
import { Project } from "@/lib/types";
import { Clapperboard, Trash2, Film, CheckCircle2, Clock, Search, Sparkles } from "lucide-react";

interface ProjectListProps {
  projects: Project[];
  activeProjectId: number | null;
  onSelectProject: (id: number) => void;
  onDeleteProject: (id: number) => void;
  isLoading: boolean;
  grid?: boolean;
}

export function ProjectList({
  projects,
  activeProjectId,
  onSelectProject,
  onDeleteProject,
  isLoading,
  grid = false,
}: ProjectListProps) {
  const [filterQuery, setFilterQuery] = useState("");

  const filteredProjects = projects.filter((p) =>
    p.title.toLowerCase().includes(filterQuery.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3 p-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-24 animate-pulse rounded-2xl bg-slate-900/60 border border-white/[0.04]"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search Filter Header */}
      <div className="p-3 border-b border-white/[0.06]">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Filter projects..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            className="w-full rounded-xl bg-slate-900/80 border border-white/[0.08] py-1.5 pl-9 pr-3 text-xs text-white placeholder-slate-500 focus:border-rose-500/80 focus:outline-none"
          />
        </div>
      </div>

      {filteredProjects.length === 0 ? (
        <div className="p-8 text-center text-slate-500">
          <Film className="mx-auto h-9 w-9 opacity-25 mb-2.5 text-rose-400" />
          <p className="text-xs font-semibold text-slate-400">No projects found</p>
          <p className="text-[11px] text-slate-600 mt-1">
            {filterQuery ? "Try another search term." : "Create your first lineup to get started."}
          </p>
        </div>
      ) : (
        <div className={grid ? 'grid grid-cols-1 gap-4 p-3 sm:grid-cols-2 xl:grid-cols-3' : 'flex flex-col gap-2.5 p-3 overflow-y-auto max-h-[calc(100vh-170px)]'}>
          {filteredProjects.map((project) => {
            const isActive = activeProjectId === project.id;
            const movies = project.movies_json || [];

            return (
              <div
                key={project.id}
                onClick={() => onSelectProject(project.id)}
                className={`group relative flex flex-col gap-2 rounded-2xl p-3.5 transition-all duration-200 cursor-pointer border ${
                  isActive
                    ? "bg-slate-900/90 border-rose-500 shadow-xl shadow-rose-950/20 ring-1 ring-rose-500/30"
                    : "glass-card hover:border-white/10 hover:bg-slate-900/70"
                }`}
              >
                {/* Header title & Delete action */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex flex-col min-w-0">
                    <span className="text-[10px] font-black tracking-wider text-rose-400 uppercase">
                      {project.job_code}
                    </span>
                    <h3 className="font-bold text-xs text-slate-200 line-clamp-1 group-hover:text-white transition">
                      <button type="button" onClick={event => { event.stopPropagation(); onSelectProject(project.id); }} className="text-left">{project.title}</button>
                    </h3>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`Delete project "${project.title}"?`)) {
                        onDeleteProject(project.id);
                      }
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-500 hover:bg-red-500/10 hover:text-red-400 transition"
                    title="Delete project"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* Movie Posters Stack */}
                <div className="flex items-center justify-between mt-1">
                  <div className="flex -space-x-2.5 overflow-hidden py-0.5">
                    {movies.slice(0, 4).map((m, idx) => (
                      <div
                        key={idx}
                        className="relative h-9 w-7 rounded-lg bg-slate-800 border-2 border-slate-950 overflow-hidden shadow-md shrink-0"
                      >
                        {m.poster_url ? (
                          <img src={m.poster_url} alt={m.title} className="h-full w-full object-cover" />
                        ) : (
                          <div className="h-full w-full flex items-center justify-center text-[9px] text-slate-400 font-bold bg-slate-900">
                            #{idx + 1}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400">
                    <span className="rounded-md bg-slate-800/80 px-2 py-0.5 text-[10px] text-slate-300 border border-white/[0.04]">
                      {project.movie_count} Movies
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mt-1 flex flex-col gap-1">
                  <div className="flex items-center justify-between text-[10px] text-slate-400 font-medium">
                    <span className="flex items-center gap-1">
                      {project.progress_percent >= 100 ? (
                        <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                      ) : (
                        <Clock className="h-3 w-3 text-amber-400" />
                      )}
                      <span>{project.status}</span>
                    </span>
                    <span className="font-bold text-slate-300">{project.progress_percent}%</span>
                  </div>

                  <div className="h-1.5 w-full bg-slate-950 rounded-full overflow-hidden p-0.5 border border-white/[0.04]">
                    <div
                      className="h-full bg-gradient-to-r from-rose-500 via-pink-500 to-amber-500 rounded-full transition-all duration-300"
                      style={{ width: `${project.progress_percent}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
