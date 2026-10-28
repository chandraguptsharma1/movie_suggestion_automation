# Movie Suggestion Automation & Group Shorts Studio

A specialized, fullstack AI platform for **Multi-Movie Suggestions & YouTube Shorts Automation**, completely decoupled from single-movie review pipelines.

## Features

- **AI Movie Suggestions & Curation**:
  - Auto-suggest 2 to 4 (or up to 7) movies for viral themes (e.g., Mind-Bending Psychological Thrillers, Edge-of-the-Seat Survival, Sci-Fi Time Loops, Underrated OTT Gems) using Google Gemini AI.
  - Automatic TMDB validation, high-res posters, backdrops, ratings, and video trailers.
- **Viral Shorts Scriptwriting**:
  - High-retention 50-60s YouTube Shorts scripts written in conversational Devanagari Hindi (देवनागरी हिंदी लिपि).
  - Custom structure: 3-5s viral curiosity hook, movie spotlights with story premise + why to watch (strictly spoiler-free, no OTT mentions, no audience quotes), and CTA outro.
- **Sarvam AI Neural Hindi Voiceovers**:
  - Native Devanagari neural TTS (Bulbul model) with speaker options (`vipul_hi_social`, `aditya_hi_conversational`, `sunny_hi_reels`, etc.).
  - Pacing control (0.9x to 1.3x), automated sentence chunking, live audio player, and MP3 download.
- **Shiro Bro-Style 9:16 Vertical Collage Thumbnails**:
  - Vertical 1080x1920 collage thumbnail generator with tilted movie cards, white borders, soft drop shadows, top star rating pill, and high-voltage English hook badges (Black box + Neon Yellow box).
- **yt-dlp Trailer Acquisition**:
  - 1-click download of individual or all trailer clips for each movie in the project.
- **FFmpeg 9:16 Shorts Video Assembly**:
  - Merges downloaded trailer video clips with blurred ambient background and overlays the generated Hindi voiceover MP3.
- **Modern Fullstack Architecture**:
  - **Backend**: FastAPI with SQLite out-of-the-box (zero configuration needed), optional PostgreSQL/Supabase compatibility.
  - **Frontend**: Next.js 15 with React 19, Tailwind CSS, and Lucide Icons.

---

## Quick Start

### 1. Backend Setup & Run

```bash
cd backend
# With virtual environment activated:
python -m pip install -r requirements.txt
python run.py
```
Or double-click `start_backend.bat`.
Backend Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Setup & Run

```bash
cd frontend
npm install
npm run dev
```
Or double-click `start_frontend.bat`.
Frontend UI: [http://localhost:3000](http://localhost:3000)

### 3. Launch Both Together

Double-click `start_all.bat` to launch both Backend and Frontend in separate windows simultaneously.

---

## Directory Structure

```
d:/movie_suggestion_automation/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point & CORS
│   │   ├── config.py                # Environment configuration
│   │   ├── database.py              # SQLite + PostgreSQL unified layer
│   │   ├── models/schemas.py        # Pydantic schemas
│   │   ├── services/
│   │   │   ├── tmdb_service.py      # TMDB search, details & trailers
│   │   │   ├── suggestion_service.py# AI & category suggestion engine
│   │   │   ├── script_service.py    # Gemini Devanagari scriptwriter
│   │   │   ├── sarvam_tts_service.py# Sarvam AI Bulbul neural TTS
│   │   │   ├── collage_thumbnail_service.py # Shiro Bro 9:16 collage generator
│   │   │   ├── trailer_downloader_service.py # yt-dlp trailer downloader
│   │   │   └── video_composer_service.py # FFmpeg 9:16 video compositor
│   │   └── routes/                  # API routers
│   ├── storage/                     # Local media storage
│   ├── tests/                       # Complete pytest suite (8 passing tests)
│   ├── requirements.txt
│   ├── run.py
│   └── .env
├── frontend/
│   ├── app/                         # Next.js App router
│   ├── components/                  # React studio components
│   ├── lib/                         # API service & TypeScript types
│   ├── package.json
│   └── tsconfig.json
├── start_backend.bat                # 1-click backend runner
├── start_frontend.bat               # 1-click frontend runner
└── start_all.bat                    # 1-click fullstack runner
```
