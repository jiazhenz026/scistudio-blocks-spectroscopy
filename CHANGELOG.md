# Changelog

All notable changes to this package are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

- OTA hot-update support (#1784): self-declared update source via
  `PackageInfo.ota` / `[tool.scistudio.ota]`; `scripts/ota_publish.py`
  publishes manifest + snapshot to the package's own `ota-<channel>`
  GitHub pre-release for the in-app Package Manager.

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
