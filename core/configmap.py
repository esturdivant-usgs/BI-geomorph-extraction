# -*- coding: utf-8 -*-
"""
Standard values for CoastalVarExtractor.
They should not need to be changed except to include more site value mappings.
They do not require any input values.
"""
sitemap = {
    'Cedar':{'region': 'Delmarva', 'site': 'Cedar',
                    'code': 'cei',
                    'MHW':0.34, 'MLW':-0.56,
                    'id_init_val':180000,
                    'morph_state' = 12},
    'Smith':{'region': 'Delmarva', 'site': 'Smith',
                    'code': 'smi',
                    'MHW':0.34, 'MLW':-0.56,
                    'id_init_val':120000,
                    'morph_state' = 12},
    'Fisherman':{'region': 'Delmarva', 'site': 'Fisherman', # transects extended manually
                    'code': 'fish',
                    'MHW':0.34, 'MLW':-0.52,
                    'id_init_val':110000,
                    'morph_state' = 12},
    'Assateague':{'region': 'Delmarva', 'site': 'Assateague',
                    'code': 'asis',
                    'MHW':0.34, 'MLW':-0.13,
                    'id_init_val':None,
                    'morph_state' = [12, 13]},
    'ParkerRiver':{'region': 'Massachusetts', 'site': 'ParkerRiver',
                    'code': 'pr',
                    'MHW':1.22, 'MLW':-1.37,
                    'id_init_val':None,
                    'morph_state' = 24},
    'Monomoy':{'region': 'Massachusetts', 'site': 'Monomoy',
                    'code': 'mon',
                    'MHW':0.39, 'MLW':-0.95,
                    'id_init_val':None,
                    'morph_state' = 22},
    'CoastGuard':{'region': 'Massachusetts', 'site': 'CoastGuard',
                    'code': 'cg',
                    'MHW':0.98, 'MLW':-1.1,
                    'id_init_val':None,
                    'morph_state' = 22},
    'Forsythe':{'region': 'NewJersey', 'site': 'Forsythe',
                    'code': 'ebf',
                    'MHW':0.43, 'MLW':-0.61,
                    'id_init_val':30000,
                    'morph_state' = 15},
    'FireIsland':{'region': 'NewYork', 'site': 'FireIsland',
                    'code': 'fiis',
                    'MHW':0.46, 'MLW':-1.01,
                    'id_init_val':10000,
                    'morph_state' = 16},
    'Rockaway':{'region': 'NewYork', 'site': 'Rockaway', # transects extended manually
                    'code': 'rock',
                    'MHW':0.46, 'MLW':-0.71, 
                    'id_init_val':20000,
                    'morph_state' = 16}
    }

########### Default Values ##########################
tID_fld = "sort_ID"                      # name of transect ID field
pID_fld = "SplitSort"                    # name of point ID field
extendlength = 3000                      # distance (m) by which to extend transects
fill = -99999                            # Nulls will be replaced with this fill value
cell_size = 5                            # Cell size for raster outputs
pt2trans_disttolerance = 25              # Maximum distance between transect and point for assigning values; originally 10 m

########### Field names ##########################
trans_flds = ['sort_ID','TRANSORDER', 'TRANSECTID',
    'LRR', 'SL_x', 'SL_y', 'Bslope',
    'DL_x', 'DL_y', 'DL_z', 'DL_zMHW', 'DL_snapX','DL_snapY',
    'DH_x', 'DH_y', 'DH_z', 'DH_zMHW', 'DH_snapX','DH_snapY',
    'Arm_x', 'Arm_y', 'Arm_z', 'Arm_zMHW',
    'DistDH', 'DistDL', 'DistArm',
    'Dist2Inlet', 'WidthPart', 'WidthLand', 'WidthFull',
    'uBW', 'uBH', 'ub_feat', 'mean_Zmhw', 'max_Zmhw']
pt_flds = ['seg_x', 'seg_y', 'ptZ', 'ptSlp', 'Dist_Seg','SplitSort',
    'Dist_MHWbay', 'DistSegDH', 'DistSegDL', 'DistSegArm', 'ptZmhw', 'sort_ID']

extra_fields = ["StartX", "StartY", "ORIG_FID", "Autogen", "ProcTime",
                "SHAPE_Leng", "OBJECTID_1", "Shape_Length", "EndX", "EndY",
                "BaselineID", "OBJECTID", "ORIG_OID", "TRANSORDER_1",
                'LR2', 'LSE', 'LCI90']
extra_fields += [x.upper() for x in extra_fields]

sorted_pt_flds = ['SplitSort', 'seg_x', 'seg_y',
    'Dist_Seg', 'Dist_MHWbay', 'DistSegDH', 'DistSegDL', 'DistSegArm',
    'ptZ', 'ptSlp', 'ptZmhw',
    'GeoSet', 'SubType', 'VegDens', 'VegType',
    'sort_ID','TRANSORDER', 'TRANSECTID', 'DD_ID',
    'LRR', 'SL_x', 'SL_y', 'Bslope',
    'DL_x', 'DL_y', 'DL_z', 'DL_zmhw', 'DL_snapX','DL_snapY',
    'DH_x', 'DH_y', 'DH_z', 'DH_zmhw', 'DH_snapX','DH_snapY',
    'Arm_x', 'Arm_y', 'Arm_z', 'Arm_zmhw',
    'DistDH', 'DistDL', 'DistArm',
    'Dist2Inlet', 'WidthPart', 'WidthLand', 'WidthFull',
    'uBW', 'uBH', 'ub_feat', 'mean_Zmhw', 'max_Zmhw',
    'Construction', 'Development', 'Nourishment']
