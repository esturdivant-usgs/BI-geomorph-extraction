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
    - supplemented and sorted transects <- script + **manual**
    - 'tidied' extended transects <- script + **manual**
    
* Sorting can be tricky. I'll need to provide lots of explanation for this step. #TODO

4. QA/QC/cross-check everything thoroughly: projections, agreement, etc. Preferred projection is NAD83, Meters - Albers or UTM Zone 18N or 19N depending on region of Atlantic coast.

5. Run extractor.py.

## Notes about using ArcPy
