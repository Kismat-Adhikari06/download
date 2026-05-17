# Implementation Plan: Web UI

## Overview

Build a React + Vite frontend and FastAPI backend for the Universal Media Downloader. The backend extracts headless download logic into `downloader_core.py`, manages in-memory job records via `TempStore`, and schedules cleanup with APScheduler. The frontend provides a single-page form with URL input, format selection, and a download link display. Plain CSS, no component libraries.

## Tasks

- [ ] 1. Set up project structure
  - Create `web/` directory with `web/frontend/` and `web/backend/` subdirectories
  - Create `web/README.md` with instructions for running both services locally
  - Create `web/backend/requirements.txt` listing `fastapi`, `uvicorn[standard]`, `apscheduler`, `yt-dlp`, `hypothesis`, `pytest`, `httpx`
  - Scaffold `web/backend/` with empty module files: `main.py`, `downloader_core.py`, `temp_store.py`, `scheduler.py`
  - Create `web/backend/tests/` directory with `__init__.py` and empty test files: `test_downloader_core.py`, `test_temp_store.py`, `test_routes.py`
  - Initialise the Vite + React project at `web/frontend/` (`npm create vite@latest frontend -- --template react`)
  - Add `vitest`, `@vitest/ui`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, and `fast-check` to `web/frontend/package.json`
  - Configure `vite.config.js` to include Vitest settings (`test.environment: 'jsdom'`, `test.setupFiles`)
  - Create `web/frontend/src/styles/main.css` as an empty placeholder
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 2. Implement `downloader_core.py`
  - [ ] 2.1 Write `download_to_path(url, fmt, output_dir)` in `web/backend/downloader_core.py`
    - Import and reuse `validate_url`, `validate_format`, `build_output_template`, and `_aria2c_available` from `downloader.py` (add the project root to `sys.path` if needed)
    - Set `outtmpl` to `output_dir/%(title)s.%(ext)s` instead of the hardcoded `downloads/` path
    - Raise `yt_dlp.utils.DownloadError` on failure; do NOT call `sys.exit()`
    - Return the absolute path of the downloaded file
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ]* 2.2 Write property test for `download_to_path` format → extension mapping
    - **Property 13: Format determines output file extension**
    - Mock yt-dlp so no real network call is made; assert `.mp4` for `"video"` and `.mp3` for `"audio"`
    - Use `@settings(max_examples=100)` and `st.sampled_from(["video", "audio"])`
    - Tag: `# Feature: web-ui, Property 13: Format determines output file extension`
    - **Validates: Requirements 7.2, 7.3**
    - _File: `web/backend/tests/test_downloader_core.py`_

- [ ] 3. Implement `TempStore` and `JobRecord`
  - [ ] 3.1 Write `JobRecord` dataclass and `TempStore` class in `web/backend/temp_store.py`
    - `JobRecord` fields: `job_id: str`, `file_path: str`, `filename: str`, `created_at: datetime` (UTC)
    - `TempStore` methods: `add(record)`, `get(job_id) -> JobRecord | None`, `remove(job_id)`, `expired_jobs(max_age_seconds=3600) -> list[JobRecord]`
    - Protect all mutations with a `threading.Lock`
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 3.2 Write property test for `expired_jobs` cleanup boundary
    - **Property 12: Cleanup deletes exactly the expired jobs**
    - Use `st.lists(st.timedeltas(min_value=timedelta(0), max_value=timedelta(hours=3)))` to generate a mix of ages
    - Assert that `expired_jobs()` returns exactly the records older than 1 hour and leaves the rest untouched
    - Tag: `# Feature: web-ui, Property 12: Cleanup deletes exactly the expired jobs`
    - **Validates: Requirements 6.2, 6.3**
    - _File: `web/backend/tests/test_temp_store.py`_

- [ ] 4. Implement `scheduler.py`
  - Write `cleanup_expired_jobs(store: TempStore)` that iterates `store.expired_jobs()`, calls `shutil.rmtree` on each job's parent directory, and calls `store.remove(job_id)` in a `finally` block
  - Write `start_scheduler(store: TempStore)` and `stop_scheduler()` functions that create and manage a `BackgroundScheduler` running `cleanup_expired_jobs` every 5 minutes
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 5. Implement FastAPI application in `main.py`
  - [ ] 5.1 Set up the FastAPI app with CORS, lifecycle hooks, and Pydantic models
    - Define `DownloadRequest`, `DownloadResponse`, and `ErrorResponse` Pydantic models
    - Add `CORSMiddleware` allowing `ALLOWED_ORIGINS` env var (default: `http://localhost:5173`)
    - On startup: create a temp root dir (from `TEMP_DIR` env var or `tempfile.mkdtemp()`), instantiate `TempStore`, start the scheduler
    - On shutdown: stop the scheduler
    - Register a `DownloadError` exception handler returning HTTP 500 with `{"detail": str(exc)}`
    - _Requirements: 4.1, 4.4, 4.5, 4.6_

  - [ ] 5.2 Implement `POST /download` route
    - Validate request with `DownloadRequest` (Pydantic handles 422 for empty URL and invalid format)
    - Generate a UUID4 job ID; create `{TEMP_DIR}/{job_id}/` subdirectory
    - Call `download_to_path(url, fmt, job_dir)` and capture the returned file path
    - Create a `JobRecord` and add it to `TempStore`
    - Return `DownloadResponse(download_url=f"/files/{job_id}/{filename}", filename=filename)`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ] 5.3 Implement `GET /files/{job_id}/{filename}` route
    - Look up `job_id` in `TempStore`; return 404 with `{"detail": "File not found"}` if missing
    - Return `FileResponse` with `Content-Disposition: attachment; filename="{filename}"`
    - Use a `BackgroundTask` to delete the file and remove the job record after the response is sent
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ]* 5.4 Write property test: invalid format values always return 422
    - **Property 8: Invalid format values always return 422**
    - Use `st.text().filter(lambda s: s not in ("video", "audio"))` with `@settings(max_examples=100)`
    - Tag: `# Feature: web-ui, Property 8: Invalid format values always return 422`
    - **Validates: Requirements 4.5**
    - _File: `web/backend/tests/test_routes.py`_

  - [ ]* 5.5 Write property test: file serving always sets `Content-Disposition: attachment`
    - **Property 9: File serving always sets Content-Disposition: attachment**
    - Use `st.binary()` to generate arbitrary file content; write to a temp job dir; assert header
    - Tag: `# Feature: web-ui, Property 9: File serving always sets Content-Disposition: attachment`
    - **Validates: Requirements 5.2**
    - _File: `web/backend/tests/test_routes.py`_

  - [ ]* 5.6 Write property test: missing job IDs always return 404
    - **Property 10: Missing job IDs always return 404**
    - Use `st.uuids()` to generate random job IDs not present in the store
    - Tag: `# Feature: web-ui, Property 10: Missing job IDs always return 404`
    - **Validates: Requirements 5.3**
    - _File: `web/backend/tests/test_routes.py`_

  - [ ]* 5.7 Write property test: served files are deleted after retrieval
    - **Property 11: Served files are always deleted after retrieval**
    - Use `st.binary()` for file content; assert file is gone from disk and job removed from store after GET
    - Tag: `# Feature: web-ui, Property 11: Served files are always deleted after retrieval`
    - **Validates: Requirements 5.4**
    - _File: `web/backend/tests/test_routes.py`_

- [ ] 6. Backend checkpoint — Ensure all backend tests pass
  - Run `pytest web/backend/tests/` and confirm all tests pass; ask the user if questions arise.

- [ ] 7. Implement frontend `api.js`
  - Create `web/frontend/src/api.js` with `requestDownload(url, format)` function
  - Read base URL from `import.meta.env.VITE_API_BASE_URL` (default `http://localhost:8000`)
  - Throw a descriptive `Error` for non-OK responses, extracting `detail` from the JSON body
  - _Requirements: 4.1, 3.2_

- [ ] 8. Implement React components
  - [ ] 8.1 Implement `UrlInput.jsx`
    - Render a controlled `<input type="text">` bound to the `url` prop
    - Display an inline validation error message when `urlError` prop is non-empty
    - _Requirements: 1.1, 1.2_

  - [ ] 8.2 Implement `FormatSelector.jsx`
    - Render two radio buttons (or equivalent) for `Video` and `Audio`
    - Default selection is `video`; reflect selection visually via CSS class
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 8.3 Implement `SubmitButton.jsx`
    - Render a `<button type="submit">Download</button>`
    - Accept a `disabled` prop; apply a disabled style when `disabled` is true
    - _Requirements: 3.1, 3.3_

  - [ ] 8.4 Implement `LoadingSpinner.jsx`, `DownloadLink.jsx`, and `ErrorMessage.jsx`
    - `LoadingSpinner`: simple animated CSS spinner, no external library
    - `DownloadLink`: render `<a href={download_url} download={filename}>{filename}</a>` plus visible filename text
    - `ErrorMessage`: render the error string in a styled container
    - _Requirements: 3.2, 3.4, 3.5, 8.1, 8.2, 8.3_

  - [ ] 8.5 Implement `StatusDisplay.jsx`
    - Switch between `LoadingSpinner`, `DownloadLink`, and `ErrorMessage` based on `status` prop (`'idle' | 'loading' | 'success' | 'error'`)
    - _Requirements: 3.2, 3.4, 3.5_

  - [ ] 8.6 Implement `DownloadForm.jsx`
    - Compose `UrlInput`, `FormatSelector`, and `SubmitButton`
    - On submit: validate URL client-side (set `urlError` if empty/whitespace); call `onSubmit` prop if valid
    - Disable submit button when `isLoading` prop is true
    - _Requirements: 1.2, 1.3, 2.4, 3.2, 3.3_

  - [ ] 8.7 Implement `App.jsx`
    - Own all state: `url`, `format`, `status`, `result`, `errorMsg`, `urlError`
    - On form submit: set `status = 'loading'`, call `requestDownload`, set `status = 'success'` or `'error'` based on outcome
    - Pass state and handlers down to `DownloadForm` and `StatusDisplay`
    - Import `main.css`
    - _Requirements: 1.3, 2.4, 3.2, 3.3, 3.4, 3.5_

- [ ] 9. Write frontend property-based tests
  - [ ]* 9.1 Write property test: whitespace URLs are rejected client-side
    - **Property 1: Whitespace URLs are rejected client-side**
    - Use `fc.stringOf(fc.constantFrom(' ', '\t', '\n'))` with `numRuns: 100`
    - Assert `urlError` is set and `requestDownload` is NOT called
    - Tag: `// Feature: web-ui, Property 1: Whitespace URLs are rejected client-side`
    - **Validates: Requirements 1.2**
    - _File: `web/frontend/src/__tests__/DownloadForm.test.jsx`_

  - [ ]* 9.2 Write property test: non-empty URLs are forwarded to the backend
    - **Property 2: Non-empty URLs are forwarded to the backend**
    - Use `fc.string({ minLength: 1 }).filter(s => s.trim() !== '')` with `numRuns: 100`
    - Assert `requestDownload` is called with the exact URL value
    - Tag: `// Feature: web-ui, Property 2: Non-empty URLs are forwarded to the backend`
    - **Validates: Requirements 1.3**
    - _File: `web/frontend/src/__tests__/DownloadForm.test.jsx`_

  - [ ]* 9.3 Write property test: selected format is included in every request
    - **Property 3: Selected format is included in every request**
    - Use `fc.constantFrom('video', 'audio')` with `numRuns: 100`
    - Assert `requestDownload` is called with the selected format value
    - Tag: `// Feature: web-ui, Property 3: Selected format is included in every request`
    - **Validates: Requirements 2.4**
    - _File: `web/frontend/src/__tests__/DownloadForm.test.jsx`_

  - [ ]* 9.4 Write property test: loading state is shown for any valid submission
    - **Property 4: Loading state is shown for any valid submission**
    - Use `fc.string({ minLength: 1 }).filter(s => s.trim() !== '')` with `numRuns: 100`
    - Assert `status === 'loading'` and submit button is disabled while request is in-flight
    - Tag: `// Feature: web-ui, Property 4: Loading state is shown for any valid submission`
    - **Validates: Requirements 3.2, 3.3**
    - _File: `web/frontend/src/__tests__/DownloadForm.test.jsx`_

  - [ ]* 9.5 Write property test: success response always produces a result state
    - **Property 5: Success response always produces a result state**
    - Use `fc.record({ download_url: fc.webUrl(), filename: fc.string() })` with `numRuns: 100`
    - Assert `status === 'success'` and `result` matches the response
    - Tag: `// Feature: web-ui, Property 5: Success response always produces a result state`
    - **Validates: Requirements 3.4, 8.1, 8.2**
    - _File: `web/frontend/src/__tests__/App.test.jsx`_

  - [ ]* 9.6 Write property test: error response always produces an error state
    - **Property 6: Error response always produces an error state**
    - Use `fc.string({ minLength: 1 })` for error messages with `numRuns: 100`
    - Assert `status === 'error'` and `errorMsg` contains the error message
    - Tag: `// Feature: web-ui, Property 6: Error response always produces an error state`
    - **Validates: Requirements 3.5**
    - _File: `web/frontend/src/__tests__/App.test.jsx`_

  - [ ]* 9.7 Write property test: download link renders all required information
    - **Property 14: Download link renders all required information**
    - Use `fc.record({ download_url: fc.webUrl(), filename: fc.string({ minLength: 1 }) })` with `numRuns: 100`
    - Assert `<a>` has correct `href`, `download` attribute, and visible filename text
    - Tag: `// Feature: web-ui, Property 14: Download link renders all required information`
    - **Validates: Requirements 8.1, 8.2, 8.3**
    - _File: `web/frontend/src/__tests__/DownloadLink.test.jsx`_

- [ ] 10. Add plain CSS styles
  - Write styles in `web/frontend/src/styles/main.css` for the form layout, format selector, submit button (including disabled state), loading spinner animation, download link display, and error message
  - No external CSS frameworks or component libraries
  - _Requirements: 9.1_

- [ ] 11. Wire everything together and write `web/README.md`
  - [ ] 11.1 Verify `main.jsx` imports `App.jsx` and mounts to `#root`
    - Confirm `index.html` has a `<div id="root">` and loads `main.jsx`
    - _Requirements: 9.1_

  - [ ] 11.2 Write `web/README.md`
    - Include backend setup: `cd web/backend && pip install -r requirements.txt && uvicorn main:app --reload`
    - Include frontend setup: `cd web/frontend && npm install && npm run dev`
    - Document the `VITE_API_BASE_URL` and `ALLOWED_ORIGINS` environment variables
    - _Requirements: 9.2, 9.3, 9.4_

- [ ] 12. Final checkpoint — Ensure all tests pass
  - Run `pytest web/backend/tests/` and `npm run test --run` (or `vitest --run`) in `web/frontend/`
  - Ensure all tests pass; ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Checkpoints (tasks 6 and 12) ensure incremental validation
- Property tests validate universal correctness properties (Properties 1–14 from the design)
- Unit tests validate specific examples and edge cases
- `downloader.py` at the project root is NOT modified; `downloader_core.py` is a new file
