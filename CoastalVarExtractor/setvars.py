'''
Configuration file for DeepDive Transect Extraction (CoastalVarExtractor module)
Author: Emily Sturdivant
email: esturdivant@usgs.gov;

Designed to be imported by either prepper.ipynb or extractor.py.
'''
import os
import sys
import arcpy
from CoastalVarExtractor.configmap import *
import CoastalVarExtractor.functions_warcpy as fwa

############ Inputs #########################
# site = 'Fisherman'
# year = '2014'
# proj_dir = r'\\Mac\stor\Projects\TransectExtraction\{}'.format(sitei+yeari)

try:
    sitei = input("site: ")
    yeari = input("year: ")
    input_possible = True
    proj_dir = r'\\Mac\stor\Projects\TransectExtraction\{}'.format(sitei+yeari)
    if not os.path.isdir(proj_dir):
        proj_dir = input("Path to project directory (e.g. \\\Mac\stor\Projects\TransectExtraction\FireIsland2014): ")
    if not os.path.isdir(proj_dir):
        sys.exit("'{}' not recognized as folder. Operation cancelled so you can get the project folder squared away.".format(proj_dir))
    site = sitei
    year = yeari
except:
    input_possible = False
    if len(proj_dir) < 1:
        print("Looks like we can't prompt for user input so you'll need to manually enter values into the module.")
        raise

sitevals = sitemap[site]
yabbr = str(year)[2:4]
home = os.path.join(proj_dir, '{}{}.gdb'.format(sitevals['site'], year))

######## Set-up project folder ################################################
# home = os.path.join(proj_dir, '{site}{year}.gdb'.format(**sitevals))
scratch_dir = os.path.join(proj_dir, 'scratch')
final_dir = os.path.join(proj_dir, 'Extracted_Data')
arcpy.env.workspace = home
arcpy.env.scratchWorkspace = proj_dir
if not os.path.exists(scratch_dir):
    os.makedirs(scratch_dir)

# Set environments
arcpy.env.overwriteOutput = True 						# Overwrite output?
arcpy.CheckOutExtension("Spatial") 						# Checkout Spatial Analysis extension

########### Input file names ##########################
# orig_trans = os.path.join(home, 'DelmarvaS_SVA_LT')
# inletLines = os.path.join(home, 'inletLines')
# ShorelinePts = os.path.join(home, 'SLpts')
# dlPts = os.path.join(home, 'DLpts')
# dhPts = os.path.join(home, 'DHpts')
# armorLines = os.path.join(home, 'armorLines')
# elevGrid = os.path.join(home, 'DEM')

# SubType = os.path.join(home, 'FI15_SubType')
# VegType = os.path.join(home, 'FI15_VegType')
# VegDens = os.path.join(home, 'FI15_VegDens')
# GeoSet = os.path.join(home, 'FI15_GeoSet')

# # Pre-processing outputs
# extendedTrans = os.path.join(home, 'extTrans')
# extTrans_tidy = os.path.join(home, 'tidyTrans')
# elevGrid_5m = os.path.join(home, 'DEM_5m')
# barrierBoundary = os.path.join(home, 'bndpoly_2sl')   # Barrier Boundary polygon; create with TE_createBoundaryPolygon.py
# shoreline = os.path.join(home, 'ShoreBetweenInlets')

# if input_possible:
#     orig_trans = fwa.SetInputFCname(orig_trans, 'original NASC transects', system_ext=True)
#     ShorelinePts = fwa.SetInputFCname(ShorelinePts, 'shoreline points', system_ext=True)
#     dhPts = fwa.SetInputFCname(dhPts, 'dune crest (dhigh) points', system_ext=True)
#     dlPts = fwa.SetInputFCname(dhPts, 'dune toe (dlow) points', system_ext=True)
#     elevGrid = fwa.SetInputFCname(elevGrid, 'DEM', system_ext=True)

########### Default Values ##########################
if sitevals['region'] == 'Massachusetts' or sitevals['region'] == 'RhodeIsland' or sitevals['region'] == 'Maine':
    proj_code = 26919 # "NAD 1983 UTM Zone 19N"
else:
    proj_code = 26918 # "NAD 1983 UTM Zone 18N"
# Spatial references
nad83 = arcpy.SpatialReference(4269)
utmSR = arcpy.SpatialReference(proj_code)

if sitevals['site'] == 'Monomoy':
    maxDH = 3
else:
    maxDH = 2.5

MHW = sitevals['MHW']
MLW = sitevals['MLW']
dMHW = -MHW                         # Beach height adjustment
oMLW = MHW-MLW                      # MLW offset from MHW # Beach height adjustment (relative to MHW)
sitevals['MTL'] = MTL = (MHW+MLW)/2

############## Output filenames/paths ###############################
if not 'elevGrid_5m' in locals() and 'elevGrid' in locals():
    elevGrid_5m = elevGrid+'_5m'                                              # Elevation resampled to 5 m grids
slopeGrid = 'slope_5m'          # Slope in 5 m grids

# INTERMEDIATE OUTPUTS
# Geomorphic features
dh2trans = 'DH2trans'             # DHigh within 25 m
dl2trans = 'DL2trans'             # DLow within 25 m
arm2trans = 'arm2trans'           # XYZ position of armoring along transect
# shl2trans = 'SHL2trans'           # beach slope from lidar within 10m of transect
# Transects
tidy_clipped = "tidyTrans_clipped"
# Points
transPts_presort = os.path.join(arcpy.env.scratchGDB, 'tran5mPts_unsorted')
transPts = 'transPts_working'
pts_elevslope = 'transPts_ZmhwSlp'

# FINAL OUTPUTS
# transects
extTrans_fill = '{}{}_extTrans_fill'.format(sitevals['site'], year)
extTrans_null = '{}{}_extTrans_null'.format(sitevals['site'], year)
extTrans_shp = '{}{}_extTrans_shp'.format(sitevals['site'], year)

# points
transPts_null = '{}{}_transPts_null'.format(sitevals['site'], year)
transPts_fill= '{}{}_transPts_fill'.format(sitevals['site'], year)
transPts_shp = '{}{}_transPts_shp'.format(sitevals['site'], year)

# Rasters
rst_transID = "{}_rstTransID".format(sitevals['site'])
rst_transIDpath = os.path.join(home, rst_transID)
rst_transPopulated = "{}{}_rstTrans_populated".format(sitevals['site'], year)
rst_transgrid_path = os.path.join(scratch_dir, "{}{}_trans".format(sitevals['code'], yabbr))
rst_bwgrid_path = os.path.join(home, "{}{}".format(sitevals['code'], yabbr))
bw_rst="{}{}_ubw".format(sitevals['code'], yabbr)

########### Temp file names ##########################
trans_presort = os.path.join(arcpy.env.scratchGDB, 'trans_presort_temp')
trans_extended = os.path.join(arcpy.env.scratchGDB, 'trans_ext_temp')
trans_sort_1 = os.path.join(arcpy.env.scratchGDB, 'trans_sort_temp')
trans_x = os.path.join(arcpy.env.scratchGDB, 'overlap_points_temp')
overlapTrans_lines = os.path.join(arcpy.env.scratchGDB, 'overlapTrans_lines_temp')
sort_lines =  os.path.join(arcpy.env.scratchGDB, 'sort_lines')

if not __name__ == '__main__':
    print("setvars.py initialized variables.")
