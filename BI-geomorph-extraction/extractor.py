# -*- coding: utf-8 -*-
#! python3
'''
BI-geomorph-extraction
Extract barrier island metrics along transects for Bayesian Network Deep Dive
Requires: python 3, ArcPy
Author: Emily Sturdivant
email: esturdivant@usgs.gov; bgutierrez@usgs.gov

Notes:
    Run in ArcGIS Pro python 3 environment;
    Spatial reference used is NAD 83 UTM 19N: arcpy.SpatialReference(26918)
'''
import os
import sys
import time
import shutil
import pandas as pd
import numpy as np
# path to TransectExtraction module
if sys.platform == 'win32':
    script_path = r"\\Mac\Home\GitHub\plover_transect_extraction\TransectExtraction"
    sys.path.append(script_path) # path to TransectExtraction module
    import arcpy
    # import pythonaddins
    import functions_warcpy as fwa
if sys.platform == 'darwin':
    script_path = '/Users/esturdivant/GitHub/plover_transect_extraction/TransectExtraction'
    sys.path.append(script_path)
from setvars import *
import functions as fun

# import pkg_resources
# pkg_resources.get_distribution("pandas").version

#%% ####### Run ###############################################################
start = time.clock()
"""
SPATIAL: transects
"""
#%% extendedTransects
if not arcpy.Exists(shoreline):
    if not arcpy.Exists(barrierBoundary):
        barrierBoundary = fwa.NewBNDpoly(bndpoly, ShorelinePts, barrierBoundary, '25 METERS', '50 METERS')
    fwa.CreateShoreBetweenInlets(barrierBoundary, inletLines, shoreline, ShorelinePts, proj_code)
if not arcpy.Exists(extendedTransects):
    arcpy.FeatureClassToFeatureClass_conversion(orig_extTrans, home, extendedTransects)

#%% Create trans_df
trans_df = fwa.FCtoDF(extendedTransects, id_fld=tID_fld, extra_fields=extra_fields)
trans_df.drop(extra_fields, axis=1, inplace=True, errors='ignore')
if not os.path.exists(scratch_dir):
    os.makedirs(scratch_dir)
trans_df.to_pickle(os.path.join(scratch_dir, 'trans_df.pkl'))

#%% Add XY and Z/slope from DH, DL, SL points within 10m of transects
sl2trans_df = fwa.add_shorelinePts2Trans(extendedTransects, ShorelinePts, shoreline, tID_fld, proximity=pt2trans_disttolerance)
sl2trans_df.to_pickle(os.path.join(scratch_dir, 'sl2trans.pkl'))
fwa.DFtoFC(sl2trans_df, 'pts2trans_SL', spatial_ref=utmSR, id_fld=tID_fld, xy=["SL_x", "SL_y"], keep_fields=['Bslope'])

dh2trans_df = fwa.find_ClosestPt2Trans_snap(extendedTransects, dhPts, trans_df, 'DH', tID_fld, proximity=pt2trans_disttolerance)
dh2trans_df.to_pickle(os.path.join(scratch_dir, 'dh2trans.pkl'))
fwa.DFtoFC(dh2trans_df, 'ptSnap2trans_DH', spatial_ref=utmSR, id_fld=tID_fld, xy=["DH_snapX", "DH_snapY"], keep_fields=['DH_z'])

dl2trans_df = fwa.find_ClosestPt2Trans_snap(extendedTransects, dlPts, trans_df, 'DL', tID_fld, proximity=pt2trans_disttolerance)
dl2trans_df.to_pickle(os.path.join(scratch_dir, 'dl2trans.pkl'))
fwa.DFtoFC(dl2trans_df, 'ptSnap2trans_DL', spatial_ref=utmSR, id_fld=tID_fld, xy=["DL_snapX", "DL_snapY"], keep_fields=['DL_z'])

arm2trans_df = fwa.ArmorLineToTrans_PD(extendedTransects, armorLines, sl2trans_df, tID_fld, proj_code, elevGrid_5m)
arm2trans_df.to_pickle(os.path.join(scratch_dir, 'arm2trans.pkl'))

#%% Add all the positions to the trans_df
trans_df = fun.join_columns_id_check(trans_df, sl2trans_df, tID_fld)
trans_df = fun.join_columns_id_check(trans_df, dh2trans_df, tID_fld)
trans_df = fun.join_columns_id_check(trans_df, dl2trans_df, tID_fld)
trans_df = fun.join_columns_id_check(trans_df, arm2trans_df, tID_fld)
# trans_df.to_pickle(os.path.join(scratch_dir, 'trans_df_beachmetrics.pkl'))

#%% Calculate distances from shore to dunes, etc.
trans_df, dl2trans, dh2trans, arm2trans = fwa.calc_BeachWidth_fill(extendedTransects, trans_df, maxDH, tID_fld, MHW, fill)

#%% Don't require trans_df
# Dist2Inlet: Calc dist from inlets SPATIAL
dist_df = fwa.measure_Dist2Inlet(shoreline, extendedTransects, inletLines, tID_fld)
# dist_df.to_pickle(os.path.join(scratch_dir, 'dist2inlet_df.pkl'))
trans_df = fun.join_columns_id_check(trans_df, dist_df, tID_fld, fill=fill)

# Clip transects, get barrier widths *SPATIAL*
widths_df = fwa.calc_IslandWidths(extendedTransects, barrierBoundary, tID_fld=tID_fld)
trans_df = fun.join_columns_id_check(trans_df, widths_df, tID_fld, fill=fill)
trans_df.to_pickle(os.path.join(scratch_dir, extTrans_null+'_prePts.pkl'))
# trans_df = pd.read_pickle(os.path.join(scratch_dir, extTrans_null+'_prePts.pkl'))

"""
5m Points
"""
#%%
# if os.path.exists(os.path.join(scratch_dir, transPts_null+'.pkl')):
#     pts_df = pd.read_pickle(os.path.join(scratch_dir,transPts_null+'.pkl'))
#     trans_df = pd.read_pickle(os.path.join(scratch_dir, extTrans_null+'_prePts.pkl'))
if not arcpy.Exists(transPts_presort):
    pts_df, transPts_presort = fwa.TransectsToPointsDF(extTrans_tidy, barrierBoundary, fc_out=transPts_presort) # 4 minutes for FireIsland

if not 'ptZ' in pts_df.columns:
    # Extract elevation and slope at points
    if not arcpy.Exists(elevGrid_5m):
        fwa.ProcessDEM(elevGrid, elevGrid_5m, utmSR)
    if not arcpy.Exists(slopeGrid):
        arcpy.Slope_3d(elevGrid_5m, slopeGrid, 'PERCENT_RISE')
    arcpy.sa.ExtractMultiValuesToPoints(transPts_presort, [[elevGrid_5m, 'ptZ'], [slopeGrid, 'ptSlp']]) # 9 min for ParkerRiver
    pts_df = fwa.FCtoDF(transPts_presort, xy=True, dffields=[tID_fld,'ptZ', 'ptSlp'])
    pts_df.to_pickle(os.path.join(scratch_dir, 'pts_df_elev_slope.pkl'))
# pts_df = pd.read_pickle(os.path.join(scratch_dir, 'pts_df_elev_slope.pkl'))

#%%
# Calculate DistSeg, Dist_MHWbay, DistSegDH, DistSegDL, DistSegArm, sort points
pts_df = fun.join_columns(pts_df, trans_df, tID_fld)
pts_df = fun.prep_points(pts_df, tID_fld, pID_fld, MHW, fill)
# Aggregate ptZmhw to max and mean and join to transPts and extendedTransects
pts_df, zmhw = fun.aggregate_z(pts_df, MHW, tID_fld, 'ptZ', fill)
trans_df = fun.join_columns(trans_df, zmhw) # join new fields to transects
pts_df = fun.join_columns(pts_df, trans_df, tID_fld) # Join transect values to pts

# Housecleaning
trans_df.drop(extra_fields, axis=1, inplace=True, errors='ignore') # Drop extra fields
pts_df.drop(extra_fields, axis=1, inplace=True, errors='ignore') # Drop extra fields

#%% Save dataframes to open elsewhere or later
trans_df.to_pickle(os.path.join(scratch_dir, extTrans_null+'.pkl'))
pts_df.to_pickle(os.path.join(scratch_dir, transPts_null+'.pkl'))
# pts_df = pd.read_pickle(os.path.join(scratch_dir, transPts_null+'.pkl'))
# trans_df = pd.read_pickle(os.path.join(scratch_dir, extTrans_null+'.pkl'))

"""
Outputs
"""
#%% Join calculated transect values to the transect FC.
trans_fc = fwa.JoinDFtoFC(trans_df, extendedTransects, tID_fld, out_fc=extTrans_fill)
# DeleteExtraFields(trans_fc, trans_flds)
fwa.CopyFCandReplaceValues(trans_fc, fill, None, out_fc=extTrans_null, out_dir=home)
# Save final SHP with fill values
arcpy.FeatureClassToFeatureClass_conversion(trans_fc, scratch_dir, extTrans_shp+'.shp')

#%% Save final pts with fill values as CSV
if not pID_fld in pts_df.columns:
    pts_df.reset_index(drop=False, inplace=True)
csv_fname = os.path.join(scratch_dir, transPts_fill +'.csv')
pts_df.to_csv(os.path.join(scratch_dir, transPts_fill +'.csv'), na_rep=fill, index=False)
print("OUTPUT: {}".format(csv_fname))

#%% Create Beach Width raster by joining DF to ID raster
if not arcpy.Exists(rst_transIDpath):
    outEucAll = arcpy.sa.EucAllocation(orig_tidytrans, maximum_distance=50, cell_size=cell_size, source_field=tID_fld)
    outEucAll.save(os.path.basename(rst_transIDpath))
out_rst = fwa.JoinDFtoRaster(trans_df, rst_transID, bw_rst, fill, tID_fld, 'uBW')

#%% Convert pts_df to FC, both pts and trans (pts_fc, trans_fc)
pts_fc = fwa.DFtoFC_large(pts_df, out_fc=os.path.join(arcpy.env.workspace, transPts_fill), spatial_ref=utmSR, df_id=pID_fld, xy=["seg_x", "seg_y"])
# DeleteExtraFields(pts_fc, pt_flds+trans_flds)
# Save final FCs with null values, final SHP and XLS with fill values
fwa.CopyFCandReplaceValues(pts_fc, fill, None, out_fc=transPts_null, out_dir=home)
arcpy.FeatureClassToFeatureClass_conversion(pts_fc, scratch_dir, transPts_shp+'.shp')
try:
    xls_fname = os.path.join(scratch_dir, transPts_fill +'.xlsx')
    pts_df.to_excel(xls_fname, na_rep=fill, index=False)
    print("OUTPUT: {}".format(xls_fname))
except:
    print("No Excel file created. You'll have to do it yourself from the CSV.")

#%% Export the files used to run the process to code file in home dir
try:
    os.makedirs(code_dir)
except OSError:
    if not os.path.isdir(code_dir):
        raise
shutil.copy(os.path.join(script_path, 'TE_execute.py'), os.path.join(code_dir, 'TE_execute.py'))
shutil.copy(os.path.join(script_path, 'TE_config.py'), os.path.join(code_dir, 'TE_config.py'))
shutil.copy(os.path.join(script_path, 'TE_functions.py'), os.path.join(code_dir, 'TE_functions.py'))
shutil.copy(os.path.join(script_path, 'TE_functions_arcpy.py'), os.path.join(code_dir, 'TE_functions_arcpy.py'))

"""
Metadata
"""
pts_df = pd.read_pickle(os.path.join(scratch_dir, transPts_null+'.pkl'))
trans_df = pd.read_pickle(os.path.join(scratch_dir, extTrans_null+'.pkl'))

len(pts_df)
var = 'ptZmhw'
pts_df[var].min()
pts_df[var].max()
pts_df[var].count()

pts_df.describe()
