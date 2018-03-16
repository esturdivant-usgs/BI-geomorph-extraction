# BI-geomorph-extraction
Author: Emily Sturdivant, U.S. Geological Survey | esturdivant@usgs.gov

## Overview
This package is used to calculate coastal geomorphology variables along shore-normal transects. It produces inputs for modeling geomorphology using a Bayesian Network and is a companion to a USGS report titled "Evaluating barrier island characteristics and piping plover (Charadrius melodus) habitat availability along the U.S. Atlantic coast - geospatial approaches and methodology" (Zeigler and others, in review) and various USGS data releases that have been or will be published (e.g. Gutierrez and others, in review). For more detail, please refer to the report by Zeigler and others. 

## Get started

### Required software
ArcGIS Pro (2.0 recommended), which includes an installation of Anaconda and Python 3. The default installation creates a conda environment, `arcgispro-py3` where you have access to the python 3 version of arcpy as well as the other ArcGIS Pro default Python programs. This installation of Anaconda is separate from any existing installations you may have.

### Installation
We recommend that you install this package in the ArcGIS Pro conda environment through pip. First, activate the arcgispro-py3 conda environment: `\ArcGIS\Pro\bin\Python\Scripts\proenv`. Then, install this package: `pip install git+https://github.com/esturdivant-usgs/BI-geomorph-extraction.git`

The Jupyter notebook files must be run within the ArcGIS Pro conda environment. To do so, type the following in your command prompt (assuming it has the default set-up and substituting path\to\dir with the location of the repository):

```
cd path\to\dir\BI-geomorph-extraction
\ArcGIS\Pro\bin\Python\Scripts\proenv
jupyter notebook
```

## How to implement:

1. Acquire all input feature classes - refer to input variables in addition to the list below.
    - Long-term shoreline change rates transect file from the National Assessment of Shoreline Change ([U.S. Geological Survey Open-File Report 2010-1119](https://pubs.usgs.gov/of/2010/1119/data_catalog.html "U.S. Geological Survey Open-File Report 2010-1119"))
    - DH points
    - DL points
    - shoreline points
    - DEM

2. Review values (mostly file paths) in setvars.py and update if needed.

3. Interactively run prepper.ipynb from the ArcGIS Pro to make some those input files that require creation or modification. There are steps in the process that must be completed manually. Notes in the script describe the procedure for creating them.
    - inlet lines <- DEM + **manual**
    - armoring lines <- ortho + **manual**
    - boundary polygon <- DEM + shoreline points + inlet lines (+ manual)
    - oceanside MHW shore between inlets <- boundary polygon + inlets
    - supplemented and sorted transects <- script + **manual**; Sorting is only semi-automated and tricky. See explanations below/in prepper.ipynb.
    - 'tidied' extended transects <- script + **manual**

4. QA/QC/cross-check everything thoroughly: projections, agreement, etc. Preferred projection is NAD83, Meters - Albers or UTM Zone 18N or 19N depending on region of Atlantic coast.

5. Run extractor.ipynb.

### Contents of this repository

- core: functions implemented in the notebooks.
- notebooks: prepper.ipynb and extractor.ipynb are used to perform the processing.
- sample_scratch: data frames in pickle format that were saved in the scratch directory during Fire Island extraction to potentially use for testing.
- temp: notebooks for sites that have already been run. These will probably be released with the datasets they were used to create and will be removed prior to publication.
