# Design Document

## Universal Media Downloader

---

## Overview

`downloader.py` is a single-file Python script. When run, it interactively asks the user for a URL and a format choice (`video` or `audio`), then delegates the download to `yt-dlp`. The result is saved to a `downloads/` folder in the project root.

There is no CLI argument parsing, no plugin architecture, and no metadata embedding — just a straightforward interactive script.

### Key Technology Choices

| Concern | Library | Rationale |
|---|---|---|
| Media extraction & download | [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Supports YouTube, Instagram, Twitter/X, Reddit, and thousands more; handles format conversion internally |
| Property-based testing | [Hypothesis](https://hypothesis.readthedocs.io/) | Standard Python PBT library; integrates with pytest |

---

## Script Structure

The entire implementation lives in a single file: `downloader.py`.

```
downloader.py
├── get_url()          — prompts user for a URL, validates it is non-empty
├── get_format()       — prompts user for "video" or "audio", validates choice
├── ensure_downloads_folder()  — creates downloads/ if it doesn't exist
├── download(url, fmt) — calls yt-dlp with the appropriate options
└── main()             — orchestrates the above in sequence
```

### Execution Flow

```
python downloader.py
  │
  ├─ Prompt: "Enter URL: "
  │     └─ empty → print error, exit(1)
  │
  ├─ Prompt: "Video or audio? [video/audio]: "
  │     └─ invalid → print error, exit(1)
  │
  ├─ Ensure downloads/ folder exists
  │
  └─ Call yt-dlp
        ├─ video → download as MP4 → save to downloads/
        └─ audio → extract audio as MP3 → save to downloads/
              └─ yt-dlp error → print error, exit(1)
```

---

## Implementation

### yt-dlp Options

**Video (MP4):**

```python
ydl_opts = {
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "merge_output_format": "mp4",
}
```

**Audio (MP3):**

```python
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}
```

yt-dlp derives the output filename from the media title automatically. The `downloads/` folder is the only output location.

### Error Handling

- Empty URL input → print message, `sys.exit(1)`
- Invalid format choice → print message, `sys.exit(1)`
- yt-dlp `DownloadError` → print the exception message, `sys.exit(1)`

No other error taxonomy is needed for this scope.

---

## Project Files

```
project-root/
├── downloader.py
├── .gitignore          ← contains "downloads/"
└── downloads/          ← created at runtime, git-ignored
```

---

## Correctness Properties

*These properties verify the helper logic in `downloader.py` using Hypothesis. They focus on the parts of the code that involve non-trivial logic: input validation and output path construction.*

### Property 1: Non-empty URL strings are accepted; empty strings are rejected

For any string `s`, `get_url()` (or its underlying validation logic) SHALL accept `s` when `s.strip()` is non-empty and reject it when `s.strip()` is empty.

**Validates: Requirement 1.2**

---

### Property 2: Only "video" and "audio" are valid format choices

For any string `s`, the format validation logic SHALL return `"video"` when `s` equals `"video"`, return `"audio"` when `s` equals `"audio"`, and signal an error for any other value — including case variants like `"Video"` or `"AUDIO"`.

**Validates: Requirements 2.2, 2.3, 2.4**

---

### Property 3: Output path is always inside the downloads/ folder

For any media title string `title` (including titles with special characters, spaces, or unicode), the output template `downloads/%(title)s.%(ext)s` SHALL produce a path whose first component is `downloads/` — the file is never saved outside that folder.

**Validates: Requirement 3.1**

---

## Testing Strategy

### Property-Based Tests (Hypothesis)

Located in `tests/test_downloader.py`. These test the pure validation and path logic without invoking yt-dlp.

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_empty_url_rejected(s):
    # s.strip() == "" → validation returns False
    # s.strip() != "" → validation returns True

@given(st.text())
def test_format_validation(s):
    # only "video" and "audio" are valid

@given(st.text(min_size=1))
def test_output_path_in_downloads_folder(title):
    # constructed path starts with "downloads/"
```

### Manual / Integration Testing

Because yt-dlp makes live network calls, end-to-end testing is done manually:

1. Run `python downloader.py`, enter a YouTube URL, choose `video` → verify MP4 appears in `downloads/`.
2. Run `python downloader.py`, enter a YouTube URL, choose `audio` → verify MP3 appears in `downloads/`.
3. Enter an empty URL → verify error message and non-zero exit.
4. Enter an invalid format choice → verify error message and non-zero exit.
