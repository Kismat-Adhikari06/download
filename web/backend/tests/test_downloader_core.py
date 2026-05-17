"""
Tests for downloader_core.download_to_path().

Property 13: Format determines output file extension.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import downloader_core  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_ydl(output_dir: str, filename: str):
    """Return a mock YoutubeDL context manager that writes a dummy file."""

    def fake_download(urls):
        # Write a dummy file so the fallback scanner finds it
        out = Path(output_dir) / filename
        out.write_bytes(b"fake media content")

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.download = fake_download
    return mock_ydl


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_download_to_path_video_returns_mp4(tmp_path):
    """download_to_path with fmt='video' should return a .mp4 path."""
    output_dir = str(tmp_path)
    mock_ydl = _make_mock_ydl(output_dir, "test_video.mp4")

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        result = downloader_core.download_to_path(
            "https://example.com/video", "video", output_dir
        )

    assert result.endswith(".mp4")
    assert Path(result).exists()


def test_download_to_path_audio_returns_mp3(tmp_path):
    """download_to_path with fmt='audio' should return a .mp3 path."""
    output_dir = str(tmp_path)
    mock_ydl = _make_mock_ydl(output_dir, "test_audio.mp3")

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        result = downloader_core.download_to_path(
            "https://example.com/audio", "audio", output_dir
        )

    assert result.endswith(".mp3")
    assert Path(result).exists()


def test_download_to_path_invalid_format_raises(tmp_path):
    """download_to_path with an invalid format should raise ValueError."""
    with pytest.raises(ValueError):
        downloader_core.download_to_path(
            "https://example.com/video", "invalid", str(tmp_path)
        )


def test_download_to_path_returns_absolute_path(tmp_path):
    """download_to_path should always return an absolute path."""
    output_dir = str(tmp_path)
    mock_ydl = _make_mock_ydl(output_dir, "video.mp4")

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        result = downloader_core.download_to_path(
            "https://example.com/video", "video", output_dir
        )

    assert Path(result).is_absolute()


# ---------------------------------------------------------------------------
# Property-based test — Property 13: Format determines output file extension
# Feature: web-ui, Property 13: Format determines output file extension
# Validates: Requirements 7.2, 7.3
# ---------------------------------------------------------------------------


@given(fmt=st.sampled_from(["video", "audio"]))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_format_determines_extension(fmt, tmp_path):
    """
    # Feature: web-ui, Property 13: Format determines output file extension
    **Validates: Requirements 7.2, 7.3**

    For any valid format value, download_to_path returns a file with the
    expected extension: .mp4 for 'video', .mp3 for 'audio'.
    """
    expected_ext = ".mp4" if fmt == "video" else ".mp3"
    filename = f"media{expected_ext}"
    output_dir = str(tmp_path / fmt)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    mock_ydl = _make_mock_ydl(output_dir, filename)

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        result = downloader_core.download_to_path(
            "https://example.com/media", fmt, output_dir
        )

    assert Path(result).suffix == expected_ext
