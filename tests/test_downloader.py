"""Property-based tests for downloader.py helper functions using Hypothesis."""

from hypothesis import given, strategies as st

from downloader import validate_url, parse_urls, validate_format, build_output_template


# ---------------------------------------------------------------------------
# Property 1: Non-empty URL strings are accepted; empty strings are rejected
# ---------------------------------------------------------------------------

@given(st.text())
def test_validate_url_property(s: str) -> None:
    """For any string s, validate_url(s) returns True iff s.strip() != ''."""
    result = validate_url(s)
    if s.strip() != "":
        assert result is True, f"Expected True for non-empty stripped string, got {result!r} (input={s!r})"
    else:
        assert result is False, f"Expected False for empty/whitespace string, got {result!r} (input={s!r})"


# ---------------------------------------------------------------------------
# Property 2: parse_urls splits on whitespace and drops empties
# ---------------------------------------------------------------------------

@given(st.lists(st.text()))
def test_parse_urls_pieces(pieces: list[str]) -> None:
    """parse_urls should split joined pieces on whitespace and only keep non-empty strings."""
    raw = " ".join(pieces)
    result = parse_urls(raw)
    expected = [p.strip() for p in raw.split() if p.strip()]
    assert result == expected


# ---------------------------------------------------------------------------
# Property 3: Accepted format values
# ---------------------------------------------------------------------------

@given(st.text())
def test_validate_format_property(s: str) -> None:
    """validate_format accepts '1'/'video' -> 'video' and '2'/'audio' -> 'audio';
    raises ValueError for everything else."""
    if s in ("1", "video"):
        assert validate_format(s) == "video"
    elif s in ("2", "audio"):
        assert validate_format(s) == "audio"
    else:
        try:
            validate_format(s)
            raise AssertionError(f"Expected ValueError for input {s!r}, but no exception was raised")
        except ValueError:
            pass  # expected


# ---------------------------------------------------------------------------
# Property 4: Output path is always inside the downloads/ folder
# ---------------------------------------------------------------------------

@given(st.text(min_size=1))
def test_build_output_template_property(title: str) -> None:
    """build_output_template() always returns a string starting with 'downloads/'."""
    template = build_output_template()
    assert isinstance(template, str), "build_output_template() must return a string"
    assert template.startswith("downloads/"), (
        f"Output template must start with 'downloads/', got {template!r}"
    )
