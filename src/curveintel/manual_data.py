"""Helpers for manual smoke scripts and local dataset discovery."""

from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "examples"
DEFAULT_REPORTS_DIR = REPO_ROOT / "reports"
TEST_REPORTS_DIR = REPO_ROOT / "tests" / "reports"
SAMPLE_NIST_CSV = EXAMPLES_DIR / "sample_nist.csv"
NIST_DIR_NAME = "nist_numisheet"
NIST_REFERENCE_NAME = "C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv"
USERIES_REFERENCE_NAME = "U00FeDP980R01T1.405W12.7.csv"
ZENODO_REFERENCE_RELATIVE = (
    Path("Zenodo Structural Metallic DB")
    / "Clean_Data_v1-0-0"
    / "Clean_Data"
    / "S355J2_Plates"
    / "S355J2_N_25mm"
    / "S_8_00_N_5.csv"
)


def _normalize_path(raw_path: str | Path | None) -> Path | None:
    """Normalize a path-like value without requiring it to exist."""

    if raw_path in {None, ""}:
        return None
    return Path(raw_path).expanduser().resolve()


def _first_existing(*candidates: Path | None) -> Path | None:
    """Return the first existing path from the provided candidates."""

    for candidate in candidates:
        if candidate is not None and candidate.exists():
            return candidate
    return None


def get_dataset_root(raw_path: str | Path | None = None) -> Path | None:
    """Resolve the optional external dataset root for manual smoke scripts."""

    explicit = _normalize_path(raw_path)
    if explicit is not None:
        return explicit if explicit.exists() else None

    configured = _normalize_path(os.getenv("CURVEINTEL_DATASET_ROOT"))
    if configured is not None and configured.exists():
        return configured
    return None


def get_default_batch_input_dir(raw_path: str | Path | None = None) -> Path:
    """Return a sensible default batch input directory."""

    dataset_root = get_dataset_root(raw_path)
    return (
        _first_existing(
            dataset_root / NIST_DIR_NAME if dataset_root is not None else None,
            EXAMPLES_DIR,
        )
        or EXAMPLES_DIR
    )


def get_default_batch_output_dir() -> Path:
    """Return the default reports directory for manual batch runs."""

    return DEFAULT_REPORTS_DIR


def get_nist_directory(raw_path: str | Path | None = None) -> Path | None:
    """Resolve the NIST dataset directory when available."""

    dataset_root = get_dataset_root(raw_path)
    return _first_existing(dataset_root / NIST_DIR_NAME if dataset_root is not None else None)


def get_nist_reference_csv(raw_path: str | Path | None = None) -> Path | None:
    """Resolve the canonical NIST sample CSV with an examples fallback."""

    nist_dir = get_nist_directory(raw_path)
    return _first_existing(
        nist_dir / NIST_REFERENCE_NAME if nist_dir is not None else None,
        SAMPLE_NIST_CSV,
    )


def get_u_series_reference_csv(raw_path: str | Path | None = None) -> Path | None:
    """Resolve the U-series manual smoke CSV when available."""

    nist_dir = get_nist_directory(raw_path)
    return _first_existing(nist_dir / USERIES_REFERENCE_NAME if nist_dir is not None else None)


def get_zenodo_reference_csv(raw_path: str | Path | None = None) -> Path | None:
    """Resolve the optional Zenodo structural-metallic sample file."""

    dataset_root = get_dataset_root(raw_path)
    return _first_existing(
        dataset_root / ZENODO_REFERENCE_RELATIVE if dataset_root is not None else None
    )


def manual_dataset_help() -> str:
    """Return a short operator-facing hint for manual dataset setup."""

    return (
        "Set CURVEINTEL_DATASET_ROOT to a local dataset directory that contains "
        "`nist_numisheet/` and any optional reference folders. When the variable "
        "is not set, some manual smoke scripts fall back to `examples/sample_nist.csv`."
    )

// Contributed via automated bounty system
