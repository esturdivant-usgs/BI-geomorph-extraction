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
site = 'Fisherman'
year = '2014'
proj_dir = r'\\Mac\stor\Projects\TransectExtraction\{}'.format(site+year)

try:
    sitei = input("site: ")
    yeari = input("year: ")
    input_possible = True
except:
    input_possible = False

if input_possible:
    if not os.path.isdir(proj_dir):
        proj_dir = input("Path to project directory (e.g. \\\Mac\stor\Projects\TransectExtraction\FireIsland2014): ")
    if not os.path.isdir(proj_dir):
        sys.exit("'{}' not recognized as folder. Operation cancelled so you can get the project folder squared away.".format(proj_dir))
    site = sitei
    year = yeari
else: # if not possible to prompt user for input
    proj_dir = ""
    site = ""
    year = ""
    if len(proj_dir) < 1:
        print("Looks like we can't prompt for user input so you'll need to manually enter values into the module.")
        raise

sitevals = siteyear[site]
yabbr = str(year)[2:4]
home = os.path.join(proj_dir, '{site}{}.gdb'.format(**sitevals, yabbr))

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
orig_trans = os.path.join(home, 'DelmarvaS_SVA_LT')
# inletLines = os.path.join(home, 'inletLines')
# ShorelinePts = os.path.join(home, 'SLpts')
# dlPts = os.path.join(home, 'DLpts')
# dhPts = os.path.join(home, 'DHpts')
# armorLines = os.path.join(home, 'armorLines')
# elevGrid = os.path.join(home, 'DEM')
# elevGrid_5m = os.path.join(home, 'DEM_5m')
#
# SubType = os.path.join(home, 'FI15_SubType')
# VegType = os.path.join(home, 'FI15_VegType')
# VegDens = os.path.join(home, 'FI15_VegDens')
# GeoSet = os.path.join(home, 'FI15_GeoSet')
#
# extendedTrans = os.path.join(home, 'extTrans')
# extTrans_tidy = os.path.join(home, 'tidyTrans')

# if input_possible:
#     orig_trans = fwa.SetInputFCname(orig_trans, 'original NASC transects', system_ext=True)
#     ShorelinePts = fwa.SetInputFCname(ShorelinePts, 'shoreline points', system_ext=True)
#     dhPts = fwa.SetInputFCname(dhPts, 'dune crest (dhigh) points', system_ext=True)
#     dlPts = fwa.SetInputFCname(dhPts, 'dune toe (dlow) points', system_ext=True)
#     elevGrid = fwa.SetInputFCname(elevGrid, 'DEM', system_ext=True)

######## Set paths ###########################################################
if sitevals['region'] == 'Massachusetts' or sitevals['region'] == 'RhodeIsland' or sitevals['region'] == 'Maine':
    proj_code = 26919 # "NAD 1983 UTM Zone 19N"
else:
    proj_code = 26918 # "NAD 1983 UTM Zone 18N"
# Spatial references
nad83 = arcpy.SpatialReference(4269)
utmSR = arcpy.SpatialReference(proj_code)

########### Default Values ##########################
if sitevals['site'] == 'Monomoy':
    maxDH = 3
else:
    maxDH = 2.5

MHW = sitevals['MHW']
MLW = sitevals['MLW']
dMHW = -MHW                         # Beach height adjustment
oMLW = MHW-MLW                      # MLW offset from MHW # Beach height adjustment (relative to MHW)
sitevals['MTL'] = MTL = (MHW+MLW)/2

############## Outputs ###############################
barrierBoundary = os.path.join(home, 'bndpoly_2sl')   # Barrier Boundary polygon; create with TE_createBoundaryPolygon.py
dh2trans = '{site}{}_DH2trans'.format(**sitevals, year)             # DHigh within 25 m
dl2trans = '{site}{}_DL2trans'.format(**sitevals, year)             # DLow within 25 m
arm2trans = '{site}{}_arm2trans'.format(**sitevals, year)           # XYZ position of armoring along transect
shl2trans = '{site}{}_SHL2trans'.format(**sitevals, year)           # beach slope from lidar within 10m of transect
shoreline = os.path.join(home, 'ShoreBetweenInlets')  # Complete shoreline ready to become route in Pt. 2
if not 'elevGrid_5m' in locals() and 'elevGrid' in locals():
    elevGrid_5m = elevGrid+'_5m'                                              # Elevation resampled to 5 m grids
slopeGrid = '{site}{}_slope_5m'.format(**sitevals, year)            # Slope in 5 m grids

# Transects
tidy_clipped = "tidyTrans_clipped"
extTrans_fill = '{site}{}_extTrans_fill'.format(**sitevals, year)
extTrans_null = '{site}{}_extTrans_null'.format(**sitevals, year)
extTrans_shp = '{site}{}_extTrans_shp'.format(**sitevals, year)

# Points
transPts_presort = os.path.join(arcpy.env.scratchGDB, 'tran5mPts_unsorted')
transPts = 'transPts_working' 	# Outputs Transect Segment points
transPts_null = '{site}{}_transPts_null'.format(**sitevals, year)
transPts_fill= '{site}{}_transPts_fill'.format(**sitevals, year)
transPts_shp = '{site}{}_transPts_shp'.format(**sitevals, year)
pts_elevslope = 'transPts_ZmhwSlp'

# Rasters
rst_transID = "{site}_rstTransID".format(**sitevals)
rst_transIDpath = os.path.join(home, rst_transID)
rst_transPopulated = "{site}{}_rstTrans_populated".format(**sitevals, year)
rst_transgrid_path = os.path.join(scratch_dir, "{code}{}_trans".format(**sitevals, yabbr))
rst_bwgrid_path = os.path.join(home, "{code}{}".format(**sitevals, yabbr))
bw_rst="{code}{}_ubw".format(**sitevals, yabbr)

########### Temp file names ##########################
trans_presort = os.path.join(arcpy.env.scratchGDB, 'trans_presort_temp')
trans_extended = os.path.join(arcpy.env.scratchGDB, 'trans_ext_temp')
trans_sort_1 = os.path.join(arcpy.env.scratchGDB, 'trans_sort_temp')
trans_x = os.path.join(arcpy.env.scratchGDB, 'overlap_points_temp')
overlapTrans_lines = os.path.join(arcpy.env.scratchGDB, 'overlapTrans_lines_temp')
sort_lines =  os.path.join(arcpy.env.scratchGDB, 'sort_lines')

if not __name__ == '__main__':
    print("setvars.py initialized variables.")
