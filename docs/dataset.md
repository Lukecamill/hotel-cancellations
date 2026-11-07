# Baseline dataset: source, identity and setup

Verified 7 November 2026. This completes Stage 3 Step 2 for the supplied baseline file. No training or data cleaning was performed.

## Source and attribution

Use [Jesse Mostipak’s Hotel booking demand dataset on Kaggle](https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand), handle `jessemostipak/hotel-booking-demand`, as specified by the task notebook. The notebook describes it as the TidyTuesday cleaning of the original authors’ data and declares CC BY 4.0. Kaggle’s page was reachable but did not expose readable metadata in this check, so its licence and numeric version were not independently confirmed from the page.

Attribute: Antonio, N., de Almeida, A., & Nunes, L. (2019). *Hotel booking demand datasets*. Data in Brief, 22, 41–49. https://doi.org/10.1016/j.dib.2018.11.126

The [original data article](https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/) confirms the Portuguese hotels, observation counts and arrival window, and displays a CC BY 4.0 licence notice. Its original two datasets have 31 variables each; this merged CSV has an additional hotel column. Preserve attribution and describe any later transformations when sharing derived outputs.

## Exact baseline identity

Machine-readable record: [dataset-manifest.json](evidence/dataset-manifest.json).

| Property | Verified value |
|---|---|
| Repository input | `data/raw/hotel_bookings/hotel_bookings.csv` |
| SHA-256 | `7c2ae42a7353905ea136e5c2287f17c92c5435826598bfbb8491c6f0c7b1fc06` |
| File size | 16,855,599 bytes |
| Rows / columns | 119,390 / 32 |
| City Hotel | 79,330 bookings |
| Resort Hotel | 40,060 bookings |
| Arrivals | 1 July 2015–31 August 2017 |

The repository file and supplied Downloads file are byte-identical. Reuse this existing input; a second download is unnecessary. The upstream numeric Kaggle version and original download date were not supplied. The checksum pins our exact baseline input without asserting that an unversioned future download is identical. Counts alone do not establish file identity or prove the notebook originally ran on these exact bytes; Step 3 will check reproduction.

## Obtain the input in a fresh checkout

1. Open the Kaggle dataset link above and download/extract `hotel_bookings.csv`, or obtain the same supplied baseline file separately.
2. Put it at `data/raw/hotel_bookings/hotel_bookings.csv` under the repository root. Create the directory if needed.
3. From the repository root, verify it on macOS:

```bash
shasum -a 256 data/raw/hotel_bookings/hotel_bookings.csv
```

Expected digest is in the identity table. If it differs, stop before claiming exact-file reproduction; inspect the difference and record its source/version. Do not silently replace the expected digest. A change in line endings can change the byte hash and requires explanation too.

The existing loader also supports KaggleHub when the local file is absent. This fallback uses an unversioned handle and therefore does not itself guarantee the pinned bytes; verify downloaded bytes against this manifest before baseline evaluation. Do not substitute the paper’s separate original files for the supplied merged CSV without documenting the conversion.

## Version-control check

`/data/` is excluded by the existing root `.gitignore`. `git check-ignore` confirmed both the raw CSV and processed Parquet path are ignored; `git ls-files data` returned no tracked files. Commit documentation and this manifest, not raw or processed datasets. No ignore-rule changes were needed.

## Provenance limitation relevant to later checks

The original article describes change-log extraction relative to the day before arrival, rather than a historical snapshot at initial booking. That supports caution about booking-time availability; it does not provide the event history needed to prove each feature was available at a seven-day decision horizon. Preserve the given method now and address historical reconstruction assumptions in Stage 4.
