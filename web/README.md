# Universal Media Downloader — Web UI

A browser-based interface for the Universal Media Downloader.  
Paste a URL, choose Video or Audio, click Download, and save the file.

---

## Architecture

```
web/
├── backend/    FastAPI Python application
└── frontend/   React + Vite single-page application
```

The backend reuses the yt-dlp download logic from `downloader.py` at the project root.  
The frontend communicates with the backend over HTTP (CORS-enabled).

---

## Local development

### Backend

**Prerequisites:** Python 3.11+, `ffmpeg` on PATH, `aria2c` on PATH (optional)

```bash
cd web/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

API available at **http://localhost:8000**

### Frontend

**Prerequisites:** Node.js 18+

```bash
cd web/frontend
npm install
npm run dev
```

App available at **http://localhost:5173**

### Environment variables

**Backend:**

| Variable          | Default                   | Description                                  |
|-------------------|---------------------------|----------------------------------------------|
| `ALLOWED_ORIGINS` | `http://localhost:5173`   | Comma-separated CORS origins. Use `*` to allow all (Railway). |
| `TEMP_DIR`        | system temp dir           | Where downloaded files are stored temporarily |

**Frontend:**

| Variable              | Default                  | Description                        |
|-----------------------|--------------------------|------------------------------------|
| `VITE_API_BASE_URL`   | `http://localhost:8000`  | Base URL of the FastAPI backend    |

---

## Deploying to Railway

Deploy the backend and frontend as **two separate Railway services** from the same repo.

### Step 1 — Deploy the backend

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select this repo
3. Set **Root Directory** to `web/backend`
4. Railway auto-detects Python + nixpacks (ffmpeg and aria2c are installed automatically)
5. Add environment variable: `ALLOWED_ORIGINS` = `*` (update to your frontend URL after step 2)
6. Deploy — note the public URL (e.g. `https://your-backend.up.railway.app`)

### Step 2 — Deploy the frontend

1. In the same Railway project → Add Service → GitHub repo (same repo)
2. Set **Root Directory** to `web/frontend`
3. Add environment variable: `VITE_API_BASE_URL` = `https://your-backend.up.railway.app`
4. Deploy

### Step 3 — Lock down CORS (optional but recommended)

Once the frontend is deployed and you have its URL:
1. Go to the backend service → Variables
2. Update `ALLOWED_ORIGINS` to your frontend URL (e.g. `https://your-frontend.up.railway.app`)
3. Redeploy the backend

### Notes

- `ffmpeg` and `aria2c` are installed automatically via `nixpacks.toml` — no manual setup needed
- Temp files are stored on Railway's ephemeral filesystem — they survive for 1 hour or until downloaded
- If the backend restarts mid-download, the download link will return 404 (acceptable for a free tier)
- Audio downloads require `ffmpeg` — this is handled automatically on Railway

---

## API reference

### `POST /download`

```json
{ "url": "https://www.youtube.com/watch?v=...", "format": "video" }
```

`format` must be `"video"` (MP4) or `"audio"` (MP3).

Success (`200`):
```json
{ "download_url": "/files/{job_id}/{filename}", "filename": "My Video.mp4" }
```

Errors: `422` (bad input), `500` (yt-dlp failure)

### `GET /files/{job_id}/{filename}`

Streams the file as an attachment. **File is deleted after serving.**  
Returns `404` if the job doesn't exist or has already been downloaded.
