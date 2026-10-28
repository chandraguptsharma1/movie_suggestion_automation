#!/usr/bin/env python3
"""
Movie Suggestion & Group Shorts Studio - Auto-Pilot CLI Runner
Generate complete viral YouTube Shorts from movie titles hands-free.

Usage Examples:
    python auto_short.py "Colony"
    python auto_short.py "Inception, Shutter Island, Interstellar"
    python auto_short.py --category psychological-thrillers --count 3
"""

import argparse
import os
import sys
from pathlib import Path

# Add backend directory to sys.path so app modules import cleanly
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from app.database import project_repo
from app.models.schemas import CreateProjectRequest, MovieItem
from app.services.tmdb_service import tmdb_service
from app.services.suggestion_service import suggestion_service
from app.services.auto_pilot_service import auto_pilot_service
from app.routes.project_routes import create_project


def print_banner():
    print("""
========================================================================
  🎬 MOVIE SHORTS STUDIO - 1-CLICK AUTOPILOT ENGINE 🚀
========================================================================
    """)


def main():
    parser = argparse.ArgumentParser(
        description="Auto-Pilot: Generate 9:16 Shorts hands-free from movie titles."
    )
    parser.add_argument(
        "movies",
        nargs="*",
        help="Movie titles to spotlight (e.g. 'Colony' or 'Inception, Interstellar')",
    )
    parser.add_argument(
        "--category",
        "-c",
        type=str,
        default="",
        help="Auto-curate from theme (e.g. 'mind-bending-scifi', 'psychological-thrillers')",
    )
    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=3,
        help="Number of movies to curate if using category (1-4)",
    )
    parser.add_argument(
        "--speaker",
        "-s",
        type=str,
        default="vipul_hi_social",
        help="Sarvam AI Hindi speaker (vipul_hi_social, aditya_hi_conversational, sunny_hi_reels, shubh_hi_stories_dramatic)",
    )
    parser.add_argument(
        "--pace",
        "-p",
        type=float,
        default=1.05,
        help="Voice speech pace (0.95 to 1.25)",
    )
    parser.add_argument(
        "--bgm",
        "--bgm-style",
        dest="bgm_style",
        type=str,
        default="suspense",
        help="Background music style (suspense, mystery, epic, ambient, or specific track / 'none')",
    )
    parser.add_argument(
        "--pipeline",
        "--style",
        dest="pipeline_mode",
        type=str,
        default="cinematic",
        choices=["cinematic", "standard"],
        help="Pipeline style: 'cinematic' (animated Hindi subtitles, sound accents, beat cuts) or 'standard'",
    )
    parser.add_argument(
        "--upload",
        dest="auto_upload",
        action="store_true",
        default=True,
        help="Automatically upload completed Short to YouTube channel as private review (default: True)",
    )
    parser.add_argument(
        "--no-upload",
        dest="auto_upload",
        action="store_false",
        help="Skip automatic YouTube upload",
    )

    args = parser.parse_args()
    print_banner()

    movie_titles = []
    if args.movies:
        raw_joined = " ".join(args.movies)
        movie_titles = [t.strip() for t in raw_joined.split(",") if t.strip()]

    selected_movies = []

    if movie_titles:
        print(f"[*] Searching TMDB for: {', '.join(movie_titles)}...")
        for title in movie_titles[:4]:
            results = tmdb_service.search_multi(title, media_type="movie")
            if results:
                m = results[0]
                print(f"    [+] Found: {m.get('title')} ({m.get('year')}) - Rating: {m.get('vote_average')}/10")
                selected_movies.append(m)
            else:
                print(f"    [!] Not found in TMDB: '{title}', creating placeholder...")
                selected_movies.append({
                    "title": title,
                    "year": "2024",
                    "overview": f"A gripping story centered on {title}.",
                    "poster_url": None,
                    "backdrop_url": None,
                    "vote_average": 8.0,
                    "trailers": [],
                })
    elif args.category:
        print(f"[*] Curating {args.count} movies from category '{args.category}'...")
        selected_movies = suggestion_service.suggest_by_category(args.category, count=args.count)
        for m in selected_movies:
            print(f"    [+] Curated: {m.get('title')} ({m.get('year')})")
    else:
        print("[!] No movie titles or category specified. Using default: 'Colony'")
        results = tmdb_service.search_multi("Colony", media_type="movie")
        selected_movies = [results[0]] if results else [{
            "title": "Colony",
            "year": "2021",
            "overview": "In a post-apocalyptic future, a shipwrecked astronaut must decide the fate of Earth's remaining populace.",
            "poster_url": None,
            "backdrop_url": None,
            "vote_average": 6.8,
            "trailers": [],
        }]

    print(f"\n[*] Creating project for {len(selected_movies)} movie(s)...")
    movie_items = [MovieItem(**m) for m in selected_movies]
    created = create_project(CreateProjectRequest(movies=movie_items))
    proj_id = created["id"]
    print(f"    [+] Project #{proj_id} created: {created.get('title')} ({created.get('job_code')})")

    print("\n" + "=" * 60)
    print("  🚀 LAUNCHING AUTOPILOT PIPELINE...")
    print("=" * 60)

    def on_progress(pct, msg):
        bar_len = 25
        filled = int(round(bar_len * pct / 100))
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r[{bar}] {pct:3d}% - {msg}", end="", flush=True)

    try:
        res = auto_pilot_service.run_auto_pilot(
            project_id=proj_id,
            speaker=args.speaker,
            pace=args.pace,
            bgm_style=args.bgm_style,
            pipeline_mode=args.pipeline_mode,
            auto_upload=args.auto_upload,
            progress_callback=on_progress,
        )
        print("\n\n" + "=" * 60)
        print("  🎉 AUTOPILOT FINISHED SUCCESSFULLY!")
        print("=" * 60)
        print(f"  🎬 Video File:     {res['video_path']}")
        print(f"  🖼️  Thumbnail:      {res['thumbnail_path']}")
        print(f"  🎙️  Voiceover:      {res['voice_path']}")

        yt = res.get("youtube_upload") or {}
        if yt.get("uploaded"):
            print("=" * 60)
            print("  📺 YOUTUBE UPLOAD SUCCESSFUL! 🚀")
            print(f"  ▶️  Shorts URL:    {yt.get('youtube_url')}")
            print(f"  🛠️  Studio Edit:   {yt.get('studio_url')}")
            print(f"  📢 Channel:       {yt.get('channel_title')}")
            print(f"  🔒 Privacy:       Private (Review in Studio & Publish)")
        elif yt.get("error"):
            print(f"  ⚠️  YouTube Upload Note: {yt.get('error')}")

        print("=" * 60)
        print("\nReady to review and share!")

    except Exception as exc:
        print(f"\n\n[ERROR] Pipeline failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
