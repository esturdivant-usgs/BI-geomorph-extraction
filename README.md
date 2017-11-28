# BI-geomorph-extraction
Extract barrier island metrics along transects for Bayesian Network Deep Dive

Requires: python 3, ArcPy

Author: Emily Sturdivant
email: esturdivant@usgs.gov; bgutierrez@usgs.gov

## How to run:

1. Acquire all input feature classes - refer to input variables in addition to the list below. 
    - transect lines
    - DH points
    - DL points
    - shoreline points
    - DEM
    
2. Update values in setvars.py.

3. Interactively run prepper.py in the Python console in ArcGIS Pro to make some of the input files. There are steps in the process that must be completed manually. Notes in the script describe the procedure for creating them. 
    - inlet lines <- DEM + **manual**
    - armoring lines <- ortho + **manual**
    - boundary polygon <- DEM + shoreline points + inlet lines (+ manual)
    - oceanside MHW shore between inlets <- boundary polygon + inlets 
    - supplemented and sorted transects <- script + **manual**; Sorting is only semi-automated and tricky. See explanations below/in prepper.ipynb.
    - 'tidied' extended transects <- script + **manual**

4. QA/QC/cross-check everything thoroughly: projections, agreement, etc. Preferred projection is NAD83, Meters - Albers or UTM Zone 18N or 19N depending on region of Atlantic coast.

5. Run extractor.ipynb.

## Notes about using ArcPy

Jupyter notebook files must be run within the ArcGIS Pro conda environment. To do so, type the following in your command prompt (assuming it has the default set-up and substituting path\to\dir with the location of the repository):

```
cd path\to\dir\BI-geomorph-extraction
\ArcGIS\Pro\bin\Python\Scripts\proenv
jupyter notebook
```
