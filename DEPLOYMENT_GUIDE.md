# 🚀 Online 24/7 Cloud Deployment Guide

Aapka laptop band hone par bhi agar aapko **apne phone se** Shorts create karne hain, toh is application ko cloud me 24/7 host karne ke do sabse best tareeqe hain:

---

## 🌟 Method 1: Railway (Backend) + Vercel (Frontend) — [Sabse Aasan, No Terminal Setup]

Is method me aapko koi Linux commands nahi chalani padengi. Sab kuch web UI se connect ho jata hai.

### Step 1: Code ko GitHub par Dalein
1. GitHub par ek naya repository banayein (e.g. `movie-suggestion-automation`).
2. Apne computer se pura code GitHub par push kar dein.

### Step 2: Backend ko Railway.app par Deploy karein
1. [Railway.app](https://railway.app/) par jayein aur GitHub se login karein.
2. **New Project** -> **Deploy from GitHub repo** click karein.
3. Root directory me `backend` select karein (Railway automatically `backend/Dockerfile` ko detect kar lega).
4. **Variables (Settings)** tab me ye keys add karein:
   - `GEMINI_API_KEY`: Aapki Gemini API key
   - `SARVAM_API_KEY`: Aapki Sarvam AI key
   - `TMDB_API_KEY`: Aapki TMDB key
   - `TMDB_BEARER_TOKEN`: Aapki TMDB bearer token
   - `CORS_ORIGINS`: `*`
5. **Volume add karein**:
   - Settings me **Volumes** -> Add Volume -> Mount path: `/app/storage` (taaki database aur videos hamesha save rahein).
6. **Networking** me **Generate Domain** par click karein.
   - Aapko ek backend URL mil jayega (e.g. `https://movie-backend.up.railway.app`).

### Step 3: Frontend ko Vercel.com par Deploy karein (100% Free)
1. [Vercel.com](https://vercel.com/) par login karein.
2. **Add New** -> **Project** -> Apna GitHub repo import karein.
3. Root Directory me `frontend` select karein.
4. **Environment Variables** add karein:
   - `NEXT_PUBLIC_API_URL`: `https://movie-backend.up.railway.app/api`
   - `NEXT_PUBLIC_MEDIA_URL`: `https://movie-backend.up.railway.app`
5. **Deploy** button click karein.
6. Aapko live website link mil jayegi (e.g. `https://movie-studio.vercel.app`).

**Bas! Ab aap apne mobile ke browser me ye Vercel link open karenge, aur aapka pura studio 24/7 chalega, chahe aapka laptop band ho!**

---

## ⚡ Method 2: Cheap VPS (Hetzner / Hostinger / DigitalOcean) — [Lowest Cost, Full Control]

Agar aap ek hi ₹300-400/month ke cloud server par sab chalana chahte hain:

1. Ubuntu 22.04 / 24.04 VPS lein.
2. VPS me Docker install karein:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-plugin
   ```
3. Repo clone karein:
   ```bash
   git clone <YOUR_GITHUB_REPO_URL>
   cd movie_suggestion_automation
   ```
4. `.env` file banakar API keys paste karein:
   ```bash
   nano backend/.env
   ```
5. Ek command se pura studio start karein:
   ```bash
   docker compose up -d --build
   ```
6. Aapka backend port `8001` aur frontend port `3001` par live ho jayega!
