# Requirements Document

## Introduction

Universal Media Downloader is a single Python script (`downloader.py`) that interactively asks the user for a URL and whether they want video or audio, then downloads the media to a local `downloads/` folder. It uses `yt-dlp` under the hood, which supports YouTube, Instagram, Twitter/X, Reddit, and thousands of other platforms.

## Glossary

- **Downloader**: The `downloader.py` script responsible for prompting the user and downloading media.
- **URL**: A web address provided by the user pointing to a video or audio source.
- **Format**: The output container type — `mp4` for video, `mp3` for audio.
- **Downloads_Folder**: The `downloads/` directory in the project root where all media is saved.
- **yt-dlp**: The third-party Python library used to extract and download media from URLs.

---

## Requirements

### Requirement 1: Interactive URL Prompt

**User Story:** As a user, I want to be asked for a URL when I run the script, so that I don't need to remember any command-line flags.

#### Acceptance Criteria

1. WHEN the user runs `python downloader.py`, THE Downloader SHALL prompt the user to enter a URL.
2. IF the user enters an empty string, THEN THE Downloader SHALL display an error message and exit without attempting a download.

---

### Requirement 2: Format Selection Prompt

**User Story:** As a user, I want to choose between video and audio, so that I get the file type I need.

#### Acceptance Criteria

1. AFTER the user provides a URL, THE Downloader SHALL prompt the user to choose between `video` and `audio`.
2. IF the user enters `video`, THEN THE Downloader SHALL download the media as an MP4 file.
3. IF the user enters `audio`, THEN THE Downloader SHALL download the media as an MP3 file.
4. IF the user enters anything other than `video` or `audio`, THEN THE Downloader SHALL display an error message and exit without attempting a download.

---

### Requirement 3: Download to Downloads Folder

**User Story:** As a user, I want downloaded files saved to a predictable location, so that I can easily find them.

#### Acceptance Criteria

1. THE Downloader SHALL save all downloaded files to a `downloads/` folder in the project root.
2. IF the `downloads/` folder does not exist, THEN THE Downloader SHALL create it before saving any files.
3. WHEN a download completes, THE Downloader SHALL display the path of the saved file.

---

### Requirement 4: yt-dlp Integration

**User Story:** As a user, I want the script to work with URLs from many different platforms, so that I don't need separate tools for each site.

#### Acceptance Criteria

1. THE Downloader SHALL use `yt-dlp` to handle URL extraction and downloading.
2. WHEN downloading video, THE Downloader SHALL instruct yt-dlp to produce an MP4 file.
3. WHEN downloading audio, THE Downloader SHALL instruct yt-dlp to extract audio and produce an MP3 file.
4. IF yt-dlp raises an error during download, THEN THE Downloader SHALL display a descriptive error message and exit with a non-zero status code.

---

### Requirement 5: .gitignore Entry

**User Story:** As a developer, I want the `downloads/` folder excluded from version control, so that downloaded media files are not accidentally committed.

#### Acceptance Criteria

1. THE project SHALL include a `.gitignore` file that contains an entry for `downloads/`.
