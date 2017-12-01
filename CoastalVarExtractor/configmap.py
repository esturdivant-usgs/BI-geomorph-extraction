# -*- coding: utf-8 -*-

import os
import arcpy

siteyear = {
    'Cedar2010':{'region': 'Delmarva', 'site': 'Cedar',
                    'year': '2010', 'code': 'cei10',
                    'MHW':0.34, 'MLW':-0.56, 'MTL':None},
    'Cedar2012':{'region': 'Delmarva', 'site': 'Cedar',
                    'year': '2012', 'code': 'cei12',
                    'MHW':0.34, 'MLW':-0.56, 'MTL':None},
    'Cedar2014':{'region': 'Delmarva', 'site': 'Cedar',
                    'year': '2014', 'code': 'cei14',
                    'MHW':0.34, 'MLW':-0.56, 'MTL':None},
    'Smith2010':{'region': 'Delmarva', 'site': 'Smith',
                    'year': '2010', 'code': 'smi10',
                    'MHW':0.34, 'MLW':-0.56, 'MTL':None},
    'Smith2012':{'region': 'Delmarva', 'site': 'Smith',
                    'year': '2012', 'code': 'smi12',
                    'MHW':0.34, 'MLW':-0.56, 'MTL':None},
    'Smith2014':{'region': 'Delmarva', 'site': 'Smith',
                    'year': '2014', 'code': 'smi14',
                    'MHW':0.34, 'MLW':-0.56, 'MTL':None},
    'Assateague2014':{'region': 'Delmarva', 'site': 'Assateague',
                    'year': '2014', 'code': 'asis14',
                    'MHW':0.34, 'MLW':-0.13, 'MTL':None},
    'ParkerRiver2014':{'region': 'Massachusetts', 'site': 'ParkerRiver',
                    'year': '2014', 'code': 'pr14',
                    'MHW':1.22, 'MLW':-1.37, 'MTL':None},
    'Monomoy2014':{'region': 'Massachusetts', 'site': 'Monomoy',
                    'year': '2014', 'code': 'mon14',
                    'MHW':0.39, 'MLW':-0.95, 'MTL':None},
    'CoastGuard2014':{'region': 'Massachusetts', 'site': 'CoastGuard',
                    'year': '2014', 'code': 'cg14',
                    'MHW':0.98, 'MLW':-1.1, 'MTL':None},
    'Forsythe2014':{'region': 'NewJersey', 'site': 'Forsythe',
                    'year': '2014', 'code': 'ebf14',
                    'MHW':0.43, 'MLW':-0.61, 'MTL':None},
    'FireIsland2014':{'region': 'NewYork', 'site': 'FireIsland',
                    'year': '2014', 'code': 'fi14',
                    'MHW':0.46, 'MLW':-1.01, 'MTL':None},
    'Fisherman2014':{'region': 'Delmarva', 'site': 'Fisherman',
                    'year': '2014', 'code': 'fish14',
                    'MHW':0.34, 'MLW':-0.52, 'MTL':None}
    }

########### Default Values ##########################
tID_fld = "sort_ID"                      # name of transect ID field
pID_fld = "SplitSort"                    # name of point ID field
extendlength = 3000                      # distance (m) by which to extend transects
fill = -99999                            # Nulls will be replaced with this fill value
cell_size = 5                            # Cell size for raster outputs
pt2trans_disttolerance = 25              # Maximum distance between transect and point for assigning values; originally 10 m

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
