'''
Configuration file for DeepDive Transect Extraction (TE_master_rework and TE_setup_rework)
Author: Emily Sturdivant
email: esturdivant@usgs.gov; bgutierrez@usgs.gov; sawyer.stippa@gmail.com
Date last modified: 3/28/2017
'''
import os
import sys
if sys.platform == 'win32':
    script_path = r"\\Mac\Home\GitHub\plover_transect_extraction\TransectExtraction"
    sys.path.append(script_path) # path to TransectExtraction module
    import arcpy
if sys.platform == 'darwin':
    script_path = '/Users/esturdivant/GitHub/plover_transect_extraction/TransectExtraction'
    sys.path.append(script_path)
from TE_siteyear_configmap import *

############ Inputs #########################
site = 'Assateague'
site = 'ParkerRiver'
site = 'Monomoy'
site = 'CoastGuard'
site = 'FireIsland'
# site = 'Forsythe'
# site = 'Cedar'
year = '2014'

SiteYear_strings = siteyear[site+year]

overwrite_Z = False



######## Set-up project folder ################################################################
proj_dir = os.path.join(r'\\Mac', 'stor', 'Projects', 'TransectExtraction', '{}'.format(site+year))
home = os.path.join(proj_dir, '{site}{year}.gdb'.format(**SiteYear_strings))
scratch_dir = os.path.join(proj_dir, 'scratch')
final_dir = os.path.join(proj_dir, 'Extracted_Data')
try:
    os.makedirs(proj_dir)
except OSError:
    if not os.path.isdir(proj_dir):
        raise

######## Set paths ################################################################
if SiteYear_strings['region'] == 'Massachusetts' or SiteYear_strings['region'] == 'RhodeIsland' or SiteYear_strings['region'] == 'Maine':
    proj_code = 26919 # "NAD 1983 UTM Zone 19N"
else:
    proj_code = 26918 # "NAD 1983 UTM Zone 18N"

######## Set environments ##########
arcpy.env.overwriteOutput = True 						# Overwrite output?
arcpy.CheckOutExtension("Spatial") 						# Checkout Spatial Analysis extension
arcpy.env.workspace = home
arcpy.env.scratchWorkspace = proj_dir
# Spatial references
nad83 = arcpy.SpatialReference(4269)
utmSR = arcpy.SpatialReference(proj_code)

########### Default Values ##########################
tID_fld = "sort_ID"
pID_fld = "SplitSort"
extendlength = 3000                      # extended transects distance (m) IF NEEDED
fill = -99999	  					# Replace Nulls with
cell_size = 5
pt2trans_disttolerance = 25        # Maximum distance that point can be from transect and still be joined; originally 10 m
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

############# Intermediate products ####################
bndMTL = '{site}{year}_bndpoly_mtl'.format(**SiteYear_strings)
bndMHW = '{site}{year}_bndpoly_mhw'.format(**SiteYear_strings)
bndpoly = '{site}{year}_bndpoly'.format(**SiteYear_strings)

############## Outputs ###############################
inletLines = '{site}{year}_inletLines'.format(**SiteYear_strings)
armorLines = '{site}{year}_armor'.format(**SiteYear_strings)
barrierBoundary = '{site}{year}_bndpoly_2sl'.format(**SiteYear_strings)   # Barrier Boundary polygon; create with TE_createBoundaryPolygon.py
dh2trans = '{site}{year}_DH2trans'.format(**SiteYear_strings)							# DHigh within 10m
dl2trans = '{site}{year}_DL2trans'.format(**SiteYear_strings)						# DLow within 10m
arm2trans = '{site}{year}_arm2trans'.format(**SiteYear_strings)
shl2trans = '{site}{year}_SHL2trans'.format(**SiteYear_strings)							# beach slope from lidar within 10m of transect
shoreline = '{site}{year}_ShoreBetweenInlets'.format(**SiteYear_strings)        # Complete shoreline ready to become route in Pt. 2
elevGrid_5m = elevGrid+'_5m'				# Elevation
slopeGrid = '{site}{year}_slope_5m'.format(**SiteYear_strings)

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
old_fields = ['MLW_x','MLW_y', 'bh_mhw','bw_mhw', 'bh_mlw','bw_mlw', 'CP_x','CP_y','CP_zMHW',
              'MAX_ptZmhw', 'MEAN_ptZmhw']
old_trans_flds_arc = ['SL_Lat', 'SL_Lon', 'SL_easting', 'SL_northing', 'Bslope',
                  'DL_Lat', 'DL_Lon', 'DL_easting', 'DL_northing', 'DL_z', 'DL_zMHW',
                  'DH_Lat', 'DH_Lon', 'DH_easting', 'DH_northing', 'DH_z', 'DH_zMHW',
                  'Arm_Lat', 'Arm_Lon', 'Arm_easting', 'Arm_northing', 'Arm_z', 'Arm_zMHW',
                  'DistDH', 'DistDL', 'DistArm',
                  'Dist2Inlet', 'WidthPart', 'WidthLand', 'WidthFull']
repeat_fields = ['SplitSort', 'seg_x', 'seg_y']

old2newflds = {'SL_easting': 'SL_x', 'SL_northing': 'SL_y',
              'DL_easting': 'DL_x', 'DL_northing': 'DL_y',
              'DH_easting': 'DH_x', 'DH_northing': 'DH_y',
              'Arm_easting': 'Arm_x', 'Arm_northing': 'Arm_y',
              'beach_h_MLW': 'uBH', 'beachWidth_MLW': 'uBW',
              'PointZ':'ptZ', 'PointZ_mhw':'ptZmhw', 'PointSlp':'ptSlp',
              'bh_mhw':'uBH', 'bw_mhw':'uBW'}
