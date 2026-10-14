"""Path policy: sources are read-only; all derivations go to scratch outside source trees."""

from __future__ import annotations

from pathlib import Path

_scratch_roots: list[Path] = []
_forbidden_roots: list[Path] = []
_source_roots: list[Path] = []


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
