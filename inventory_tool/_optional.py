"""Single place that decides whether psutil is available.

Every collector imports PSUTIL from here instead of doing its own
try/except import, so there is exactly one code path that decides
"do we have the rich backend or not."
"""
try:
    import psutil  # type: ignore
    HAS_PSUTIL = True
except ImportError:  # pragma: no cover - exercised via tests that monkeypatch this flag
    psutil = None  # type: ignore
    HAS_PSUTIL = False
