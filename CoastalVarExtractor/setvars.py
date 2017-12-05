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

# proj_dir = r"\\Mac\stor\Projects\TransectExtraction\Fisherman2014"
# site = "Fisherman"
# year = "2014"

SiteYear_strings = siteyear[site+year] # get siteyear dict from configmap
home = os.path.join(proj_dir, '{site}{year}.gdb'.format(**SiteYear_strings))

######## Set-up project folder ################################################
# home = os.path.join(proj_dir, '{site}{year}.gdb'.format(**SiteYear_strings))
scratch_dir = os.path.join(proj_dir, 'scratch')
final_dir = os.path.join(proj_dir, 'Extracted_Data')
arcpy.env.workspace = home
arcpy.env.scratchWorkspace = proj_dir
if not os.path.exists(scratch_dir):
    os.makedirs(scratch_dir)

# Set environments
arcpy.env.overwriteOutput = True 						# Overwrite output?
arcpy.CheckOutExtension("Spatial") 						# Checkout Spatial Analysis extension

########### Input files ##########################
orig_trans = os.path.join(home, 'DelmarvaS_SVA_LT')
inletLines = os.path.join(home, 'inletLines')
ShorelinePts = os.path.join(home, 'SLpts')
dlPts = os.path.join(home, 'DLpts')
dhPts = os.path.join(home, 'DHpts')
armorLines = os.path.join(home, 'armorLines')
elevGrid = os.path.join(home, 'DEM')
elevGrid_5m = os.path.join(home, 'DEM_5m')

extendedTrans = os.path.join(home, 'extTrans')
extTrans_tidy = os.path.join(home, 'tidyTrans')
if input_possible:
    orig_trans = fwa.SetInputFCname(orig_trans, 'original NASC transects', system_ext=True)
    ShorelinePts = fwa.SetInputFCname(ShorelinePts, 'shoreline points', system_ext=True)
    dhPts = fwa.SetInputFCname(dhPts, 'dune crest (dhigh) points', system_ext=True)
    dlPts = fwa.SetInputFCname(dhPts, 'dune toe (dlow) points', system_ext=True)
    elevGrid = fwa.SetInputFCname(elevGrid, 'DEM', system_ext=True)

######## Set paths ###########################################################
if SiteYear_strings['region'] == 'Massachusetts' or SiteYear_strings['region'] == 'RhodeIsland' or SiteYear_strings['region'] == 'Maine':
    proj_code = 26919 # "NAD 1983 UTM Zone 19N"
else:
    proj_code = 26918 # "NAD 1983 UTM Zone 18N"
# Spatial references
nad83 = arcpy.SpatialReference(4269)
utmSR = arcpy.SpatialReference(proj_code)

########### Default Values ##########################
if SiteYear_strings['site'] == 'Monomoy':
    maxDH = 3
else:
    maxDH = 2.5

MHW = SiteYear_strings['MHW']
MLW = SiteYear_strings['MLW']
dMHW = -MHW                         # Beach height adjustment
oMLW = MHW-MLW                      # MLW offset from MHW # Beach height adjustment (relative to MHW)
SiteYear_strings['MTL'] = MTL = (MHW+MLW)/2

############## Outputs ###############################
barrierBoundary = '{site}{year}_bndpoly_2sl'.format(**SiteYear_strings)   # Barrier Boundary polygon; create with TE_createBoundaryPolygon.py
dh2trans = '{site}{year}_DH2trans'.format(**SiteYear_strings)             # DHigh within 25 m
dl2trans = '{site}{year}_DL2trans'.format(**SiteYear_strings)             # DLow within 25 m
arm2trans = '{site}{year}_arm2trans'.format(**SiteYear_strings)           # XYZ position of armoring along transect
shl2trans = '{site}{year}_SHL2trans'.format(**SiteYear_strings)           # beach slope from lidar within 10m of transect
shoreline = '{site}{year}_ShoreBetweenInlets'.format(**SiteYear_strings)  # Complete shoreline ready to become route in Pt. 2
elevGrid_5m = elevGrid+'_5m'                                              # Elevation resampled to 5 m grids
slopeGrid = '{site}{year}_slope_5m'.format(**SiteYear_strings)            # Slope in 5 m grids

# Transects
tidy_clipped = "{site}{year}_tidyTrans_clipped".format(**SiteYear_strings)
extTrans_fill = '{site}{year}_extTrans_fill'.format(**SiteYear_strings)
extTrans_null = '{site}{year}_extTrans_null'.format(**SiteYear_strings)
extTrans_shp = '{site}{year}_extTrans_shp'.format(**SiteYear_strings)

# Points
transPts_presort = '{site}{year}_5mPts_unsorted'.format(**SiteYear_strings)
transPts = '{site}{year}_transPts_working'.format(**SiteYear_strings) 	# Outputs Transect Segment points
transPts_null = '{site}{year}_transPts_null'.format(**SiteYear_strings)
transPts_fill= '{site}{year}_transPts_fill'.format(**SiteYear_strings)
transPts_shp = '{site}{year}_transPts_shp'.format(**SiteYear_strings)
pts_elevslope = 'transPts_ZmhwSlp'

# Rasters
rst_transID = "{site}_rstTransID".format(**SiteYear_strings)
rst_transIDpath = os.path.join(home, rst_transID)
rst_transPopulated = "{site}{year}_rstTrans_populated".format(**SiteYear_strings)
rst_transgrid_path = os.path.join(scratch_dir, "{code}_trans".format(**SiteYear_strings))
rst_bwgrid_path = os.path.join(home, "{code}".format(**SiteYear_strings))
bw_rst="{code}_ubw".format(**SiteYear_strings)

########### Temp file names ##########################
trans_presort = os.path.join(arcpy.env.scratchGDB, 'trans_presort_temp')
trans_extended = os.path.join(arcpy.env.scratchGDB, 'trans_ext_temp')
trans_sort_1 = os.path.join(arcpy.env.scratchGDB, 'trans_sort_temp')
trans_x = os.path.join(arcpy.env.scratchGDB, 'overlap_points_temp')
overlapTrans_lines = os.path.join(arcpy.env.scratchGDB, 'overlapTrans_lines_temp')
sort_lines =  os.path.join(arcpy.env.scratchGDB, 'sort_lines')

########### Input/output file names ##########################
extendedTrans = os.path.join(home, 'extTrans')
extTrans_tidy = os.path.join(home, 'tidyTrans')
inletLines = os.path.join(home, 'inletLines')
ShorelinePts = os.path.join(home, 'SLpts')
dlPts = os.path.join(home, 'DLpts')
dhPts = os.path.join(home, 'DHpts')
armorLines = os.path.join(home, 'armorLines')
elevGrid = os.path.join(home, 'DEM')
elevGrid_5m = os.path.join(home, 'DEM_5m')

if not __name__ == '__main__':
    print("setvars.py initialized variables.")
