# Universal Media Downloader — CLI Plan

## Goal

Turn `downloader.py` into a system-wide command (`videodownloader`) that can be
installed on **any** laptop with a single `pip` command.

---

## How it works (already implemented)

### Interactive mode

Run without arguments:

```
$ python downloader.py
Enter URL(s) (separate multiple with spaces): https://youtube.com/watch?v=abc https://youtube.com/watch?v=def
Format: 1) Video  2) Audio  [1/2]: 1

[1/2] Downloading: https://youtube.com/watch?v=abc
...
[2/2] Downloading: https://youtube.com/watch?v=def
...
All done! 2 file(s) saved to the downloads/ folder.
```

### CLI argument mode

Pass one or more URLs directly:

```
$ python downloader.py https://youtube.com/watch?v=abc
Format: 1) Video  2) Audio  [1/2]: 2
```

Or multiple:

```
$ python downloader.py https://url1 https://url2 https://url3
```

### Format selection

| Input | Result |
|-------|--------|
| `1` or `video` | Downloads video (MP4) |
| `2` or `audio` | Downloads audio (MP3) |

### Failure handling

If one URL fails, the script continues with the rest and shows a summary:

```
Done! 2 succeeded, 1 failed.
```

---

## What still needs to be done (for pip install)

1. **Add `pyproject.toml`** — tells pip how to install it, maps the
   `videodownloader` command to `downloader.py:main()`

2. **Push to GitHub** — then install anywhere with:
   ```bash
   pip install git+https://github.com/Kismat-Adhikari06/download.git
   ```

---

## Future ideas

- **Auto-update reminder** — script checks GitHub for newer version on each run
- **PyPI release** — `pip install videodownloader` (no URL)
- **Standalone `.exe`** — no Python needed at all

---

## Quick reference

| Action | Command |
|--------|---------|
| Fresh install | `pip install git+https://github.com/Kismat-Adhikari06/download.git` |
| Use it | `videodownloader https://youtube.com/watch?v=...` |
| Use with audio | `videodownloader https://youtube.com/watch?v=...` then choose `2` |
| Multiple URLs | `videodownloader https://url1 https://url2` |
| Update to latest | `pip install -U git+https://github.com/Kismat-Adhikari06/download.git` |
