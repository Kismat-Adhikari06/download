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
| `ALLOWED_ORIGINS` | `http://localhost:5173`   | Comma-separated CORS origins. Use `*` to allow all (Render). |
| `TEMP_DIR`        | system temp dir           | Where downloaded files are stored temporarily |

**Frontend:**

| Variable              | Default                  | Description                        |
|-----------------------|--------------------------|------------------------------------|
| `VITE_API_BASE_URL`   | `http://localhost:8000`  | Base URL of the FastAPI backend    |

---

## Deploying to Render

This project includes a [`render.yaml`](../render.yaml) Blueprint that defines both the backend web service and the frontend static site. You can deploy everything in one click:

### One-click deploy (Blueprint)

1. Push this repo to GitHub
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New +** → **Blueprint**
3. Connect your GitHub repo and select the `render.yaml` file
4. Render will create both services automatically
5. After deployment, grab the frontend URL and set it as the `VITE_API_BASE_URL` environment variable on the backend (see Step 3)

### Manual deployment

#### Step 1 — Backend (Web Service)

1. [dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service**
2. Connect your GitHub repo
3. **Name:** `universal-media-downloader-backend`
4. **Root Directory:** `web/backend`
5. **Runtime:** `Python 3`
6. **Build Command:** `pip install -r requirements.txt`
7. **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
8. **Health Check Path:** `/health`
9. Add environment variable: `ALLOWED_ORIGINS` = `*` (update after frontend is deployed)
10. Select the **Free** plan and deploy

> **System dependencies:** Render's Python environment includes `ffmpeg` by default. `aria2c` is optional but recommended for faster downloads.

#### Step 2 — Frontend (Static Site)

1. [dashboard.render.com](https://dashboard.render.com) → **New +** → **Static Site**
2. Connect your GitHub repo
3. **Name:** `universal-media-downloader-frontend`
4. **Root Directory:** `web/frontend`
5. **Build Command:** `npm install && npm run build`
6. **Publish Directory:** `dist`
7. Add environment variable: `VITE_API_BASE_URL` = `https://your-backend-url.onrender.com` (from Step 1)
8. Click **Deploy**

> Client-side routing is handled by the [`_redirects`](web/frontend/public/_redirects) file — all routes are rewritten to `index.html`.

#### Step 3 — Lock down CORS (optional but recommended)

Once the frontend is deployed and you have its URL:
1. Go to the backend Web Service → **Environment**
2. Update `ALLOWED_ORIGINS` to `https://your-frontend.onrender.com`
3. The backend will auto-restart with the new setting

### Blueprint environment variables

The `render.yaml` has two variables you **must** configure in the dashboard after the initial deploy:

| Service   | Variable            | Required value                          |
|-----------|---------------------|-----------------------------------------|
| Frontend  | `VITE_API_BASE_URL` | Your backend URL (e.g. `https://api.onrender.com`) |

### Important notes

- **Ephemeral filesystem:** Downloaded files are stored temporarily and deleted after serving or after 1 hour — this is normal for free-tier hosting
- **Audio downloads** require `ffmpeg`, which is pre-installed on all Render services
- **Large downloads** may time out on the free plan — consider upgrading for larger files
- If a deploy fails, check the Render logs for missing system packages or dependency errors

---

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
