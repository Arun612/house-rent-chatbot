# Deploy RentChat: Render (Backend) + Vercel (Frontend)

## Overview

Your app is a **FastAPI backend** (Python, LangChain, Pinecone, Groq) + a **React/Vite frontend**.
- **Backend** → [Render](https://render.com) (Web Service, free tier)
- **Frontend** → [Vercel](https://vercel.com) (static/SPA, free tier)

The backend currently serves static files too (via `StaticFiles`), but for this deployment we decouple them — frontend goes to Vercel, backend to Render, and we update the `API_BASE` URL.

---

## User Review Required

> [!IMPORTANT]
> Your `.env` file contains **real API keys** (GROQ + Pinecone). These will **NOT** be committed to GitHub (it should be in `.gitignore`). We'll manually paste them into Render's environment variables dashboard instead.

> [!WARNING]
> Render's **free tier sleeps after 15 minutes of inactivity**. The first request after sleep can take ~30–50 seconds to wake up. Upgrade to paid ($7/mo) to avoid this.

> [!WARNING]
> The backend uses `sqlite.db` (SQLAlchemy) for session/document storage. On Render's free tier, the filesystem is **ephemeral** — the DB resets on every redeploy or restart. If you want persistence, we need to either use Render's Postgres addon or PostgreSQL (free tier available on Render). I'll flag this as a question below.

---

## Open Questions

> [!IMPORTANT]
> **Database Persistence**: The backend uses a local `sqlite.db` file. On Render free tier, this gets wiped on each redeploy. Do you want me to:
> - Keep SQLite as-is (sessions/docs reset on redeploy — acceptable for demo/portfolio)
> - Switch to Render's free PostgreSQL (persistent but needs a small code change in `database.py`)

---

## Proposed Changes

### Backend — Render Prep

#### [NEW] [render.yaml](file:///d:/OneDrive/Desktop/New folder/house-rent-chatbot/render.yaml)
Render blueprint file so the service is auto-detected. Specifies build command, start command, and env var placeholders.

#### [MODIFY] [requirements.txt](file:///d:/OneDrive/Desktop/New folder/house-rent-chatbot/backend/requirements.txt)
Add `psycopg2-binary` only if we switch to Postgres. Otherwise no change needed here.

#### [MODIFY] [.gitignore](file:///d:/OneDrive/Desktop/New folder/house-rent-chatbot/.gitignore)
Confirm `backend/.env` and `backend/sqlite.db` are ignored (they should already be).

#### [MODIFY] [main.py](file:///d:/OneDrive/Desktop/New folder/house-rent-chatbot/backend/main.py)
Remove or guard the `StaticFiles` mount (it will fail on Render because the frontend dist won't exist there). The backend will be API-only.

---

### Frontend — Vercel Prep

#### [MODIFY] [api.js](file:///d:/OneDrive/Desktop/New folder/house-rent-chatbot/frontend/src/api.js)
Change `API_BASE` from `http://localhost:8000` → **Render backend URL** (e.g. `https://house-rent-chatbot.onrender.com`). We'll use a `.env` variable so it's configurable:
```js
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
```

#### [NEW] [.env.production](file:///d:/OneDrive/Desktop/New folder/house-rent-chatbot/frontend/.env.production)
```
VITE_API_BASE_URL=https://YOUR-APP-NAME.onrender.com
```
(Updated after we know the Render URL)

#### [NEW] [vercel.json](file:///d:/OneDrive/Desktop/New folder/house-rent-chatbot/frontend/vercel.json)
Handles SPA routing — all paths fall back to `index.html`:
```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
```

---

## Deployment Steps (Manual — Done Together)

### Step 1 — Backend on Render
1. Go to [render.com](https://render.com), create account/login
2. **New → Web Service → Connect GitHub repo**
3. Set **Root Directory** = `backend`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add **Environment Variables** in dashboard:
   - `GROQ_API_KEY`
   - `PINECONE_API_KEY`
   - `PINECONE_INDEX_NAME=house-rent-chatbot`
   - `GROQ_LLM_MODEL=llama-3.1-8b-instant`
7. Deploy → copy the live URL (e.g. `https://house-rent-chatbot-xyz.onrender.com`)

### Step 2 — Frontend on Vercel
1. Go to [vercel.com](https://vercel.com), create account/login
2. **Add New Project → Import GitHub repo**
3. Set **Root Directory** = `frontend`
4. Add Environment Variable: `VITE_API_BASE_URL=https://YOUR-RENDER-URL.onrender.com`
5. Deploy → get the live URL

---

## Verification Plan

### Automated Tests
- `curl https://YOUR-RENDER-URL.onrender.com/health` → should return `{"status":"ok"}`

### Manual Verification
- Open the Vercel URL in browser
- Upload a PDF, start a chat, confirm responses stream correctly
- Check CORS is working (no browser console errors)
