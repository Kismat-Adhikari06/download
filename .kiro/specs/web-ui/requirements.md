# Requirements Document

## Introduction

The Web UI feature adds a browser-based interface to the Universal Media Downloader. It consists of a React (Vite) frontend and a FastAPI Python backend. The backend reuses the same yt-dlp download logic from the existing CLI tool. Users paste a URL, choose video or audio, click Download, and receive a temporary link to retrieve the file. The server automatically deletes the file after one hour or after it has been downloaded, whichever comes first.

There is no authentication, no user accounts, and no database. The project lives under a new `web/` directory with `web/frontend/` and `web/backend/` subdirectories.

## Glossary

- **Web_UI**: The browser-based interface consisting of the React frontend and the FastAPI backend together.
- **Frontend**: The React + Vite single-page application served to the user's browser.
- **Backend**: The FastAPI Python application that accepts download requests and serves temporary files.
- **Downloader_Core**: The reusable download logic extracted from `downloader.py` (the `download()` function and its helpers).
- **Temp_Store**: The server-side temporary directory where downloaded files are held before the user retrieves them.
- **Download_Job**: A single request to download one media item, identified by a unique job ID.
- **Temp_Link**: A time-limited URL path (valid for 1 hour) that the user can use to retrieve a completed Download_Job's file.
- **URL**: A web address provided by the user pointing to a video or audio source on a supported platform.
- **Format**: The requested output type — `video` (MP4) or `audio` (MP3).
- **yt-dlp**: The third-party Python library used to extract and download media from URLs.

---

## Requirements

### Requirement 1: URL Input

**User Story:** As a user, I want to paste a media URL into a text field in the browser, so that I can start a download without using the command line.

#### Acceptance Criteria

1. THE Frontend SHALL display a text input field for the user to enter a URL.
2. WHEN the user submits a download request with an empty URL field, THE Frontend SHALL display an inline validation error and SHALL NOT send a request to the Backend.
3. WHEN the user submits a download request with a non-empty URL, THE Frontend SHALL send the URL to the Backend.

---

### Requirement 2: Format Selection

**User Story:** As a user, I want to choose between video and audio before downloading, so that I get the file type I need.

#### Acceptance Criteria

1. THE Frontend SHALL display two selectable options — `Video` and `Audio` — for the user to choose the desired Format.
2. THE Frontend SHALL default to `Video` when the page first loads.
3. WHEN the user selects a Format option, THE Frontend SHALL reflect the selection visually before the download is submitted.
4. WHEN the user submits a download request, THE Frontend SHALL include the selected Format in the request sent to the Backend.

---

### Requirement 3: Download Trigger

**User Story:** As a user, I want a single Download button that starts the process, so that the interaction is straightforward.

#### Acceptance Criteria

1. THE Frontend SHALL display a Download button.
2. WHEN the user clicks the Download button and a valid URL is entered, THE Frontend SHALL send a download request to the Backend and display a loading indicator.
3. WHILE a download request is in progress, THE Frontend SHALL disable the Download button to prevent duplicate submissions.
4. WHEN the Backend returns a successful response, THE Frontend SHALL hide the loading indicator and display the Temp_Link.
5. IF the Backend returns an error response, THEN THE Frontend SHALL hide the loading indicator and display a descriptive error message.

---

### Requirement 4: Backend Download Endpoint

**User Story:** As a developer, I want a REST endpoint that accepts a URL and format, triggers a yt-dlp download, and returns a temporary link, so that the Frontend can retrieve the file.

#### Acceptance Criteria

1. THE Backend SHALL expose a `POST /download` endpoint that accepts a JSON body containing a `url` string and a `format` string (`"video"` or `"audio"`).
2. WHEN a valid request is received, THE Backend SHALL invoke the Downloader_Core to download the media and save the output file to the Temp_Store.
3. WHEN the download completes successfully, THE Backend SHALL return a JSON response containing a `download_url` field with the Temp_Link path and a `filename` field with the original file name.
4. IF the `url` field is empty or missing, THEN THE Backend SHALL return a `422` status code with a descriptive error message.
5. IF the `format` field is not `"video"` or `"audio"`, THEN THE Backend SHALL return a `422` status code with a descriptive error message.
6. IF the Downloader_Core raises an error during download, THEN THE Backend SHALL return a `500` status code with a descriptive error message.

---

### Requirement 5: Temporary File Serving

**User Story:** As a user, I want to click a link to download my file directly from the server, so that I can save it to my own machine.

#### Acceptance Criteria

1. THE Backend SHALL expose a `GET /files/{job_id}/{filename}` endpoint that serves the file associated with the given job ID.
2. WHEN a valid Temp_Link is requested, THE Backend SHALL respond with the file as an attachment download.
3. IF the requested job ID does not exist in the Temp_Store, THEN THE Backend SHALL return a `404` status code.
4. WHEN a file is served via its Temp_Link, THE Backend SHALL delete the file and its associated Temp_Store entry after the response is sent.

---

### Requirement 6: Automatic Temp File Cleanup

**User Story:** As a server operator, I want temporary files deleted automatically after one hour, so that the server does not accumulate unclaimed files indefinitely.

#### Acceptance Criteria

1. THE Backend SHALL schedule a cleanup task that runs at regular intervals while the server is running.
2. WHEN a Download_Job's file has existed in the Temp_Store for more than 1 hour without being retrieved, THE Backend SHALL delete the file from disk and remove the Temp_Store entry.
3. THE Backend SHALL delete only files that belong to expired Download_Jobs and SHALL NOT delete files that are still within their 1-hour window.

---

### Requirement 7: Downloader Core Reuse

**User Story:** As a developer, I want the web backend to reuse the existing download logic from `downloader.py`, so that there is a single source of truth for yt-dlp configuration.

#### Acceptance Criteria

1. THE Backend SHALL import and call the `download` function (or an equivalent extracted helper) from the existing `downloader.py` module rather than duplicating yt-dlp option construction.
2. WHEN the Backend invokes the Downloader_Core for a video request, THE Downloader_Core SHALL produce an MP4 file.
3. WHEN the Backend invokes the Downloader_Core for an audio request, THE Downloader_Core SHALL produce an MP3 file.

---

### Requirement 8: Frontend Download Link Display

**User Story:** As a user, I want to see a clickable download link after the server finishes processing, so that I can save the file to my machine.

#### Acceptance Criteria

1. WHEN the Backend returns a successful response, THE Frontend SHALL display a clickable link that triggers a file download in the browser.
2. THE Frontend SHALL display the filename alongside the download link so the user knows what they are downloading.
3. WHEN the user clicks the download link, THE Frontend SHALL initiate the file download using the Temp_Link returned by the Backend.

---

### Requirement 9: Project Structure

**User Story:** As a developer, I want the web UI code isolated in its own directory, so that it does not interfere with the existing CLI tool.

#### Acceptance Criteria

1. THE Web_UI SHALL be organized under a `web/` directory in the project root, with `web/frontend/` containing the React + Vite application and `web/backend/` containing the FastAPI application.
2. THE `web/` directory SHALL contain a `README.md` with instructions for running both the frontend and the backend locally.
3. THE Backend SHALL be runnable with a single command from the `web/backend/` directory.
4. THE Frontend SHALL be runnable with a single command from the `web/frontend/` directory.
