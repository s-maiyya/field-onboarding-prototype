# Data in this prototype

`regions.json` holds a coarse district lookup grid (0.03°, about 3 km) and the main crops for each district. The app uses it to order the crop list for the plot's location and the current season. It is a static file with no backend.

## Sources and licences
- **Crop areas:** Area, Production and Yield (APY), Directorate of Economics and Statistics, Ministry of Agriculture and Farmers Welfare, via [India Data Portal](https://ckandev.indiadataportal.com/dataset/area-production-yield-apy). Open Data Commons Attribution License. Uses the average of 2020-21 to 2022-23 by district, crop and season, keeping the top 20 crops with at least 50 ha.
- **District boundaries:** [geoBoundaries](https://www.geoboundaries.org/) India ADM2 and ADM1 (2021). Open Data Commons Open Database License 1.0 (ODbL). The grid in `regions.json` is derived from it and is shared under ODbL.

## Known limits
- 709 of 735 districts are matched by state and name. The rest are mostly cities (Delhi, Mumbai, Kolkata, Hyderabad), small enclaves and new Manipur districts. They fall back to the default list.
- The recent APY years cover 56 field and plantation crops. Most fruit and vegetables (mango, onion in some states) are missing.
- At district borders the grid can pick the neighbouring district.

## Rebuild
`python3 tools/build_regions.py <data-dir> regions.json`, where `<data-dir>` holds `apy.csv` (the India Data Portal CSV) and `adm2.geojson` / `adm1.geojson` (geoBoundaries simplified files).
