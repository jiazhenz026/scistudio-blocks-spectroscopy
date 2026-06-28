"""SpectralDataset previewer contract tests (SC-004, SC-005, SC-006).

Drives the package dataset provider against a real bounded ``PreviewDataAccess``
reading a real core ``CompositeStore`` composite (the way a ``SpectralDataset``
actually persists: a ``manifest.json`` of slot refs), asserting:

- exact ``SpectralDataset`` refs route to the dataset previewer (SC-004);
- the envelope is a COMPOSITE envelope exposing the slot inventory + a paginated
  index table, with slots resolved through the sanctioned
  ``PreviewDataAccess.composite_slot_ref`` (ADR-052 §8.5);
- grouped plotting is available over arbitrary index columns including
  ``material`` and a preparation/condition column (SC-005);
- export/save controls for figures, visible rows, and grouped summaries exist
  (SC-006);
- the pure ``compute_dataset_diagnostics`` helper flags health issues in
  isolation (SC-005 health surface).
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pyarrow as pa
from scistudio.core.storage.composite_store import CompositeStore
from scistudio.core.types import StorageReference
from scistudio.previewers.data_access import PreviewDataAccess
from scistudio.previewers.models import (
    EnvelopeKind,
    OwnerKind,
    PreviewerSpec,
    PreviewLimits,
    PreviewRequest,
    PreviewTarget,
    TargetKind,
)

from scistudio_blocks_spectroscopy.previewers import (
    SPECTRAL_DATASET_PREVIEWER_ID,
    get_previewers,
)
from scistudio_blocks_spectroscopy.previewers.providers import (
    compute_dataset_diagnostics,
    spectral_dataset_provider,
)

_DATASET_CHAIN = ("DataObject", "CompositeData", "SpectralDataset")


def _spec() -> PreviewerSpec:
    for spec in get_previewers():
        if spec.previewer_id == SPECTRAL_DATASET_PREVIEWER_ID:
            return cast(PreviewerSpec, spec)
    raise AssertionError(SPECTRAL_DATASET_PREVIEWER_ID)


def _write_dataset(tmp_path: Path, *, index_cols: dict, spectra_cols: dict) -> StorageReference:
    """Persist a SpectralDataset-shaped composite via the core CompositeStore.

    This mirrors how a real ``SpectralDataset`` (a ``CompositeData`` subclass)
    lands on disk — a ``manifest.json`` recording each slot's backend/path/format
    — so the previewer resolves slots through ``composite_slot_ref`` against the
    authoritative manifest, exactly as in production.
    """
    return CompositeStore().write(
        {
            "index": ("arrow", pa.table(index_cols)),
            "spectra": ("arrow", pa.table(spectra_cols)),
        },
        StorageReference(backend="composite", path=str(tmp_path / "dataset")),
    )


def _request(
    storage: StorageReference,
    record_md: dict,
    extra_query: dict | None = None,
) -> PreviewRequest:
    return PreviewRequest(
        target=PreviewTarget(
            kind=TargetKind.DATA_REF,
            ref=storage.path,
            recorded_type="SpectralDataset",
            type_chain=_DATASET_CHAIN,
        ),
        spec=_spec(),
        query=dict(extra_query or {}),
        data_access=PreviewDataAccess(),
        limits=PreviewLimits(),
        session_id=None,
        storage=storage,
        record_metadata=record_md,
    )


def test_dataset_previewer_is_package_owned() -> None:
    """SC-004: the dataset previewer is a PACKAGE-owned spec for SpectralDataset."""
    spec = _spec()
    assert spec.owner_kind is OwnerKind.PACKAGE
    assert spec.owner_name == "scistudio-blocks-spectroscopy"
    assert spec.target_type == "SpectralDataset"


def test_dataset_provider_builds_composite_envelope_with_index_table(tmp_path: Path) -> None:
    storage = _write_dataset(
        tmp_path,
        index_cols={"spectrum_id": ["a", "b"], "material": ["gold", "silver"], "prep": ["wet", "dry"]},
        spectra_cols={
            "spectrum_id": ["a", "a", "b", "b"],
            "lambda": [1.0, 2.0, 1.0, 2.0],
            "intensity": [10.0, 11.0, 20.0, 21.0],
        },
    )
    env = spectral_dataset_provider(
        _request(storage, {"slots": {"index": "DataFrame", "spectra": "DataFrame"}, "dataset_name": "demo"})
    )
    assert env.previewer_id == SPECTRAL_DATASET_PREVIEWER_ID
    assert env.kind is EnvelopeKind.COMPOSITE
    assert env.error is None
    assert env.payload["slots"] == {"index": "DataFrame", "spectra": "DataFrame"}
    assert env.payload["index_table"]["available"] is True
    assert env.payload["index_table"]["total_rows"] == 2
    assert env.payload["spectra_table"]["available"] is True
    assert env.payload["plot"]["overlay"]["series"]
    assert env.payload["plot"]["heatmap"]["aligned"] is True
    assert {"groupable_columns", "selected_ids", "plot_mode"} <= set(env.payload["controls"])


def test_dataset_provider_resolves_slots_via_composite_manifest(tmp_path: Path) -> None:
    # ADR-052 §8.5: the provider resolves slots through the sanctioned
    # composite_slot_ref against the core CompositeStore manifest — no path
    # reverse-engineering, no StorageReference construction.
    storage = _write_dataset(
        tmp_path,
        index_cols={"spectrum_id": ["a"], "material": ["gold"]},
        spectra_cols={"spectrum_id": ["a"], "lambda": [1.0], "intensity": [10.0]},
    )
    access = PreviewDataAccess()
    index_ref = access.composite_slot_ref(storage, "index")
    assert index_ref is not None
    assert index_ref.format == "parquet"
    assert index_ref.path.endswith("index/data.parquet")

    env = spectral_dataset_provider(_request(storage, {"slots": {"index": "DataFrame", "spectra": "DataFrame"}}))
    assert env.payload["index_table"]["available"] is True
    assert env.payload["index_table"]["rows"][0]["spectrum_id"] == "a"
    assert env.payload["spectra_table"]["available"] is True
    assert env.payload["plot"]["overlay"]["series"][0]["points"] == [{"x": 1.0, "y": 10.0}]


def test_dataset_previewer_filters_index_and_spectra_by_index_column(tmp_path: Path) -> None:
    storage = _write_dataset(
        tmp_path,
        index_cols={
            "spectrum_id": ["a", "b", "c"],
            "material": ["gold", "silver", "gold"],
            "prep": ["wet", "dry", "dry"],
        },
        spectra_cols={
            "spectrum_id": ["a", "a", "b", "b", "c", "c"],
            "lambda": [1.0, 2.0, 1.0, 2.0, 1.0, 2.0],
            "intensity": [10.0, 11.0, 20.0, 21.0, 30.0, 31.0],
        },
    )
    env = spectral_dataset_provider(
        _request(
            storage,
            {"slots": {"index": "DataFrame", "spectra": "DataFrame"}},
            extra_query={"filter_column": "material", "filter_value": "gold"},
        )
    )

    index_ids = [row["spectrum_id"] for row in env.payload["index_table"]["rows"]]
    spectra_ids = {row["spectrum_id"] for row in env.payload["spectra_table"]["rows"]}
    plot_ids = {series["spectrum_id"] for series in env.payload["plot"]["overlay"]["series"]}
    assert index_ids == ["a", "c"]
    assert spectra_ids == {"a", "c"}
    assert plot_ids == {"a", "c"}
    assert env.payload["index_table"]["filtered"] is True
    assert env.payload["index_table"]["unfiltered_total_rows"] == 3
    assert env.payload["controls"]["active_filters"] == [{"column": "material", "value": "gold", "op": "contains"}]


def test_dataset_previewer_supports_grouping_over_arbitrary_index_columns(tmp_path: Path) -> None:
    """SC-005: grouped plotting works over arbitrary index columns (material + prep)."""
    storage = _write_dataset(
        tmp_path,
        index_cols={"spectrum_id": ["a", "b"], "material": ["gold", "silver"], "prep": ["wet", "dry"]},
        spectra_cols={
            "spectrum_id": ["a", "b"],
            "lambda": [1.0, 1.0],
            "intensity": [10.0, 20.0],
        },
    )
    env = spectral_dataset_provider(
        _request(
            storage,
            {"slots": {"index": "DataFrame", "spectra": "DataFrame"}},
            extra_query={"group_by": "material", "color_by": "prep", "selected_ids": ["a"]},
        )
    )
    # Grouping is exposed as a capability + group-capable plot modes.
    assert "group" in env.payload["capabilities"]
    assert {"group_mean", "group_band"} <= set(env.payload["plot_modes"])
    # The arbitrary grouping columns are available in the index table.
    assert {"material", "prep"} <= set(env.payload["index_table"]["columns"])
    assert env.payload["controls"]["group_by"] == "material"
    assert env.payload["controls"]["color_by"] == "prep"
    assert env.payload["plot"]["selected"]["series"][0]["spectrum_id"] == "a"
    groups = {group["group"] for group in env.payload["plot"]["group_mean"]["groups"]}
    assert groups == {"gold", "silver"}


def test_dataset_previewer_export_controls_exist(tmp_path: Path) -> None:
    """SC-006: figure + visible-row + grouped-summary export controls exist."""
    storage = _write_dataset(
        tmp_path,
        index_cols={"spectrum_id": ["a"], "material": ["gold"]},
        spectra_cols={"spectrum_id": ["a"], "lambda": [1.0], "intensity": [10.0]},
    )
    env = spectral_dataset_provider(_request(storage, {"slots": {"index": "DataFrame", "spectra": "DataFrame"}}))
    resource_ids = {r.resource_id for r in env.resources}
    assert {"slot:index", "slot:spectra"} <= resource_ids
    assert {
        "export_figure_svg",
        "export_figure_png",
        "export_figure_pdf",
        "export_visible_spectra_csv",
        "export_selected_rows_csv",
        "export_grouped_summary_csv",
    } <= resource_ids


def test_dataset_diagnostics_grouped_health_columns() -> None:
    """SC-005: the pure diagnostics helper reports grouped per-issue health."""
    diag = compute_dataset_diagnostics(
        index_rows=[{"spectrum_id": "a"}, {"spectrum_id": "a"}, {"spectrum_id": "c"}],
        spectra_rows=[
            {"spectrum_id": "a", "lambda": 1.0, "intensity": 5.0},
            {"spectrum_id": "z", "lambda": 1.0, "intensity": 6.0},
        ],
    )
    codes = {issue["code"] for issue in diag["issues"]}
    assert "duplicate_ids" in codes
    assert "orphan_spectra" in codes
    assert "missing_spectra_coverage" in codes
    # Grouped counts are reported alongside the issue list.
    assert diag["counts"]["duplicate_ids"] >= 1
    assert diag["ok"] is False


def test_dataset_diagnostics_clean_when_consistent() -> None:
    diag = compute_dataset_diagnostics(
        index_rows=[{"spectrum_id": "a"}, {"spectrum_id": "b"}],
        spectra_rows=[
            {"spectrum_id": "a", "lambda": 1.0, "intensity": 2.0},
            {"spectrum_id": "b", "lambda": 1.0, "intensity": 3.0},
        ],
    )
    assert diag["ok"] is True
    assert diag["issues"] == []
    assert diag["heatmap_aligned"] is True


def test_dataset_diagnostics_detects_same_bounds_different_interior_grid() -> None:
    diag = compute_dataset_diagnostics(
        index_rows=[{"spectrum_id": "a"}, {"spectrum_id": "b"}],
        spectra_rows=[
            {"spectrum_id": "a", "lambda": 1.0, "intensity": 2.0},
            {"spectrum_id": "a", "lambda": 2.0, "intensity": 3.0},
            {"spectrum_id": "a", "lambda": 3.0, "intensity": 4.0},
            {"spectrum_id": "b", "lambda": 1.0, "intensity": 2.0},
            {"spectrum_id": "b", "lambda": 2.5, "intensity": 3.0},
            {"spectrum_id": "b", "lambda": 3.0, "intensity": 4.0},
        ],
    )
    assert diag["heatmap_aligned"] is False
    assert "heatmap_alignment" in {issue["code"] for issue in diag["issues"]}
