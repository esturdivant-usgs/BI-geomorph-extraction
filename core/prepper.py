
'''
OUTDATED. Operation now takes place in prepper.ipynb

Preprocessing for extracting barrier island metrics along transects
Requires: python 3, ArcPy
Author: Emily Sturdivant
email: esturdivant@usgs.gov

Notes:
    Run in ArcMap python window;

'''
import os
import sys
import time
import shutil
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import arcpy
import functions_warcpy as fwa
from setvars import *

"""
Dunes and armoring
"""
#%% DUNE POINTS
# Replace fill values with Null # Check the points for irregularities
fwa.ReplaceValueInFC(dhPts, oldvalue=fill, newvalue=None, fields=["dhigh_z"])
fwa.ReplaceValueInFC(dlPts, oldvalue=fill, newvalue=None, fields=["dlow_z"])
fwa.ReplaceValueInFC(ShorelinePts, oldvalue=fill, newvalue=None, fields=["slope"])

#%% ARMORING LINES
arcpy.CreateFeatureclass_management(home, armorLines, 'POLYLINE', spatial_reference=utmSR)
print("{} created. Now we'll stop for you to manually digitize the shorefront armoring based on the orthoimage.".format(armorLines))
exit()
#%% Resume after manual editing.

"""
Inlets
"""
#%% INLETS
# manually create lines based on the boundary polygon that correspond to end of land and cross the MHW line
arcpy.CreateFeatureclass_management(home, inletLines, 'POLYLINE', spatial_reference=utmSR)
print("{} created. Now we'll stop for you to manually create lines at each inlet.".format(inletLines))
exit()
#%% Resume after manual editing.

"""
Shoreline
"""
#%% BOUNDARY POLYGON
# Inlet lines must intersect MHW
bndpoly = fwa.DEMtoFullShorelinePoly(elevGrid_5m, MTL, MHW, inletLines, ShorelinePts)
# Eliminate any remnant polygons on oceanside
print('Select features from {} that should not be included in {}'.format(bndpoly, barrierBoundary))
exit()
#%% Resume after manual selection
arcpy.DeleteFeatures_management(bndpoly)

#%% SHORELINE
barrierBoundary = fwa.NewBNDpoly(bndpoly, ShorelinePts, barrierBoundary, '25 METERS', '50 METERS')
shoreline = fwa.CreateShoreBetweenInlets(barrierBoundary, inletLines, shoreline, ShorelinePts, proj_code)

"""
Transects
"""
#%% TRANSECTS - extendedTrans
# Create extendedTrans, LT transects with gaps filled and lines extended
# set parameters for sorting. multi_sort should be true if the
multi_sort = True # True indicates that the transects must be sorted in batches to preserve order
sort_corner = 'LL'

#%% Temp filenames
trans_presort = os.path.join(arcpy.env.scratchGDB, 'trans_presort_temp')
trans_extended = os.path.join(arcpy.env.scratchGDB, 'trans_ext_temp')
trans_sort_1 = os.path.join(arcpy.env.scratchGDB, 'trans_sort_temp')
trans_x = os.path.join(arcpy.env.scratchGDB, 'overlap_points_temp')
overlapTrans_lines = os.path.join(arcpy.env.scratchGDB, 'overlapTrans_lines_temp')
sort_lines =  os.path.join(arcpy.env.scratchGDB, 'sort_lines')

#%% 1. Extend and Copy only the geometry of transects to use as material for filling gaps
fwa.ExtendLine(fc=orig_trans, new_fc=trans_extended, distance=extendlength, proj_code=proj_code)
fwa.CopyAndWipeFC(trans_extended, trans_presort, ['sort_ID'])
print("MANUALLY: use groups of existing transects in new FC '{}' to fill gaps. Avoid overlapping transects as much as possible".format(trans_presort))
exit()
#%% Resume after manual editing.

#%% 2. automatically sort.
fwa.PrepTransects_part2(trans_presort, trans_extended, barrierBoundary)
# Create lines to use to sort new transects
if multi_sort:
    sort_lines = 'sort_lines'
    arcpy.CreateFeatureclass_management(trans_dir, sort_lines, "POLYLINE", spatial_reference=utmSR)
    print("MANUALLY: Add features to sort_lines.")
    exit()
    #%% Resume after manual editing...
else:
    sort_lines = []
#%% Possibly resume after manual editing...
fwa.SortTransectsFromSortLines(trans_presort, extendedTrans, sort_lines, sortfield=tID_fld, sort_corner=sort_corner)
# # Clean up OBJECTID
# if len(arcpy.ListFields(extendedTrans, 'OBJECTID*')) == 2:
#     fwa.ReplaceFields(extendedTrans, {'OBJECTID': 'OID@'})

#%% TRANSECTS - tidyTrans
print("Manual work seems necessary to remove transect overlap")
print("Select the boundary lines between groups of overlapping transects")
# Select the boundary lines between groups of overlapping transects
exit()
#%% Resume after manual selection
# Copy only the selected lines
arcpy.CopyFeatures_management(orig_extTrans, overlapTrans_lines)
arcpy.SelectLayerByAttribute_management(orig_extTrans, "CLEAR_SELECTION")
# Split transects at the lines of overlap.
arcpy.Intersect_analysis([orig_extTrans, overlapTrans_lines], trans_x,
                         'ALL', output_type="POINT")
arcpy.SplitLineAtPoint_management(orig_extTrans, trans_x, extTrans_tidy)
print("MANUALLY: Select transect segments to be deleted. ")
exit()
#%% Resume after manual selection

arcpy.DeleteFeatures_management(extTrans_tidy)

print("Pre-processing completed.")
