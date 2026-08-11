# Catchment method

## Origin and drive-time windows

The routing origin is the verified public Google Maps listing for Vintage Optical at 605 S Main St, Morton, Illinois: latitude 40.6049094 and longitude -89.467024. This public map pin replaces any conflicting prior origin. The five Valhalla contours use the auto profile at 5, 10, 15, 20, and 30 minutes. Input and snapped location markers are excluded. The routes are modeled and have no live traffic. No contour geometry required repair.

## Area allocation

The calculation uses an area-weighted block-group intersection. Illinois 2024 TIGER block groups are limited to county FIPS 107, 113, 143, 179, and 203, the five counties touched by the 30-minute contour. Block-group and isochrone geometry is projected to EPSG:5070 before area is measured.

For every block group that overlaps a window, the script divides intersection area by the full block-group area. It multiplies additive 2024 ACS 5-year estimates by that fraction. This partial-block allocation assumes the measured population characteristic is evenly distributed inside each block group. It is more precise than assigning a whole block group by centroid, but it does not reveal where people actually live inside the block group.

## ACS measures and uncertainty

Population, children under 18, ages 40 to 64, ages 65 plus, and households use the specified 2024 ACS 5-year estimate cells. Negative ACS sentinel estimates are null, never zero. ACS values are survey estimates with sampling error. Area allocation adds another approximation, and the data vintage does not describe changes after the 2020 through 2024 ACS collection period.

The income context is a household-weighted mean of valid block-group median household incomes. Blocks with missing or invalid median income or missing households are excluded. This is an approximation, not a true median for the catchment.

## Diabetes context

TIGER block groups are dissolved to Census tracts and joined by tract GEOID to CDC PLACES. For each window, the 2023 crude diabetes prevalence from the CDC PLACES 2025 release is weighted by adult population and the fraction of tract area inside the isochrone. The result is modeled public-health context, not a patient measure.

## Interpretation limits

This is not a patient-origin model. It has no patient addresses, visit histories, referral flows, or observed travel patterns. It describes public aggregate context inside modeled drive-time windows.

Full VDU remains null because there is no direct national comparator receipt for `diabetes_prevalence_indexed_population` and no supported receipt for `commercial_pay_indexed_population`. The four-term value is labeled `partial_diagnostic_not_canonical_vdu`. It is only a partial diagnostic. It is not full VDU and is not promoted into any score.
