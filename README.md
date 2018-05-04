# BI-geomorph-extraction
Author: Emily Sturdivant, U.S. Geological Survey | esturdivant@usgs.gov

## Overview
This package is used to calculate coastal geomorphology variables along shore-normal transects. The calculated variables are used as inputs for modeling geomorphology using a Bayesian Network (BN). The resulting input variables to the Geomorphology BN are described in the table below.

The package is a companion to a USGS methods report entitled "Evaluating barrier island characteristics and piping plover (Charadrius melodus) habitat availability along the U.S. Atlantic coast - geospatial approaches and methodology" (Zeigler and others, in review) and various USGS data releases that have been or will be published (e.g. Gutierrez and others, in review). For more detail, please refer to the report by Zeigler and others. 

| BN variable, point value (5 m)      | Format      | Definition                                                                                                                                                                                                                                     |
|-------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Beach Height (uBH)                  | continuous  | Vertical distance (m) between the mean high water (MHW) shoreline and foredune toe elevations. All points along the transect are assigned the same value.                                                                                      |
| Beach Width (uBW)                   | continuous  | Euclidean distance (m) between the MHW shoreline and the foredune toe or equivalent (either foredune crest or coastal armoring/development if the foredune toe was not delineated). All points along the transect are assigned the same value. |
| Construction (Construction)         | categorical | Presence of shoreline management structures along a transect. All points along the transect are assigned the same value.                                                                                                                       |
| Cross-Island Width (WidthLand)      | continuous  | Width (m) of the barrier island measured as a cross-section of the island along the transect. All points along the transect are assigned the same value.                                                                                       |
| Development (Development)           | categorical | Density of human development along a transect. All points along the transect are assigned the same value.                                                                                                                                      |
| Distance to Foredune Crest (DistDH) | continuous  | Euclidean distance (m) between the MHW shoreline and the foredune crest position. All points along the transect assigned the same value.                                                                                                       |
| Distance to Inlet (Dist2Inlet)      | continuous  | Alongshore distance (m) from the transect to the nearest tidal inlet. All points along the transect are assigned the same value.                                                                                                               |
| Distance to MHW (Dist_Seg)          | continuous  | Euclidean distance (m) between the point and the intersection of the transect with seaward MHW shoreline.                                                                                                                                      |
| Elevation (ptZmhw)                  | continuous  | Elevation (m; referenced to local MHW datum) at the 5 m grid cell containing the point.                                                                                                                                                        |
| Foredune Crest Height (DH_zmhw)     | continuous  | Elevation (m; referenced to local MHW datum) at the foredune crest nearest to the transect and no farther than 25 m. All points along the transect are assigned the same value.                                                                |
| Geomorphic Setting (GeoSet)         | categorical | Geomorphic setting (e.g., beach, dune) that best characterizes the landscape at that point. The value is assigned from the grid cell containing the point (see Piping Plover Habitat Bayesian Network below).                                  |
| Mean Transect Elevation (Mean_zMHW) | continuous  | Average elevation of the barrier along each transect. All points along the transect are assigned the same value.                                                                                                                               |
| Nourishment (Nourishment)           | categorical | Beach nourishment frequency at the transect. All points along the transect are assigned the same value.                                                                                                                                        |
| Shoreline Change Rate (LRR)         | continuous  | Historical rate of change in the shoreline position of that transect, represented by a linear regression rate. All points along the transect are assigned the same value.                                                                      |
| Substrate Type (SubType)            | categorical | Substrate type (for example, sand or mud/peat) that best characterizes the landscape at that point. The value is assigned from the grid cell containing the point (see Piping Plover Habitat Bayesian Network below).                          |
| Vegetation Density (VegDen)         | categorical | Vegetation density (for example, sparse or moderate) that best characterizes the landscape at that point. The value is assigned from the grid cell containing the point (see Piping Plover Habitat Bayesian network below).                    |
| Vegetation Type (VegType)           | categorical | Vegetation type (for example, herbaceous or shrub) that best characterizes the landscape at that point. The value is assigned from the grid cell containing the point (see Piping Plover Habitat Bayesian Network below).                      |

## Get started

### Required software
ArcGIS Pro (2.0 recommended), which includes an installation of Anaconda and Python 3. The default installation creates a conda environment, `arcgispro-py3` where you have access to the Python 3 version of ArcPy as well as the other ArcGIS Pro default Python programs. This installation of Anaconda is separate from any existing installations you may have.

### Installation
We recommend that you install this package in the ArcGIS Pro conda environment through pip. First, activate the arcgispro-py3 conda environment: `\ArcGIS\Pro\bin\Python\Scripts\proenv`. Then, install this package: `pip install git+https://github.com/esturdivant-usgs/BI-geomorph-extraction.git`

The Jupyter notebook files must be run within the ArcGIS Pro conda environment. To do so, type the following in your command prompt (assuming it has the default set-up and substituting path\to\dir with the location of the repository):

```
cd path\to\dir\BI-geomorph-extraction
\ArcGIS\Pro\bin\Python\Scripts\proenv
jupyter notebook
```

## How to implement:

1. Acquire all input datasets and save them into an Esri file geodatabase.
    - National Assessment of Shoreline Change (NASC) transect lines. Long-term shoreline change rates transect file from the NASC ([U.S. Geological Survey Open-File Report 2010-1119](https://pubs.usgs.gov/of/2010/1119/data_catalog.html "U.S. Geological Survey Open-File Report 2010-1119"))
    - Lidar-derived beach morphology points. These are published through the USGS National Assessment of Coastal Change Hazards [Beach Morphology (Dune Crest, Dune Toe, and Shoreline) for U.S. Sandy Coastlines] (https://coastal.er.usgs.gov/data-release/doi-F7GF0S0Z/). They need to be separated into shoreline, dune crest, and dune toe points. 
    - Digital elevation model (DEM). A good source for airborne lidar datasets is [NOAA's Digital Coast](https://coast.noaa.gov/dataviewer/). The lidar dataset should be the same as that used to derive the morphology points.
    - boundary polygon <- DEM + shoreline points + inlet lines (+ manual)
    - supplemented and sorted transects <- script + **manual**; Sorting is only semi-automated and tricky. See explanations below/in prepper.ipynb.
    - 'tidied' extended transects <- script + **manual**

2. Review values (mostly file paths) in setvars.py and update if needed.

3. QA/QC/cross-check everything thoroughly: projections, agreement, etc. Preferred projection is NAD83, Meters - Albers or UTM Zone 18N or 19N depending on region of Atlantic coast. Where projection is important, the script will reproject as necessary. You may need to create the following files: 
    - inlet lines <- DEM + **manual**
    - armoring lines <- ortho + **manual**

4. Run extractor.ipynb.

### Contents of this repository

- core: functions implemented in the notebooks.
- notebooks: prepper.ipynb and extractor.ipynb are used to perform the processing.
- sample_scratch: data frames in pickle format that were saved in the scratch directory during Fire Island extraction to potentially use for testing.
- temp: notebooks for sites that have already been run. These will probably be released with the datasets they were used to create and will be removed prior to publication.
- docs: files for use in the display of the package.
