# Implementation Plan: Universal Media Downloader

## Overview

Implement `downloader.py` as a single-file Python script that interactively prompts the user for a URL and format choice, then downloads media via `yt-dlp` into a `downloads/` folder. Also includes a `.gitignore` entry and a property-based test suite using Hypothesis.

## Tasks

- [x] 1. Set up project scaffolding
  - Create `.gitignore` with a `downloads/` entry
  - Create an empty `downloads/` directory (or note it is created at runtime)
  - Create `tests/` directory and an empty `tests/test_downloader.py` file
  - Install dependencies: `yt-dlp` and `hypothesis` (document in a `requirements.txt`)
  - _Requirements: 5.1_

- [x] 2. Implement input validation helpers
  - [x] 2.1 Implement `validate_url(s)` — returns `True` when `s.strip()` is non-empty, `False` otherwise
    - Extract this logic as a standalone, pure function so it can be tested without I/O
    - _Requirements: 1.2_

  - [ ]* 2.2 Write property test for `validate_url` (Property 1)
    - **Property 1: Non-empty URL strings are accepted; empty strings are rejected**
    - Use `@given(st.text())` to assert `validate_url(s)` is `True` iff `s.strip() != ""`
    - **Validates: Requirement 1.2**

  - [x] 2.3 Implement `validate_format(s)` — returns `"video"` or `"audio"` when `s` matches exactly, raises `ValueError` otherwise
    - Case-sensitive: `"Video"` and `"AUDIO"` must be rejected
    - _Requirements: 2.2, 2.3, 2.4_

  - [ ]* 2.4 Write property test for `validate_format` (Property 2)
    - **Property 2: Only "video" and "audio" are valid format choices**
    - Use `@given(st.text())` to assert the function accepts only the two exact strings
    - **Validates: Requirements 2.2, 2.3, 2.4**

- [x] 3. Implement output path helper
  - [x] 3.1 Implement `build_output_template()` — returns the yt-dlp `outtmpl` string `"downloads/%(title)s.%(ext)s"`
    - Keep it as a pure function returning a string so it can be tested independently
    - _Requirements: 3.1_

  - [ ]* 3.2 Write property test for output path (Property 3)
    - **Property 3: Output path is always inside the downloads/ folder**
    - Use `@given(st.text(min_size=1))` to simulate title values and assert the rendered path starts with `"downloads/"`
    - **Validates: Requirement 3.1**

- [x] 4. Checkpoint — Ensure all property tests pass
  - Run `pytest tests/test_downloader.py` and confirm all tests are green before proceeding.

- [x] 5. Implement core script functions
  - [x] 5.1 Implement `get_url()` — prints prompt, reads input, calls `validate_url`, exits with error on failure
    - Print `"Enter URL: "` prompt; on empty input print an error message and call `sys.exit(1)`
    - _Requirements: 1.1, 1.2_

  - [x] 5.2 Implement `get_format()` — prints prompt, reads input, calls `validate_format`, exits with error on failure
    - Print `"Video or audio? [video/audio]: "` prompt; on invalid input print an error message and call `sys.exit(1)`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 5.3 Implement `ensure_downloads_folder()` — creates `downloads/` if it does not exist
    - Use `os.makedirs("downloads", exist_ok=True)`
    - _Requirements: 3.2_

  - [x] 5.4 Implement `download(url, fmt)` — builds yt-dlp options for the chosen format and runs the download
    - For `"video"`: use `format`, `outtmpl`, and `merge_output_format` options as specified in the design
    - For `"audio"`: use `format`, `outtmpl`, and `FFmpegExtractAudio` postprocessor options as specified in the design
    - Catch `yt_dlp.utils.DownloadError`, print the error message, and call `sys.exit(1)`
    - _Requirements: 3.1, 3.3, 4.1, 4.2, 4.3, 4.4_

- [x] 6. Implement `main()` and wire everything together
  - Call `get_url()`, `get_format()`, `ensure_downloads_folder()`, and `download(url, fmt)` in sequence
  - Guard execution with `if __name__ == "__main__": main()`
  - _Requirements: 1.1, 2.1, 3.1, 3.2, 3.3_

- [x] 7. Final checkpoint — Ensure all tests pass
  - Run `pytest tests/test_downloader.py` and confirm all tests are still green.
  - Verify `downloader.py` is importable without side effects (the `main()` guard works correctly).

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis and target pure helper functions — no yt-dlp network calls are made during testing
- End-to-end testing (live downloads) is done manually as described in the design document
