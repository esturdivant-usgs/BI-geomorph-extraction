
'''
Preprocessing for extracting barrier island metrics along transects
Requires: python 2.7, Arcpy
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
import pythonaddins
# path to TransectExtraction module
script_path = r"\\Mac\Home\GitHub\plover_transect_extraction\TransectExtraction"
sys.path.append(script_path) # path to TransectExtraction module
import functions_warcpy as fwa
from setvars import *

start = time.clock()

"""
Pre-processing
"""
#%% DUNE POINTS
# Replace fill values with Null # Check the points for irregularities
fwa.ReplaceValueInFC(dhPts, oldvalue=fill, newvalue=None, fields=["dhigh_z"])
fwa.ReplaceValueInFC(dlPts, oldvalue=fill, newvalue=None, fields=["dlow_z"])
fwa.ReplaceValueInFC(ShorelinePts, oldvalue=fill, newvalue=None, fields=["slope"])

#%% ARMORING LINES
arcpy.CreateFeatureclass_management(home, armorLines, 'POLYLINE', spatial_reference=utmSR)
print("{} created. Now we'll stop for you to manually create lines at each inlet.".format(armorLines))
exit()
#%% Resume after manual editing.

#%% INLETS
# manually create lines based on the boundary polygon that correspond to end of land and cross the MHW line
arcpy.CreateFeatureclass_management(home, inletLines, 'POLYLINE', spatial_reference=utmSR)
print("{} created. Now we'll stop for you to manually create lines at each inlet.".format(inletLines))
exit()
#%% Resume after manual editing.

#%% BOUNDARY POLYGON
# Inlet lines must intersect MHW
bndpoly = fwa.DEMtoFullShorelinePoly(elevGrid_5m, '{site}{year}'.format(**SiteYear_strings), MTL, MHW, inletLines, ShorelinePts)
# Eliminate any remnant polygons on oceanside
print('Select features from {} that should not be included in {}'.format(bndpoly, barrierBoundary))
exit()
#%% Resume after manual selection
arcpy.DeleteFeatures_management(bndpoly)
barrierBoundary = fwa.NewBNDpoly(bndpoly, ShorelinePts, barrierBoundary, '25 METERS', '50 METERS')

#%% SHORELINE
shoreline = fwa.CreateShoreBetweenInlets(barrierBoundary, inletLines, shoreline, ShorelinePts, proj_code)

#%% TRANSECTS - extendedTrans
# Copy transects from archive directory
"""
~~ start transect work
"""
# if transects already exist, but without correct field ID, use DuplicateField()
# DuplicateField(extendedTransects, 'TransOrder', tID_fld)
# arcpy.FeatureClassToFeatureClass_conversion(extendedTransects, trans_dir, os.path.basename(orig_extTrans))
# DeleteExtraFields(orig_extTrans, [tID_fld])
# arcpy.FeatureClassToFeatureClass_conversion(orig_extTrans, trans_dir, os.path.basename(orig_tidytrans))

# Create extendedTrans, LT transects with gaps filled and lines extended
multi_sort = True # True indicates that the transects must be sorted in batches to preserve order
sort_corner = 'LL'

trans_presort = 'trans_presort_temp'
LTextended = 'LTextended'
trans_sort_1 = 'trans_sort_temp'
trans_x = 'overlap_points_temp'
overlapTrans_lines = 'overlapTrans_lines_temp'

arcpy.env.workspace = trans_dir
#%% 1. Extend and Copy only the geometry of transects to use as material for filling gaps
fwa.ExtendLine(fc=orig_trans, new_fc=LTextended, distance=extendlength, proj_code=proj_code)
fwa.CopyAndWipeFC(LTextended, trans_presort, ['sort_ID'])
print("MANUALLY: use groups of existing transects in new FC '{}' to fill gaps. Avoid overlapping transects as much as possible".format(trans_presort))
exit()
#%% Resume after manual editing.

#%% 2. automatically sort.
fwa.PrepTransects_part2(trans_presort, LTextended, barrierBoundary)
# Create lines to use to sort new transects
if multi_sort:
    sort_lines = 'sort_lines'
    arcpy.CreateFeatureclass_management(trans_dir, sort_lines, "POLYLINE", spatial_reference=arcpy.SpatialReference(proj_code))
    print("MANUALLY: Add features to sort_lines.")
    exit()
    #%% Resume after manual editing...
else:
    sort_lines = []
#%% Possibly resume after manual editing...
fwa.SortTransectsFromSortLines(trans_presort, extendedTrans, sort_lines, sortfield=tID_fld, sort_corner=sort_corner)

if len(arcpy.ListFields(extendedTrans, 'OBJECTID*')) == 2:
    fwa.ReplaceFields(extendedTrans, {'OBJECTID': 'OID@'})

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
arcpy.SplitLineAtPoint_management(orig_extTrans, trans_x, orig_tidytrans)
print("MANUALLY: Select transect segments to be deleted. ")
exit()
#%% Resume after manual selection

arcpy.DeleteFeatures_management(orig_tidytrans)

"""
~~ end transect work
"""

print("Pre-processing completed.")

DeleteTempFiles()
