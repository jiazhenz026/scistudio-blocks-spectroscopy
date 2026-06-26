# Package Overview — scistudio-blocks-spectroscopy

The structured catalog required by `docs/DOCUMENTATION-STANDARD.md`. It must
stay in sync with the code: the blocks listed here match `get_blocks()` and the
`README.md` block table. Full per-block parameters live in each block's class
docstring.

## Purpose

General 1-D spectroscopy blocks for SciStudio — Raman, FTIR, UV-Vis,
fluorescence, and NIR. Implements spec `001-spectroscopy-package`
(`docs/specs/spectroscopy-package.md` in core).

## Scope and non-goals

- In scope: 1-D spectra and many-spectrum datasets, their IO, preprocessing,
  feature extraction, peak fitting, reference correction, library matching, and
  unmixing.
- Out of scope: SRS imaging and SRS spectral cubes (FR-002). This package never
  imports `scistudio_blocks_srs`.

## Data types

| Type | Core base | Represents | Key metadata |
| --- | --- | --- | --- |
| `Spectrum` | `Series` | One 1-D spectrum (`lambda` index, `intensity` value) | `lambda_unit`, `intensity_unit`, `lambda_kind`, `modality`, `spectrum_id`, `source_file` |
| `SpectralDataset` | `CompositeData` | Many spectra: an `index` table + a long-form `spectra` table | `dataset_role` (a library is a dataset with `dataset_role="library"`), `lambda_unit`, `intensity_unit`, `modality` |

Format support is not declared on the types (FR-131); it lives on the IO blocks
as ADR-043 `FormatCapability` records.

## Blocks (26)

| Group | Block | Operates on | Notes |
| --- | --- | --- | --- |
| utilities (9) | LoadSpectrum, SaveSpectrum, LoadSpectralDataset, SaveSpectralDataset, SpectrumToSpectralDataset, SpectralDatasetToSpectrum, FilterSpectralDataset, MergeSpectralDataset, AttachFeaturesToSpectralDataset | IO + `Spectrum`↔`SpectralDataset` conversion, dataset filter/merge, feature attach | — |
| preprocessing (7) | CropSpectrumRange, ShiftSpectralAxis, BaselineCorrection, SmoothSpectrum, AlignAndResampleSpectra, NormalizeSpectrum, SubtractPeakComponent | `Collection[Spectrum]` → `Collection[Spectrum]` | — |
| feature_extraction (5) | ExtractIntensity, CalculateAUC, CalculateCentroid, CalculateRatio, FindPeaks | `Collection[Spectrum]` → flat feature `DataFrame` keyed by `spectrum_id` | Merge back with AttachFeaturesToSpectralDataset |
| peak_fitting (1) | FitPeak | `Collection[Spectrum]` | — |
| reference_correction (2) | SubtractReferenceSpectrum, DivideByReferenceSpectrum | `Collection[Spectrum]` | — |
| library_matching (1) | MatchSpectralLibrary | `SpectralDataset` library | — |
| unmixing (1) | SpectralUnmixing | `Collection[Spectrum]` | — |

## IO / format support (ADR-043)

The four IO blocks declare explicit `FormatCapability` records (FR-128..FR-143).

- **Round-trippable and advertised:** delimited text `.txt`/`.csv`/`.tsv`,
  Excel `.xlsx`, package-native `.spectrum.json` (`Spectrum`), JSON manifest +
  Parquet sidecars (`SpectralDataset`), and JCAMP-DX `.jdx`/`.dx`/`.jcamp`
  (`Spectrum`).
- **Deferred and not advertised:** SPC (`.spc`) and vendor/instrument-native
  formats are intentionally not exposed through `FormatCapability` records and
  raise an informative `NotImplementedError` (`TODO(#1661)`).

## Previewers (ADR-048)

| Previewer | Targets | Capabilities |
| --- | --- | --- |
| `spectroscopy.spectrum.viewer` | `Spectrum` | plot, navigate, diagnostics, export |
| `spectroscopy.spectral_dataset.viewer` | `SpectralDataset` | table, filter, group, plot, diagnostics, export |

Both ship `previewers/assets/viewer.js` at `priority=100`, degrading to the core
series/composite renderers when the package is absent.

## Compatibility

- Requires `scistudio>=0.2.1a0`.
- Python `>=3.11`.
