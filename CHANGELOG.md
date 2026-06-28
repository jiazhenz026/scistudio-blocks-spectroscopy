# Changelog

All notable changes to this package are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

- OTA hot-update support (#1784): self-declared update source via
  `PackageInfo.ota` / `[tool.scistudio.ota]`; `scripts/ota_publish.py`
  publishes manifest + snapshot to the package's own `ota-<channel>`
  GitHub pre-release for the in-app Package Manager.

### Changed

- Previewer rewritten onto the ADR-052 §8 public previewer authoring API, so
  this package is the exemplary reference for package-owned previewers (#7).
  Behavior-preserving for users; internal storage wiring only:
  - reads storage via the typed `request.storage` / `request.record_metadata`
    instead of the `request.query["_storage"]` / `["_record_metadata"]` carrier;
  - resolves composite slots via the sanctioned
    `PreviewDataAccess.composite_slot_ref(request.storage, slot)` and drops the
    local `_slot_ref` / `_manifest_slot_path` / `_slot_file_candidate` /
    `_format_for_path` heuristics that reverse-engineered core's on-disk layout;
  - imports `sanitize_svg` from the public `scistudio.previewers.helpers`
    instead of the core-internal `scistudio.previewers.fallbacks`;
  - no longer imports `scistudio.core.storage.ref` or constructs a
    `StorageReference`; the type is referenced (annotations / pass-through) only
    via the public `scistudio.core.types` re-export.
  Requires core **`scistudio>=0.3.1a0`** (raised floor; alpha-inclusive, matching
  the current core line): the typed `request.storage`
  field landed in SciStudio #1829 (ADR-052 §8.5) and `composite_slot_ref` in
  SciStudio #1830 (ADR-052 §8.2). The OTA `[tool.scistudio.ota].min_core_base`
  is raised `0.2.1` → `0.3.1` to match, so core 0.2.x clients are not offered an
  update that calls APIs they lack. Tests now build composites via the core
  `CompositeStore` (real `manifest.json`), matching how a `SpectralDataset`
  actually persists.

### Added

- Package governance from `scistudio-package-template`: CI (lint, type, test,
  wheel build, SciStudio contract check), `AGENTS.md` + PR checklist,
  `CONTRIBUTING.md`, `docs/DOCUMENTATION-STANDARD.md`, `docs/package-overview.md`,
  `LICENSE` (MIT), and `scripts/validate_contract.py`.

### Fixed

- `previewers/providers.py`: narrow `dict`-or-`None` payload lookups so they
  are type-safe (no behavior change).
- `tests/test_packaging.py`: assert the actual `scistudio>=0.2.1a0` dependency
  floor (was a stale `scistudio>=0.2.1`).

## [0.1.0]

- Initial spectroscopy package: 26 blocks, 2 data types (`Spectrum`,
  `SpectralDataset`), 2 previewers.
