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
The frontend communicates with the backend over HTTP (CORS-enabled for local development).

---

## Backend setup

### Prerequisites

- Python 3.11+
- `ffmpeg` on PATH (required for audio extraction)
- `aria2c` on PATH (optional — enables faster multi-connection downloads)

### Install dependencies

```bash
cd web/backend
pip install -r requirements.txt
```

### Run the development server

```bash
uvicorn main:app --reload
```

The API will be available at **http://localhost:8000**.

### Environment variables

| Variable          | Default                   | Description                                      |
|-------------------|---------------------------|--------------------------------------------------|
| `ALLOWED_ORIGINS` | `http://localhost:5173`   | Comma-separated list of allowed CORS origins     |
| `TEMP_DIR`        | system temp dir           | Directory where downloaded files are stored temporarily |

Example:

```bash
ALLOWED_ORIGINS="http://localhost:5173,https://myapp.example.com" uvicorn main:app --reload
```

### Run backend tests

```bash
pytest tests/
```

---

## Frontend setup

### Prerequisites

- Node.js 18+

### Install dependencies

```bash
cd web/frontend
npm install
```

### Run the development server

```bash
npm run dev
```

The app will be available at **http://localhost:5173**.

### Environment variables

| Variable              | Default                  | Description                        |
|-----------------------|--------------------------|------------------------------------|
| `VITE_API_BASE_URL`   | `http://localhost:8000`  | Base URL of the FastAPI backend    |

Create a `.env.local` file in `web/frontend/` to override:

```
VITE_API_BASE_URL=http://localhost:8000
```

### Run frontend tests

```bash
npm test
```

---

## Running both services together (local development)

Open two terminals:

**Terminal 1 — backend:**
```bash
cd web/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Terminal 2 — frontend:**
```bash
cd web/frontend
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## API reference

### `POST /download`

Request body:
```json
{ "url": "https://www.youtube.com/watch?v=...", "format": "video" }
```

`format` must be `"video"` (MP4) or `"audio"` (MP3).

Success response (`200`):
```json
{ "download_url": "/files/{job_id}/{filename}", "filename": "My Video.mp4" }
```

Error responses:
- `422` — empty URL or invalid format
- `500` — yt-dlp download failure

### `GET /files/{job_id}/{filename}`

Streams the file as an attachment download.  
The file is **deleted from the server** after it is served.

- `404` — job ID not found (file already downloaded or expired)
