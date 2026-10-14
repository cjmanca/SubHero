"""Path policy: sources are read-only; all derivations go to scratch outside source trees."""

from __future__ import annotations

import re
from pathlib import Path

_scratch_roots: list[Path] = []
_forbidden_roots: list[Path] = []
_source_roots: list[Path] = []

SAFE_ID_MAX_LEN = 128
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def is_safe_id(value: str) -> bool:
    """Strict validator for user-controlled ids used in paths/registry keys.

    Non-empty, at most SAFE_ID_MAX_LEN chars, charset [A-Za-z0-9._-] only (so
    no '/', '\\', '..', NUL, whitespace, or shell/metacharacters), and no
    leading '.' (so no '.'/'..' and no hidden files).
    """
    return (
        isinstance(value, str)
        and 0 < len(value) <= SAFE_ID_MAX_LEN
        and not value.startswith(".")
        and _SAFE_ID_RE.match(value) is not None
    )


def require_safe_id(value: str, label: str) -> None:
    if not is_safe_id(value):
        raise ValueError(
            f"REFUSED: {label} {value!r} is not a safe id (required: non-empty, "
            f"<= {SAFE_ID_MAX_LEN} chars, [A-Za-z0-9._-] only, no leading '.' "
            "or path separators)"
        )


def configure(
    scratch_roots: list[Path],
    source_roots: list[Path],
    forbidden_roots: list[Path] | None = None,
) -> None:
    _scratch_roots[:] = [p.resolve() for p in scratch_roots]
    _source_roots[:] = [p.resolve() for p in source_roots]
    _forbidden_roots[:] = [p.resolve() for p in (forbidden_roots or [])]


def reset() -> None:
    _scratch_roots.clear()
    _source_roots.clear()
    _forbidden_roots.clear()


def _under(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def ensure_scratch_path(path: Path) -> Path:
    resolved = Path(path).resolve()
    if not _scratch_roots:
        raise RuntimeError("scratch roots not configured")
    if not _under(resolved, _scratch_roots):
        raise RuntimeError(f"path is not inside a scratch root: {resolved}")
    if _under(resolved, _source_roots):
        raise RuntimeError(
            f"refusing to write inside a read-only source root: {resolved}"
        )
    if _under(resolved, _forbidden_roots):
        raise RuntimeError(
            f"refusing to write inside a forbidden (e.g. Plex-watched) root: {resolved}"
        )
    return resolved


def add_source_root(path: Path) -> None:
    resolved = Path(path).resolve()
    if resolved not in _source_roots:
        _source_roots.append(resolved)


def add_forbidden_root(path: Path) -> None:
    resolved = Path(path).resolve()
    if resolved not in _forbidden_roots:
        _forbidden_roots.append(resolved)
