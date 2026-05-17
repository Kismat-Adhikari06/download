"""Property-based tests for downloader.py helper functions using Hypothesis."""

from hypothesis import given, strategies as st

from downloader import validate_url, validate_format, build_output_template


# ---------------------------------------------------------------------------
# Property 1: Non-empty URL strings are accepted; empty strings are rejected
# Validates: Requirement 1.2
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
# Property 2: Only "video" and "audio" are valid format choices
# Validates: Requirements 2.2, 2.3, 2.4
# ---------------------------------------------------------------------------

@given(st.text())
def test_validate_format_property(s: str) -> None:
    """For any string s, validate_format returns 'video'/'audio' only for exact matches,
    and raises ValueError for everything else."""
    if s == "video":
        assert validate_format(s) == "video"
    elif s == "audio":
        assert validate_format(s) == "audio"
    else:
        try:
            validate_format(s)
            raise AssertionError(f"Expected ValueError for input {s!r}, but no exception was raised")
        except ValueError:
            pass  # expected


# ---------------------------------------------------------------------------
# Property 3: Output path is always inside the downloads/ folder
# Validates: Requirement 3.1
# ---------------------------------------------------------------------------

@given(st.text(min_size=1))
def test_build_output_template_property(title: str) -> None:
    """build_output_template() always returns a string starting with 'downloads/'."""
    template = build_output_template()
    assert isinstance(template, str), "build_output_template() must return a string"
    assert template.startswith("downloads/"), (
        f"Output template must start with 'downloads/', got {template!r}"
    )
