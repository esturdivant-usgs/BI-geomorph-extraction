'''
Configuration file for DeepDive Transect Extraction (CoastalVarExtractor module)
Author: Emily Sturdivant
email: esturdivant@usgs.gov;

Designed to be imported by either prepper.ipynb or extractor.py.
'''
import os
import sys
import arcpy
from configmap import *

############ Inputs #########################
# site = 'FireIsland'
# year = '2014'
# proj_dir = r'\\Mac\stor\Projects\TransectExtraction\{}'.format(site+year)
try:
    input_possible = input('Does this interpretter allow for string input? ')
    input_possible = True
except:
    input_possible = False

if input_possible:
    proj_dir = input("Path to project directory (e.g. \\\Mac\stor\Projects\TransectExtraction\FireIsland2014): ")
    if not os.path.isdir(proj_dir):
        reply = input("'{}' not recognized as folder. Do you want to create it (y/n)? ".format(proj_dir))
        if reply == 'y':
            try:
                os.makedirs(proj_dir)
            except OSError:
                if not os.path.isdir(proj_dir):
                    raise
        else:
            sys.exit("Operation cancelled so you can get the project folder squared away.")

    site = input("site: ")
    year = input("year: ")
else:
    proj_dir = ""
    site = ""
    year = ""
    if len(proj_dir) < 1:
        print("Looks like we can't prompt for user input so you'll need to manually enter values into the module.")
        raise

SiteYear_strings = siteyear[site+year] # get siteyear dict from configmap

######## Set-up project folder ################################################
home = os.path.join(proj_dir, '{site}{year}.gdb'.format(**SiteYear_strings))
scratch_dir = os.path.join(proj_dir, 'scratch')
final_dir = os.path.join(proj_dir, 'Extracted_Data')
arcpy.env.workspace = home
arcpy.env.scratchWorkspace = proj_dir

# Set environments
arcpy.env.overwriteOutput = True 						# Overwrite output?
arcpy.CheckOutExtension("Spatial") 						# Checkout Spatial Analysis extension

########### Input files ##########################
orig_trans = '{site}_LTorig'.format(**SiteYear_strings)
ShorelinePts = '{site}{year}_SLpts'.format(**SiteYear_strings)
dhPts = '{site}{year}_DHpts'.format(**SiteYear_strings)				# Dune crest
dlPts = '{site}{year}_DLpts'.format(**SiteYear_strings) 		  # Dune toe
elevGrid = '{site}{year}_DEM'.format(**SiteYear_strings)				# Elevation

if input_possible:
    orig_trans = SetInputFCname(orig_trans, 'original NASC transects', system_ext=True)
    ShorelinePts = SetInputFCname(ShorelinePts, 'shoreline points', system_ext=True)
    dhPts = SetInputFCname(dhPts, 'dune crest (dhigh) points', system_ext=True)
    dlPts = SetInputFCname(dhPts, 'dune toe (dlow) points', system_ext=True)
    elevGrid = SetInputFCname(elevGrid, 'DEM', system_ext=True)

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
inletLines = '{site}{year}_inletLines'.format(**SiteYear_strings)         # delineated inlets
armorLines = '{site}{year}_armor'.format(**SiteYear_strings)              # delineated shorefront armoring to suplement dlows
bndMTL = '{site}{year}_bndpoly_mtl'.format(**SiteYear_strings)            # polygon at MTL contour line; intermediate product
bndMHW = '{site}{year}_bndpoly_mhw'.format(**SiteYear_strings)            # polygon at MHW contour line; intermediate product
bndpoly = '{site}{year}_bndpoly'.format(**SiteYear_strings)               # polygon combined MTL and MHW contour line; before snapped to SLpts
barrierBoundary = '{site}{year}_bndpoly_2sl'.format(**SiteYear_strings)   # Barrier Boundary polygon; create with TE_createBoundaryPolygon.py
dh2trans = '{site}{year}_DH2trans'.format(**SiteYear_strings)             # DHigh within 25 m
dl2trans = '{site}{year}_DL2trans'.format(**SiteYear_strings)             # DLow within 25 m
arm2trans = '{site}{year}_arm2trans'.format(**SiteYear_strings)           # XYZ position of armoring along transect
shl2trans = '{site}{year}_SHL2trans'.format(**SiteYear_strings)           # beach slope from lidar within 10m of transect
shoreline = '{site}{year}_ShoreBetweenInlets'.format(**SiteYear_strings)  # Complete shoreline ready to become route in Pt. 2
elevGrid_5m = elevGrid+'_5m'                                              # Elevation resampled to 5 m grids
slopeGrid = '{site}{year}_slope_5m'.format(**SiteYear_strings)            # Slope in 5 m grids

# Transects
extendedTransects = '{site}{year}_extTrans_working'.format(**SiteYear_strings)
extTrans_tidy = "{site}_tidyTrans".format(**SiteYear_strings)
extendedTrans = "{site}{year}_extTrans".format(**SiteYear_strings) # Created MANUALLY: see TransExtv4Notes.txt
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

if not __name__ == '__main__':
    print("setvars.py initialized variables.")
