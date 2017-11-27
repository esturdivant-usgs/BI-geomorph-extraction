'''
Configuration file for DeepDive Transect Extraction (CoastalVarExtractor module)
Author: Emily Sturdivant
email: esturdivant@usgs.gov;

Designed to be imported by either prepper.py or extractor.py.
'''
import os
import sys
import arcpy
from configmap import *

############ Inputs #########################
# site = 'FireIsland'
# year = '2014'
# proj_dir = r'\\Mac\stor\Projects\TransectExtraction\{}'.format(site+year)
if __name__ == '__main__':
    proj_dir = input("Path to project directory (e.g. \\\Mac\stor\Projects\TransectExtraction\FireIsland2014): ")
    site = input("site: ")
    year = input("year: ")
else:
    from __main__ import *
SiteYear_strings = siteyear[site+year] # get siteyear dict from configmap

######## Set-up project folder ################################################################
home = os.path.join(proj_dir, '{site}{year}.gdb'.format(**SiteYear_strings))
scratch_dir = os.path.join(proj_dir, 'scratch')
final_dir = os.path.join(proj_dir, 'Extracted_Data')
try:
    os.makedirs(proj_dir)
except OSError:
    if not os.path.isdir(proj_dir):
        raise
arcpy.env.workspace = home
arcpy.env.scratchWorkspace = proj_dir

# Set environments
arcpy.env.overwriteOutput = True 						# Overwrite output?
arcpy.CheckOutExtension("Spatial") 						# Checkout Spatial Analysis extension

######## Set paths ################################################################
if SiteYear_strings['region'] == 'Massachusetts' or SiteYear_strings['region'] == 'RhodeIsland' or SiteYear_strings['region'] == 'Maine':
    proj_code = 26919 # "NAD 1983 UTM Zone 19N"
else:
    proj_code = 26918 # "NAD 1983 UTM Zone 18N"
# Spatial references
nad83 = arcpy.SpatialReference(4269)
utmSR = arcpy.SpatialReference(proj_code)

########### Default Values ##########################
tID_fld = "sort_ID"                      # name of transect ID field
pID_fld = "SplitSort"                    # name of point ID field
extendlength = 3000                      # distance (m) by which to extend transects
fill = -99999                            # Nulls will be replaced with this fill value
cell_size = 5                            # Cell size for raster outputs
pt2trans_disttolerance = 25              # Maximum distance between transect and point for assigning values; originally 10 m
if SiteYear_strings['site'] == 'Monomoy':
    maxDH = 3
else:
    maxDH = 2.5

MHW = SiteYear_strings['MHW']
MLW = SiteYear_strings['MLW']
dMHW = -MHW                         # Beach height adjustment
oMLW = MHW-MLW                      # MLW offset from MHW # Beach height adjustment (relative to MHW)
SiteYear_strings['MTL'] = MTL = (MHW+MLW)/2

########### Default inputs ##########################
orig_trans = '{site}_LTorig'.format(**SiteYear_strings)
ShorelinePts = '{site}{year}_SLpts'.format(**SiteYear_strings)
dhPts = '{site}{year}_DHpts'.format(**SiteYear_strings)				# Dune crest
dlPts = '{site}{year}_DLpts'.format(**SiteYear_strings) 		  # Dune toe
elevGrid = '{site}{year}_DEM'.format(**SiteYear_strings)				# Elevation

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

########### Field names ##########################
trans_flds0 = ['sort_ID','TRANSORDER', 'TRANSECTID', 'LRR', 'LR2', 'LSE', 'LCI90']
trans_flds_arc = ['SL_Lat', 'SL_Lon', 'SL_x', 'SL_y', 'Bslope',
    'DL_Lat', 'DL_Lon', 'DL_x', 'DL_y', 'DL_z', 'DL_zMHW',
    'DH_Lat', 'DH_Lon', 'DH_x', 'DH_y', 'DH_z', 'DH_zMHW',
    'Arm_Lat', 'Arm_Lon', 'Arm_x', 'Arm_y', 'Arm_z', 'Arm_zMHW',
    'DistDH', 'DistDL', 'DistArm',
    'Dist2Inlet', 'WidthPart', 'WidthLand', 'WidthFull']
trans_flds_arc = ['SL_x', 'SL_y', 'Bslope',
    'DL_x', 'DL_y', 'DL_z', 'DL_zMHW', 'DL_snapX','DL_snapY',
    'DH_x', 'DH_y', 'DH_z', 'DH_zMHW', 'DH_snapX','DH_snapY',
    'Arm_x', 'Arm_y', 'Arm_z', 'Arm_zMHW',
    'DistDH', 'DistDL', 'DistArm',
    'Dist2Inlet', 'WidthPart', 'WidthLand', 'WidthFull']
trans_flds_pd = ['uBW', 'uBH', 'ub_feat', 'mean_Zmhw', 'max_Zmhw']
pt_flds_arc = ['ptZ', 'ptSlp']
pt_flds_pd = ['seg_x', 'seg_y', 'Dist_Seg','SplitSort',
    'Dist_MHWbay', 'DistSegDH', 'DistSegDL', 'DistSegArm', 'ptZmhw']

pt_flds = pt_flds_arc + pt_flds_pd + [tID_fld]
trans_flds = trans_flds0 + trans_flds_arc + trans_flds_pd

extra_fields = ["StartX", "StartY", "ORIG_FID", "Autogen", "ProcTime",
                "SHAPE_Leng", "OBJECTID_1", "Shape_Length", "EndX", "EndY",
                "BaselineID", "OBJECTID", "ORIG_OID", "TRANSORDER_1"]
extra_fields += [x.upper() for x in extra_fields]

if not __name__ == '__main__':
    print("setvars.py initialized variables.")
