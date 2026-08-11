# Run summary

## Five-window outputs

Values below are rounded display values. Raw floating-point values remain in `catchment_demographics.json`.

| Minutes | Population | Households | Under 18 | Ages 40-64 | Ages 65+ | Approx. income context | Diabetes crude | BGs | Tracts | Partial diagnostic |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 6,624 | 2,722 | 1,712 | 1,811 | 1,311 | $93,888 | 9.6% | 12 | 5 | 8,553 |
| 10 | 19,322 | 7,873 | 4,571 | 5,843 | 4,291 | $93,730 | 10.9% | 30 | 14 | 25,250 |
| 15 | 54,768 | 23,793 | 11,707 | 17,431 | 10,939 | $76,519 | 12.4% | 89 | 42 | 70,658 |
| 20 | 173,058 | 75,244 | 38,652 | 53,102 | 32,473 | $68,303 | 13.2% | 193 | 72 | 222,001 |
| 30 | 283,661 | 120,940 | 64,831 | 86,558 | 53,258 | $77,711 | 12.3% | 255 | 90 | 364,275 |

The income context is an approximation, not a true catchment median. The partial diagnostic is not canonical VDU.

## Growth evidence

Census PEP Vintage 2025 Morton village annual estimates:

- 2020: 17,172
- 2021: 17,196
- 2022: 17,361
- 2023: 17,552
- 2024: 17,555
- 2025: 17,565

- 2020 to 2025: +393 people, 2.29%
- 2024 to 2025: +10 people, 0.06%

Morton CUSD 709 first-party enrollment:

- 2022-2023: 3,238
- 2024-25: 3,299
- 2025-26: 3,365
- 2022-2023 to 2025-26: +127 students, 3.92%
- 2024-25 to 2025-26: +66 students, 2.00%

No 2023-24 value was interpolated. These figures describe observed public change only.

## Sources

Source IDs used: `GOOGLE_MAPS_SAMPLE_20260730`, `VALHALLA_20260730`, `TIGER2024_BG`, `ACS2024_BG`, `CDC_PLACES_2025`, `CENSUS_PEP_2025`, and `MORTON709_FIRST_PARTY_ARCHIVE`.

## Checks run

- Direct Google Maps origin matched latitude 40.6049094 and longitude -89.467024.
- Valhalla marker features were excluded and exactly five polygon contours remained.
- TIGER to ACS joins used exact block-group GEOIDs in the five required counties.
- Geometry areas and intersections used EPSG:5070.
- District parsed values and stored HTML receipt hashes matched.
- The canonical validator printed PASS for this packet.
- Two consecutive build runs produced identical JSON and GeoJSON SHA-256 checksums.

Deterministic output checksums:

- `catchment_demographics.json`: `5ba62163d5f3cd1316c8f9b39ab27818e1ec208d277dd05210f1453d2f55885f`
- `catchment_windows.geojson`: `7f733dbece1a217e2a45854731eb823754b0abd7069c3eb2760ee5e6b2b57368`
- `growth_evidence.json`: `76c9ce4068b42c10a127132e2a2a0753d46249aaca227025d7e2969b06d2d4d8`
- `source_receipts.json`: `7322f85abc7581e953a04c0cfb34d4f1974701ce9b69e1d926b0c5d77aab83fd`

No score, report, external system, or delivery was changed.
