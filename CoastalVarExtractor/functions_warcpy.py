# -*- coding: utf-8 -*-
#! python3

# Transect Extraction module
# possible categories: preprocess, create, calculate

# v1.0 – removed many unused functions. They are still in the former repo (plover_transect_extraction.TransectExtractoin.TE_functions_arcpy)

import arcpy
import time
import os
import collections
import pandas as pd
import numpy as np
from operator import add
import sys
import arcpy
import CoastalVarExtractor.functions as fun

"""
# General use functions
"""
def SetInputFCname(inFCname, varname='', system_ext=True):
    # Look for input feature class name in workspace and prompt for different name if not found.
    if len(varname) < 1:
        varname = inFCname
    if arcpy.Exists(inFCname):
        inFCname = inFCname
    else:
        FCname = input("{} file (e.g. {} or '0' for none): ".format(varname, inFCname))
        if FCname == '0':
            FCname = False
        elif not arcpy.Exists(FCname):
            FCname = input("'{}' doesn't exist in the workspace. Try again. \n{} file: ".format(FCname, varname, inFCname))
            if FCname == '0':
                FCname = False
        if FCname:
            inFCname = os.path.basename(FCname)
        else:
            print('No data selected for {}.'.format(inFCname))
            inFCname = False
            if system_ext:
                raise SystemExit
    return inFCname

def unique_values(table, field):
    # return sorted unique values in field
    data = arcpy.da.TableToNumPyArray(table, [field])
    return numpy.unique(data[field])

def CheckValues(inFeatureClass,fieldName,expectedRange):
    # Check for anomalous values in FC
    lowrows = list()
    highrows = list()
    expectedRange.sort() # make sure pair is [low,high]
    with arcpy.da.UpdateCursor(inFeatureClass,[fieldName,'trans_sort']) as cursor:
        for row in cursor:
            if row[0]< expectedRange[0]:
                row[0] = None
                lowrows.append(row[1])
            elif row[0]>expectedRange[1]:
                row[0] = None
                highrows.append(row[1])
            else:
                pass
            cursor.updateRow(row)
    return lowrows,highrows

def fieldsAbsent(in_fc, fieldnames):
    try:
        fieldList = arcpy.ListFields(os.path.join(arcpy.env.workspace,in_fc))
    except:
        fieldList = arcpy.ListFields(in_fc)
    fnamelist = [f.name.lower() for f in fieldList]
    mfields = []
    for fn in fieldnames:
        if not fn.lower() in fnamelist:
            mfields.append(fn)
    if not len(mfields):
        print("All expected fields present in file '{}'.".format(in_fc))
        return False
    else:
        print("Fields '{}' not present in transects file '{}'.".format(
              mfields, in_fc))
        return mfields

def fieldExists(in_fc, fieldname):
    # Check whether field exists in feature class
    try:
        fieldList = arcpy.ListFields(os.path.join(arcpy.env.workspace, in_fc))
    except:
        fieldList = arcpy.ListFields(in_fc)
    for f in fieldList:
        if f.name.lower() == fieldname.lower():
            return True
    return False

def CopyAndWipeFC(in_fc, out_fc, preserveflds=[]):
    # Make copy of feature class with all Null. Preserves values in necessary and/or indicated fields.
    out_fc = os.path.join(arcpy.env.scratchGDB, out_fc)
    arcpy.CopyFeatures_management(in_fc, out_fc)
    # Replace values of all new transects
    fldsToWipe = [f.name for f in arcpy.ListFields(out_fc)
                  if not f.required and not f.name in preserveflds] # list all fields that are not required in the FC (e.g. OID@)
    with arcpy.da.UpdateCursor(out_fc, fldsToWipe) as cursor:
        for row in cursor:
            cursor.updateRow([None] * len(row))
    return out_fc

def AddNewFields(fc,fieldlist,fieldtype="DOUBLE", verbose=True):
    # Add fields to FC if they do not already exist. New fields must all be the same type.
    # print('Adding fields to {} as type {} if they do not already exist.'.format(out_fc, fieldtype))
    def AddNewField(fc, newfname, fieldtype, verbose):
        # Add single new field
        if not fieldExists(fc, newfname):
            arcpy.AddField_management(fc, newfname, fieldtype)
            if verbose:
                print('Added {} field to {}'.format(newfname, fc))
        return fc
    # Execute for multiple fields
    if type(fieldlist) is str:
        AddNewField(fc, fieldlist, fieldtype, verbose)
    elif type(fieldlist) is list or type(fieldlist) is tuple:
        for newfname in fieldlist:
            AddNewField(fc, newfname, fieldtype, verbose)
    else:
        print("fieldlist accepts string, list, or tuple of field names. {} type not accepted.".format(type(fieldlist)))
    return fc

def DeleteExtraFields(inTable, keepfields=[]):
    fldsToDelete = [x.name for x in arcpy.ListFields(inTable) if not x.required] # list all fields that are not required in the FC (e.g. OID@)
    if keepfields:
        [fldsToDelete.remove(f) for f in keepfields if f in fldsToDelete] # remove keepfields from fldsToDelete
    if len(fldsToDelete):
        arcpy.DeleteField_management(inTable, fldsToDelete)
    return inTable

def DeleteTempFiles(wildcard='*_temp'):
    # Delete files of type FC, Dataset, or Table ending in '_temp' fromw workspace
    templist = []
    try:
        templist = templist + arcpy.ListFeatureClasses(wildcard)
    except:
        pass
    try:
        templist = templist + arcpy.ListDatasets(wildcard)
    except:
        pass
    try:
        templist = templist + arcpy.ListTables(wildcard)
    except:
        pass
    for tempfile in templist:
        arcpy.Delete_management(tempfile)
    return templist

def RemoveLayerFromMXD(lyrname):
    # accepts wildcards
    try:
        mxd = arcpy.mapping.MapDocument('CURRENT')
        for df in arcpy.mapping.ListDataFrames(mxd):
            for lyr in arcpy.mapping.ListLayers(mxd, lyrname, df):
                arcpy.mapping.RemoveLayer(df, lyr)
                return True
            else:
                return True
    except:
        print("Layer '{}' could not be removed from map document.".format(lyrname))
        return False

def ReplaceFields(fc, newoldfields, fieldtype='DOUBLE'):
    # Use tokens to save geometry properties as attributes
    # E.g. newoldfields={'LENGTH':'SHAPE@LENGTH'}
    spatial_ref = arcpy.Describe(fc).spatialReference
    for (new, old) in newoldfields.items():
        if not fieldExists(fc, new): # Add field if it doesn't already exist
            arcpy.DeleteField_management(fc, new)
            arcpy.AddField_management(fc, new, fieldtype)
        with arcpy.da.UpdateCursor(fc, [new, old], spatial_reference=spatial_ref) as cursor:
            for row in cursor:
                cursor.updateRow([row[1], row[1]])
        if fieldExists(fc, old):
            try:
                arcpy.DeleteField_management(fc,old)
            except:
                print(arcpy.GetMessage(2))
                pass
    return fc

def DuplicateField(fc, fld, newname, ftype=False):
    # Copy field values into field with new name
    # 1. get field type
    if not ftype:
        flds = arcpy.ListFields(fc, fld)
        ftype = flds.type
    # 2. add new field
    arcpy.AddField_management(fc, newname, ftype)
    # 3. copy values
    with arcpy.da.UpdateCursor(fc, [fld, newname]) as cursor:
        for row in cursor:
            cursor.updateRow([row[0], row[0]])
    return(fc)

# def AddXYAttributes(fc, newfc, prefix, proj_code=26918):
#     try:
#         try:
#             RemoveLayerFromMXD(fc)
#         except:
#             pass
#         arcpy.MultipartToSinglepart_management(fc,newfc) # failed for SHL2trans_temp: says 'Cannot open...'
#     except arcpy.ExecuteError:
#         print(arcpy.GetMessages(2))
#         print("Attempting to continue")
#         #RemoveLayerFromMXD(fc)
#         arcpy.FeatureClassToFeatureClass_conversion(fc,arcpy.env.workspace,newfc)
#         pass
#     fieldlist = [prefix+'_Lat',prefix+'_Lon',prefix+'_x',prefix+'_y']
#     AddNewFields(newfc, fieldlist)
#     with arcpy.da.UpdateCursor(newfc, [prefix+'_Lon', prefix+'_Lat',"SHAPE@XY"], spatial_reference=arcpy.SpatialReference(4269)) as cursor:
#         [cursor.updateRow([row[2][0], row[2][1], row[2]]) for row in cursor]
#     with arcpy.da.UpdateCursor(newfc,[prefix+'_x',prefix+'_y',"SHAPE@XY"], spatial_reference=arcpy.SpatialReference(proj_code)) as cursor:
#         [cursor.updateRow([row[2][0], row[2][1], row[2]]) for row in cursor]
#     return newfc, fieldlist

def ReplaceValueInFC(fc, oldvalue=-99999, newvalue=None, fields="*"):
    # Replace oldvalue with newvalue in fields in fc
    # First check field types
    with arcpy.da.UpdateCursor(fc, fields) as cursor:
        fieldindex = range(len(cursor.fields))
        for row in cursor:
            for i in fieldindex:
                if row[i] == oldvalue:
                    row[i] = newvalue
            cursor.updateRow(row)
    return fc

def CopyFCandReplaceValues(fc, oldvalue=-99999, newvalue=None, fields="*", out_fc='', out_dir='', verbose=True):
    # Replace oldvalue with newvalue in fields in fc
    # First check field types
    if len(out_fc) > 0:
        if len(out_dir) < 1:
            out_dir = arcpy.env.workspace
        arcpy.FeatureClassToFeatureClass_conversion(fc, out_dir, out_fc)
        fc = out_fc
    fc = ReplaceValueInFC(fc, oldvalue, newvalue, fields)
    if verbose:
        print("OUTPUT: {}".format(fc))
    return fc

def ReProject(fc,newfc,proj_code=26918):
    # If spatial reference does not match desired, project in correct SR.
    if not arcpy.Describe(fc).spatialReference.factoryCode == proj_code: # NAD83 UTM18N
        arcpy.Project_management(fc,newfc,arcpy.SpatialReference(proj_code))
    else:
        newfc = fc
    return newfc

def DeleteFeaturesByValue(fc,fields=[], deletevalue=-99999):
    if not len(fields):
        fs = arcpy.ListFields(fc)
        for f in fs:
            fields.append(f.name)
    with arcpy.da.UpdateCursor(fc, fields) as cursor:
        for row in cursor:
            for i in range(len(fields)):
                if row[i] == deletevalue:
                    cursor.deleteRow()
    return fc

"""
Pre-processing
"""
# Part 1 functions
def ProcessDEM(elevGrid, elevGrid_5m, utmSR):
    # If cell size is not 1x1m in NAD83 UTM Zone__, Project it to such.
    # Aggregate the raster to 5m x 5m
    sr = arcpy.Describe(elevGrid).spatialReference
    cs = arcpy.GetRasterProperties_management(elevGrid, "CELLSIZEX")
    if sr != utmSR or cs.getOutput(0) != '1':
        elevGrid2 = elevGrid+'_projected'
        arcpy.ProjectRaster_management(elevGrid, elevGrid2, utmSR,cell_size="1")
    else:
        elevGrid2 = elevGrid
    outAggreg = arcpy.sa.Aggregate(elevGrid2,5,'MEAN')
    outAggreg.save(elevGrid_5m)
    return(elevGrid_5m)

def ExtendLine(fc, new_fc, distance, proj_code=26918):
    # From GIS stack exchange http://gis.stackexchange.com/questions/71645/a-tool-or-way-to-extend-line-by-specified-distance
    # layer must have map projection
    def accumulate(iterable):
        # accumulate([1,2,3,4,5]) --> 1 3 6 10 15
        # (Equivalent to itertools.accumulate() - isn't in Python 2.7)
        it = iter(iterable)
        total = next(it) # initialize with the first value
        yield total
        for element in it:
            total = add(total, element)
            yield total
    # Project transects to UTM
    if not arcpy.Describe(fc).spatialReference.factoryCode == proj_code:
        print('Projecting {} to UTM'.format(fc))
        arcpy.Project_management(fc, fc+'utm_temp', arcpy.SpatialReference(proj_code))  # project to PCS
        arcpy.FeatureClassToFeatureClass_conversion(fc+'utm_temp', arcpy.env.workspace, new_fc)
    else:
        print('{} is already projected in UTM.'.format(fc))
        arcpy.FeatureClassToFeatureClass_conversion(fc, arcpy.env.workspace, new_fc)
    #OID is needed to determine how to break up flat list of data by feature.
    coordinates = [[row[0], row[1]] for row in
                   arcpy.da.SearchCursor(fc, ["OID@", "SHAPE@XY"],
                   explode_to_points=True)]
    oid, vert = zip(*coordinates)
    # Construct list of numbers that mark the start of a new feature class by
    # counting OIDs and accumulating the values.
    vertcounts = list(accumulate(collections.Counter(oid).values()))
    # Grab the last two vertices of each feature
    lastpoint = [point for x,point in enumerate(vert) if x+1 in vertcounts or x+2 in vertcounts]
    # Obtain list of tuples of new end coordinates by converting flat list of
    # tuples to list of lists of tuples.
    newvert = [fun.newcoord(y, float(distance)) for y in zip(*[iter(lastpoint)]*2)]
    j = 0
    with arcpy.da.UpdateCursor(new_fc, "SHAPE@XY", explode_to_points=True) as cursor:
        for i, row in enumerate(cursor):
            if i+1 in vertcounts:
                row[0] = newvert[j]
                j+=1
                cursor.updateRow(row) #FIXME: If the FC was projected as part of the function, returns RuntimeError: "The spatial index grid size is invalid."
    return new_fc

def PrepTransects_part2(trans_presort, LTextended, barrierBoundary=''):
    # 2. Remove orig transects from manually created transects
    # If any of the original extended transects (with null values) are still present in trans_presort, delete them.
    arcpy.SelectLayerByLocation_management(trans_presort, "ARE_IDENTICAL_TO", LTextended)
    if int(arcpy.GetCount_management(trans_presort)[0]):
        # if old trans in new trans, delete them
        arcpy.DeleteFeatures_management(trans_presort)
    # 3. Append original extended transects (with values) to the new transects
    if len(barrierBoundary)>0:
        arcpy.SelectLayerByLocation_management(LTextended, "INTERSECT", barrierBoundary)
    arcpy.Append_management(LTextended, trans_presort)
    return(trans_presort)

def SpatialSort(in_fc, out_fc, sort_corner='LL', reverse_order=False, startcount=0, sortfield='sort_ID'):
    # Sort transects and assign values to new sortfield; option to assign values in reverse order
    arcpy.Sort_management(in_fc,out_fc,[['Shape','ASCENDING']],sort_corner) # Sort from lower left - this
    try:
        arcpy.AddField_management(out_fc,sortfield,'SHORT')
    except:
        pass
    rowcount = int(arcpy.GetCount_management(out_fc)[0])
    if reverse_order:
        with arcpy.da.UpdateCursor(out_fc,['OID@',sortfield]) as cursor:
            for row in cursor:
                cursor.updateRow([row[0],startcount+rowcount-row[0]+1])
    else:
        with arcpy.da.UpdateCursor(out_fc,['OID@',sortfield]) as cursor:
            for row in cursor:
                cursor.updateRow([row[0],startcount+row[0]])
    return out_fc, rowcount


def SortTransectsFromSortLines(in_fc, out_fc, sort_lines=[], sortfield='sort_ID', sort_corner='LL'):
    # Alternative to SpatialSort() when sorting must be done in spatial groups
    try:
        # add the transect ID field to the transects if it doesn't already exist.
        arcpy.AddField_management(in_fc, sortfield, 'SHORT')
    except:
        pass
    if not len(sort_lines):
        # If sort_lines is blank ([]),
        base_fc, ct = SortTransectsByFeature(in_fc, 0, sort_lines, [1, sort_corner], sortfield)
    else:
        #
        sort_lines_arr = arcpy.da.FeatureClassToNumPyArray(sort_lines, ['sort', 'sort_corn'])
        base_fc, ct = SortTransectsByFeature(in_fc, 0, sort_lines, sort_lines_arr[0])
        for row in sort_lines_arr[1:]:
            next_fc, ct = SortTransectsByFeature(in_fc, ct, sort_lines, row)
            arcpy.Append_management(next_fc, base_fc) # Append each new FC to the base.
    # arcpy.FeatureClassToFeatureClass_conversion(base_fc, arcpy.env.workspace, out_fc)
    SetStartValue(base_fc, out_fc, sortfield, start=1)
    return(out_fc)

def SortTransectsByFeature(in_fc, new_ct, sort_lines=[], sortrow=[0, 'LL'], sortfield='sort_ID'):
    out_fc = 'trans_sort{}_temp'.format(new_ct)
    arcpy.Delete_management(os.path.join(arcpy.env.workspace, out_fc)) # delete if it already exists
    if len(sort_lines):
        arcpy.SelectLayerByAttribute_management(sort_lines, "NEW_SELECTION", "sort = {}".format(sortrow[0]))
        arcpy.SelectLayerByLocation_management(in_fc, overlap_type='INTERSECT', select_features=sort_lines)
    arcpy.Sort_management(in_fc, out_fc, [['Shape', 'ASCENDING']], sortrow[1]) # Sort from lower left - this
    ct = 0
    with arcpy.da.UpdateCursor(out_fc, ['OID@', sortfield]) as cursor:
        for row in cursor:
            ct+=1
            cursor.updateRow([row[0], row[0]+new_ct])
    return(out_fc, ct)

def SetStartValue(trans_sort_1, extendedTrans, tID_fld, start=1):
    # Make sure tID_fld counts from 1
    # Work with duplicate of original transects to preserve them
    arcpy.Sort_management(trans_sort_1, extendedTrans, tID_fld)
    # If tID_fld does not count from 1, adjust the values
    with arcpy.da.SearchCursor(extendedTrans, tID_fld) as cursor:
        row = next(cursor)
    if row[0] > start:
        offset = row[0]-start
        with arcpy.da.UpdateCursor(extendedTrans, tID_fld) as cursor:
            for row in cursor:
                row[0] = row[0]-offset
                cursor.updateRow(row)
    else:
        print("First value was already {}.".format(start))
    return

def PreprocessTransects(site,old_transects=False,sort_corner='LL',sortfield='sort_ID',distance=3000):
    # In copy of transects feature class, create and populate sort field (sort_ID), and extend transects
    if not old_transects:
        old_transects = '{}_LTtransects'.format(site)
    new_transects = '{}_LTtrans_sort'.format(site)
    extTransects = '{}_extTrans'.format(site)
    # Create field trans_order and sort by that
    SpatialSort(old_transects,new_transects,sort_corner,sortfield=sortfield)
    # extend lines
    ExtendLine(new_transects,extTransects,distance)
    return extTransects

def CreateShoreBetweenInlets(shore_delineator, inletLines, out_line, ShorelinePts, proj_code=26918, verbose=True):
    # initialize temp layer names
    split = os.path.join(arcpy.env.scratchGDB, 'shoreline_split')
    # Ready layers for processing
    DeleteExtraFields(inletLines)
    DeleteExtraFields(shore_delineator)
    shore_delineator = ReProject(shore_delineator,shore_delineator+'_utm',proj_code) # Problems projecting
    typeFC = arcpy.Describe(shore_delineator).shapeType
    if typeFC == "Point" or typeFC =='Multipoint':
        line_temp = os.path.join(arcpy.env.scratchGDB, 'shoreline_line')
        shore_temp = os.path.join(arcpy.env.scratchGDB, 'shoreline_shore')
        # Create shoreline from shoreline points
        arcpy.PointsToLine_management(shore_delineator, line_temp)
        shore_delineator = shore_temp
        # Merge and then extend shoreline to inlet lines
        arcpy.Merge_management([line_temp,inletLines],shore_delineator)
        arcpy.ExtendLine_edit(shore_delineator,'500 Meters')
    # Eliminate extra lines, e.g. bayside, based on presence of SHLpts
    if verbose:
        print("Splitting {} at inlets...".format(shore_delineator))
    arcpy.Delete_management(split) # delete if already exists
    arcpy.FeatureToLine_management([shore_delineator, inletLines], split)
    # Delete any lines that are not intersected by a shoreline point.
    if verbose:
        print("Preserving only those line segments that intersect shoreline points...")
    arcpy.SpatialJoin_analysis(split, ShorelinePts, split+'_join', "#","KEEP_COMMON", match_option="COMPLETELY_CONTAINS")
    if verbose:
        print("Dissolving the line to create {}...".format(out_line))
    arcpy.Dissolve_management(split+'_join', out_line, [["FID_{}".format(shore_delineator)]])
    return out_line

def CreateShoreBetweenInlets_old(shore_delineator,inletLines, out_line, ShorelinePts, proj_code=26918):
    # initialize temp layer names
    split_temp = os.path.join(arcpy.env.scratchGDB, 'split_temp')
    # Ready layers for processing
    DeleteExtraFields(inletLines)
    DeleteExtraFields(shore_delineator)
    shore_delineator = ReProject(shore_delineator,shore_delineator+'_utm',proj_code) # Problems projecting
    typeFC = arcpy.Describe(shore_delineator).shapeType
    if typeFC == "Point" or typeFC =='Multipoint':
        line_temp = os.path.join(arcpy.env.scratchGDB, 'line_temp')
        shore_temp = os.path.join(arcpy.env.scratchGDB, 'shore_temp')
        # Create shoreline from shoreline points
        arcpy.PointsToLine_management(shore_delineator, line_temp)
        shore_delineator = shore_temp
        # Merge and then extend shoreline to inlet lines
        arcpy.Merge_management([line_temp,inletLines],shore_delineator)
        arcpy.ExtendLine_edit(shore_delineator,'500 Meters')
    # Eliminate extra lines, e.g. bayside, based on presence of SHLpts
    arcpy.Delete_management(split_temp) # delete if already exists
    arcpy.FeatureToLine_management([shore_delineator, inletLines], split_temp)
    arcpy.SelectLayerByLocation_management("split_temp", "INTERSECT", ShorelinePts,'1 METERS')
    print('CHECK THIS PROCESS. Added Dissolve operation to CreateShore... and so far it has not been tested.')
    arcpy.Dissolve_management('split_temp', out_line, [["FID_{}".format(shore_delineator)]])
    return out_line

def RasterToLandPerimeter(in_raster, out_polygon, threshold, agg_dist='30 METERS', min_area='300 SquareMeters', min_hole_sz='300 SquareMeters', manualadditions=None):
    """ Raster to Polygon: DEM => Reclass => MHW line """
    r2p = os.path.join(arcpy.env.scratchGDB, out_polygon+'_r2p_temp')
    r2p_union = os.path.join(arcpy.env.scratchGDB, out_polygon+'_r2p_union_temp')

    # Reclassify the DEM: 1 = land above threshold; the rest is nodata
    rastertemp = arcpy.sa.Con(arcpy.sa.Raster(in_raster)>threshold, 1, None)  # temporary layer classified from threshold
    # Convert the reclass raster to a polygon
    arcpy.RasterToPolygon_conversion(rastertemp, r2p)  # polygon outlining the area above MHW
    if manualadditions: # Manually digitized any large areas missed by the lidar
        arcpy.Union_analysis([manualadditions,r2p], r2p_union, gaps='NO_GAPS')
        arcpy.AggregatePolygons_cartography(r2p_union, out_polygon, agg_dist, min_area, min_hole_sz)
    else:
        arcpy.AggregatePolygons_cartography(r2p, out_polygon, agg_dist, min_area, min_hole_sz)
    return(out_polygon)

def CombineShorelinePolygons(bndMTL, bndMHW, inletLines, ShorelinePts, bndpoly):
    # Use MTL and MHW contour polygons to create full barrier island shoreline polygon; Shoreline at MHW on oceanside and MTL on bayside
    # Inlet lines must intersect the MHW polygon
    symdiff = os.path.join(arcpy.env.scratchGDB, 'shore_symdiff')
    split_lyrname = 'shore_split'
    split = os.path.join(arcpy.env.scratchGDB, split_lyrname)
    union_2 = os.path.join(arcpy.env.scratchGDB, 'shore_union')

    # Create layer (symdiff) of land between MTL and MHW
    arcpy.Delete_management(symdiff) # delete if already exists
    arcpy.SymDiff_analysis(bndMTL, bndMHW, symdiff)
    arcpy.FeatureToPolygon_management([symdiff, inletLines], split) # Split MTL features at inlets

    # Select bayside MHW-MTL area, polygons that don't intersect shoreline points
    with arcpy.da.UpdateCursor(split, ("SHAPE@")) as cursor:
        for prow in cursor:
            pgeom = prow[0]
            for srow in arcpy.da.SearchCursor(ShorelinePts, ("SHAPE@")):
                spt = srow[0] # point geometry
                if not pgeom.disjoint(spt):
                    cursor.deleteRow()
    # Merge bayside MHW-MTL with above-MHW polygon
    arcpy.Union_analysis([split, bndMHW], union_2)
    arcpy.Dissolve_management(union_2, bndpoly, multi_part='SINGLE_PART') # Dissolve all features in union_2 to single part polygons
    print('''\nUser input required! Select extra features in {} for deletion.\n
        Recommended technique: select the polygon/s to keep and then Switch Selection.\n'''.format(bndpoly))
    return(bndpoly)

def CombineShorelinePolygons_old2(bndMTL, bndMHW, inletLines, ShorelinePts, bndpoly):
    # Use MTL and MHW contour polygons to create full barrier island shoreline polygon; Shoreline at MHW on oceanside and MTL on bayside
    # Inlet lines must intersect the MHW polygon
    symdiff = os.path.join(arcpy.env.scratchGDB, 'symdiff')
    split_lyrname = 'split_temp'
    split = os.path.join(arcpy.env.scratchGDB, 'split_temp')
    union_2 = os.path.join(arcpy.env.scratchGDB, 'union_2_temp')

    # Create layer (symdiff) of land between MTL and MHW
    arcpy.Delete_management(symdiff) # delete if already exists
    arcpy.SymDiff_analysis(bndMTL, bndMHW, symdiff)
    arcpy.FeatureToPolygon_management([symdiff, inletLines], split) # Split MTL features at inlets

    # Select bayside MHW-MTL area, polygons that don't intersect shoreline points
    arcpy.SelectLayerByLocation_management(split_lyrname, "INTERSECT", ShorelinePts, '#', "NEW_SELECTION")
    arcpy.SelectLayerByLocation_management(split_lyrname, "#", ShorelinePts, '#', "SWITCH_SELECTION")
    # arcpy.FeatureClassToFeatureClass_conversion(split_lyrname, arcpy.env.scratchGDB, 'mtlkeep')
    arcpy.Union_analysis([split_lyrname, bndMHW], union_2)
    arcpy.Dissolve_management(union_2, bndpoly, multi_part='SINGLE_PART') # Dissolve all features in union_2 to single part polygons
    print('''\nUser input required! Select extra features in {} for deletion.\n
        Recommended technique: select the polygon/s to keep and then Switch Selection.\n'''.format(bndpoly))
    return bndpoly

def DEMtoFullShorelinePoly(elevGrid, MTL, MHW, inletLines, ShorelinePts):
    bndMTL = 'bndpoly_mtl'
    bndMHW = 'bndpoly_mhw'
    bndpoly = 'bndpoly'
    print("Creating the MTL contour polgon from the DEM...")
    RasterToLandPerimeter(elevGrid, bndMTL, MTL)  # Polygon of MTL contour
    print("Creating the MHW contour polgon from the DEM...")
    RasterToLandPerimeter(elevGrid, bndMHW, MHW)  # Polygon of MHW contour
    print("Combining the two polygons...")
    bndpoly = CombineShorelinePolygons(bndMTL, bndMHW, inletLines, ShorelinePts, bndpoly)
    # print("User input required! Open the files in ArcGIS, select the polygons that should not be included in the final shoreline polygon, and then delete them. ")
    #DeleteTempFiles()
    return(bndpoly)

def NewBNDpoly(old_boundary, modifying_feature, new_bndpoly='boundary_poly', vertexdist='25 METERS', snapdist='25 METERS'):
    # boundary = input line or polygon of boundary to be modified by newline
    typeFC = arcpy.Describe(old_boundary).shapeType
    if typeFC == "Line" or typeFC =='Polyline':
        arcpy.FeatureToPolygon_management(old_boundary,new_bndpoly,'1 METER')
    else:
        arcpy.FeatureClassToFeatureClass_conversion(old_boundary,arcpy.env.workspace,new_bndpoly)
    typeFC = arcpy.Describe(modifying_feature).shapeType
    if typeFC == "Line" or typeFC == "Polyline":
        arcpy.Densify_edit(modifying_feature, 'DISTANCE', vertexdist)
    # elif typeFC == "Point" or typeFC == "Multipoint":
    #     arcpy.PointsToLine_management(modifying_feature, modifying_feature+'_line')
    #     modifying_feature = modifying_feature+'_line'
    #     arcpy.Densify_edit(modifying_feature, 'DISTANCE', vertexdist)
    arcpy.Densify_edit(new_bndpoly, 'DISTANCE', vertexdist)
    #arcpy.Densify_edit(modifying_feature,'DISTANCE',vertexdist)
    arcpy.Snap_edit(new_bndpoly,[[modifying_feature, 'VERTEX',snapdist]]) # Takes a while
    return new_bndpoly # string name of new polygon

def JoinFields(targetfc, sourcefile, dest2src_fields, joinfields=['sort_ID']):
    # Add fields from sourcefile to targetfc; alter
    # If dest2src_fields is a list/tuple instead of dictionary, convert.
    if type(dest2src_fields) is list or type(dest2src_fields) is tuple:
        joinlist = dest2src_fields
        dest2src_fields = {}
        for new in joinlist:
            dest2src_fields[new] = new
    # Prepare target and source FCs: remove new field if it exists and find name of src field
    print('Deleting any fields in {} with the name of fields to be joined ({}).'.format(targetfc, dest2src_fields.keys()))
    for (dest, src) in dest2src_fields.items():
        # Remove dest field from FC if it already exists
        try: #if fieldExists(targetfc, dest):
            arcpy.DeleteField_management(targetfc, dest)
        except:
            pass
        # Search for fieldname matching 'src' field
        found = fieldExists(sourcefile, src) # if src field exists, found is True
        if not found:
            # identify most similarly named field and replace in dest2src_fields
            fieldlist = arcpy.ListFields(sourcefile, src+'*')
            if len(fieldlist) < 2:
                dest2src_fields[dest] = fieldlist[0].name
                found=True
            else:
                for f in fieldlist:
                    if f.name.endswith('_sm'):
                        dest2src_fields[dest] = f.name
                        found = True
        if not found:
            raise AttributeError("Field similar to {} was not found in {}.".format(src, sourcefile))
    # Add [src] fields from sourcefile to targetFC
    src_fnames = dest2src_fields.values()
    print('Joining fields from {} to {}: {}'.format(sourcefile, targetfc, src_fnames))
    if len(joinfields)==1:
        try:
            arcpy.JoinField_management(targetfc, joinfields, sourcefile, joinfields, src_fnames)
        except RuntimeError as e:
            print("JoinField_management produced RuntimeError: {} \nHere were the inputs:".format(e))
            print("dest2src_fields.values (src_fnames): {}".format(src_fnames))
            print("joinfields: {}".format(joinfields))
    elif len(joinfields)==2:
        arcpy.JoinField_management(targetfc, joinfields[0], sourcefile, joinfields[1], src_fnames)
    else:
        print('joinfield accepts either one or two values only.')
    # Rename new fields from src fields
    print('Renaming the joined fields to their new names...')
    for (dest, src) in dest2src_fields.items():
        if not dest == src:
            try:
                arcpy.AlterField_management(targetfc, src, dest, dest)
            except:
                pass
    #arcpy.Delete_management(os.path.join(arcpy.env.workspace,sourcefile))
    return targetfc

"""
#%% dune and shoreline points to transects
"""
def find_similar_fields(prefix, oldPts, fields=[]):
    fmapdict = {'lon': {'dest': prefix+'_Lon'},
                'lat': {'dest': prefix+'_Lat'},
                'east': {'dest': prefix+'_x'},
                'north': {'dest': prefix+'_y'},
                '_z': {'dest': prefix+'_z'},
                'slope': {'dest': 'slope'}}
    # Reduce dict to only desired fields; Default looks for all 6
    if len(fields):
        fdict = {}
        for f in fields:
            fdict[f] = fmapdict[f]
    else:
        fdict = fmapdict
    for key in fdict: # Yes, this loops through keys
        src = key
        if not fieldExists(oldPts, src):
            print('Looking for field {}'.format(src))
            # identify most similarly named field and replace in dest2src_fields
            fieldlist = arcpy.ListFields(oldPts, src+'*')
            if len(fieldlist) == 1: # if there is only one field that matches src
                src = fieldlist[0].name
            elif len(fieldlist) > 1:
                for f in fieldlist:
                    if f.name.endswith('_sm'):
                        src = f.name
            else:
                fieldlist = arcpy.ListFields(oldPts, '*'+src+'*')
                if len(fieldlist) == 1: # if there is only one field that matches src
                    src = fieldlist[0].name
                elif len(fieldlist) > 1:
                    for f in fieldlist:
                        if f.name.endswith('_sm'):
                            src = f.name
                else:
                    # raise AttributeError("Field similar to {} was not found in {}.".format(src, oldPts))
                    print("Field similar to {} was not found in {}.".format(src, oldPts))
                    # pass
        fdict[key]['src'] = src
    return(fdict)

def ArmorLineToTrans_PD(in_trans, armorLines, sl2trans_df, tID_fld, proj_code, elevGrid_5m):
    #FIXME: How do I know which point will be encountered first? - don't want those in back to take the place of
    arm2trans = os.path.join(arcpy.env.scratchGDB, "arm2trans")
    flds = ['Arm_x', 'Arm_y', 'Arm_z']
    if not arcpy.Exists(armorLines) or not int(arcpy.GetCount_management(armorLines).getOutput(0)):
        print('Armoring file either missing or empty so we will proceed without armoring data. If shorefront tampering is present at this site, cancel the operations to digitize.')
        df = pd.DataFrame(columns=flds)
    else:
        # Create armor points with XY fields
        if not arcpy.Exists(arm2trans):
            arcpy.Intersect_analysis((armorLines, in_trans), arm2trans+'_multi', output_type='POINT')
            print('Getting elevation of beach armoring by extracting elevation values to arm2trans points.')
            arcpy.MultipartToSinglepart_management(arm2trans+'_multi', arm2trans)
            arcpy.sa.ExtractMultiValuesToPoints(arm2trans, [[elevGrid_5m, 'Arm_z']])
        df = FCtoDF(arm2trans, xy=True, dffields=[tID_fld, 'Arm_z'])
        df.index = df.pop(tID_fld)
        df.rename(columns={'SHAPE@X':'Arm_x','SHAPE@Y':'Arm_y'}, inplace=True)
    if df.index.duplicated().any():
        idx = df.index[df.index.duplicated()]
        for i in idx:
            sl = sl2trans_df.loc[i, :] # get shoreline point at transect
            rows = df.loc[i,:] # get rows with duplicated transect ID
            rows = rows.assign(bw = lambda x: np.hypot(sl.SL_x - x.Arm_x, sl.SL_y - x.Arm_y)) # calculate dist from SL to each point in row (bw)
            df.drop(i, axis=0, inplace=True)
            df = pd.concat([df, rows.loc[rows['bw'] == min(rows['bw']), flds]]) # return the row with the smallest bw
    return(df)

def add_shorelinePts2Trans(in_trans, in_pts, shoreline, tID_fld='sort_ID', proximity=25, verbose=True):
    #FIXME: save previous cursor (or this one) to dict to reduce iterations https://gis.stackexchange.com/a/30235
    start = time.clock()
    if verbose:
        print("\nJoining shoreline points to transects:")
    # Find fieldname of slope field
    fmapdict = find_similar_fields('sl', in_pts, ['slope'])
    slp_fld = fmapdict['slope']['src']
    # Make dataframe with SL_x, SL_y, Bslope
    df = pd.DataFrame(columns=['SL_x', 'SL_y', 'Bslope'], dtype='float64')
    df.index.name = tID_fld
    # Iterate through transects
    for trow in arcpy.da.SearchCursor(in_trans, ("SHAPE@",  tID_fld)):
        transect = trow[0]
        tID = trow[1]
        #!! Get values (slope at nearest SLpt and XY at intersect) for transect geometry
        newrow = geom_shore2trans(transect, tID, shoreline, in_pts, slp_fld, proximity)
        df.loc[tID, ['SL_x', 'SL_y', 'Bslope']] = newrow
        if verbose:
            if tID % 100 < 1:
                print('Duration at transect {}: {}'.format(tID, fun.print_duration(start, True)))
    fun.print_duration(start)
    return(df)

def geom_dune2trans(transect, tID, in_pts, z_fld, proximity=25):
    z = x = y = np.nan
    shortest_dist = float(proximity)
    for prow in arcpy.da.SearchCursor(in_pts, [z_fld, "SHAPE@X", "SHAPE@Y"]):
        pt_distance = transect.distanceTo(arcpy.Point(prow[1], prow[2]))
        if pt_distance < shortest_dist:
            shortest_dist = pt_distance
            # z, x, y = prow
            x = prow[1]
            y = prow[2]
            z = prow[0]
    return(x, y, z)

def geom_shore2trans(transect, tID, shoreline, in_pts, slp_fld, proximity=25):
    #SUMMARY: for input transect geometry, get slope at nearest shoreline point and XY at intersect
    # 1. Set SL_x and SL_y to point where transect intersects shoreline
    slxpt = arcpy.Point(np.nan, np.nan)
    for srow in arcpy.da.SearchCursor(shoreline, ("SHAPE@")):
        sline = srow[0] # polyline geometry
        # Set SL_x and SL_y to point where transect intersects shoreline
        if not transect.disjoint(sline):
            slxpt = transect.intersect(sline, 1)[0]
    # 2. Get the slope value at the closest shoreline point within proximity
    slp = np.nan
    shortest_dist = float(proximity)
    for prow in arcpy.da.SearchCursor(in_pts, [slp_fld, "SHAPE@X", "SHAPE@Y"]):
        pt_distance = transect.distanceTo(arcpy.Point(prow[1], prow[2])) #FIXME: ValueError: <geoprocessing describe geometry object object at 0x3248E400>
        if pt_distance < shortest_dist:
            shortest_dist = pt_distance
            slp = prow[0]
    # Return: X and Y at the intersect of trans and shoreline, slope at nearest shoreline point (within proximity distance)
    return(slxpt.X, slxpt.Y, slp)

def find_ClosestPt2Trans_snap(in_trans, in_pts, trans_df, prefix, tID_fld='sort_ID', proximity=25, verbose=True, fill=-99999):
    # About 1 minute per transect
    start = time.clock()
    if verbose:
        print("\nJoining {} points to transects:".format(prefix))
    # Get fieldname for Z field
    if verbose:
        print('Getting name of Z field...')
    if prefix == 'DH' or prefix == 'DL':
        fmapdict = find_similar_fields(prefix, in_pts, fields=['_z'])
    z_fld = fmapdict['_z']['src']
    # Initialize dataframe
    out_df = pd.DataFrame(columns=[prefix+'_x', prefix+'_y', prefix+'_z', prefix+'_snapX', prefix+'_snapY'], dtype='f8')
    out_df.index.name = tID_fld
    # Find nearest point
    if verbose:
        print('Looping through transects to find nearest point within {} meters...'.format(proximity))
    for row in arcpy.da.SearchCursor(in_trans, ("SHAPE@", tID_fld)):
        # reset values
        shortest_dist = float(proximity)
        found = False
        # retrieve transect geom, ID value
        transect = row[0]
        tID = row[1]
        for prow in arcpy.da.SearchCursor(in_pts, ["SHAPE@X", "SHAPE@Y", z_fld, "OID@"]):
            in_pt = arcpy.Point(X=prow[0], Y=prow[1], Z=prow[2], ID=prow[3])
            if transect.distanceTo(in_pt) < shortest_dist:
                shortest_dist = transect.distanceTo(in_pt)
                pt = in_pt
                found = True
        if found:
            snappt = transect.snapToLine(arcpy.Point(pt.X, pt.Y))
            out_df.loc[tID, [prefix+'_snapX', prefix+'_snapY']] = [snappt[0].X, snappt[0].Y]
            out_df.loc[tID, [prefix+'_x', prefix+'_y', prefix+'_z']] = [pt.X, pt.Y, pt.Z]
        if verbose:
            if tID % 100 < 1:
                print('Duration at transect {}: {}'.format(tID, fun.print_duration(start, True)))
    duration = fun.print_duration(start)
    return(out_df)

"""
Dist2Inlet
"""
def measure_Dist2Inlet(shoreline, in_trans, inletLines, tID_fld='sort_ID'):
    start = time.clock()
    utmSR = arcpy.Describe(in_trans).spatialReference
    df = pd.DataFrame(columns=[tID_fld, 'Dist2Inlet']) # initialize dataframe
    inlets = [row[0] for row in arcpy.da.SearchCursor(inletLines, ("SHAPE@"))] # get inlet features as geometry objects; faster than cursor in depths of loop
    for row in arcpy.da.SearchCursor(shoreline, ("SHAPE@")): # highest level loop through lines is faster than through transects
        line = row[0]
        for [transect, tID] in arcpy.da.SearchCursor(in_trans, ("SHAPE@",  tID_fld)):
            # [transect, tID] = trow
            if not line.disjoint(transect): #line and transect overlap
                # cut shoreline with transect
                [rseg, lseg] = line.cut(transect)
                # get length for only segs that touch inlets # use only first part in case of multipart feature
                lenR = arcpy.Polyline(rseg.getPart(0), utmSR).length if not all(rseg.disjoint(i) for i in inlets) else np.nan
                lenL = arcpy.Polyline(lseg.getPart(0), utmSR).length if not all(lseg.disjoint(i) for i in inlets) else np.nan
                mindist = np.nanmin([lenR, lenL])
                df = df.append({tID_fld:tID, 'Dist2Inlet':mindist}, ignore_index=True)
    df.index = df[tID_fld]
    df.drop(tID_fld, axis=1, inplace=True)
    fun.print_duration(start) # 25.8 seconds for Monomoy; converting shorelines to geom objects took longer time to complete.
    return(df)

"""
Beach width
"""
def calc_BeachWidth_fill(in_trans, trans_df, maxDH, tID_fld='sort_ID', MHW='', fill=-99999):
    # v3 (v1: arcpy, v2: pandas, v3: pandas with snapToLine() from arcpy)
    # To find dlow proxy, uses code written by Ben in Matlab and converted to pandas by Emily
    # Adds snapToLine() polyline geometry method from arcpy

    # replace nan's with fill for cursor operations;
    #FIXME: may actually be necessary to work with nans... performing calculations with fill results in inaccuracies
    if trans_df.isnull().values.any():
        nan_input = True
        trans_df.fillna(fill, inplace=True)
    else:
        nan_input = False
    # add (or recalculate) elevation fields adjusted to MHW
    trans_df = fun.adjust2mhw(trans_df, MHW, ['DH_z', 'DL_z', 'Arm_z'], fill)
    # initialize df
    bw_df = pd.DataFrame(fill, index=trans_df.index, columns= ['DistDL', 'DistDH', 'DistArm', 'uBW', 'uBH', 'ub_feat'], dtype='f8')
    # field ub_feat gets converted to object type when the value is set
    dl2trans = pd.DataFrame(fill, index=trans_df.index, columns= [tID_fld, 'x', 'y'], dtype='f8')
    dh2trans = pd.DataFrame(fill, index=trans_df.index, columns= [tID_fld, 'x', 'y'], dtype='f8')
    arm2trans = pd.DataFrame(fill, index=trans_df.index, columns= [tID_fld, 'x', 'y'], dtype='f8')
    for row in arcpy.da.SearchCursor(in_trans, ("SHAPE@",  tID_fld)):
        transect = row[0]
        tID = row[1]
        tran = trans_df.loc[tID]
        try:
            if int(tran['SL_x']) != int(fill):
                # Calculate Dist_ values in bw_df columns. Use snapToLine method.
                if int(tran.DL_x) != int(fill):
                    ptDL = transect.snapToLine(arcpy.Point(tran['DL_x'], tran['DL_y']))
                    bw_df.loc[tID, 'DistDL'] = np.hypot(tran['SL_x']- ptDL[0].X, tran['SL_y'] - ptDL[0].Y)
                    dl2trans.loc[tID, ['x', 'y']] = [ptDL[0].X, ptDL[0].Y]
                if int(tran.DH_x) != int(fill):
                    ptDH = transect.snapToLine(arcpy.Point(tran['DH_x'], tran['DH_y']))
                    bw_df.loc[tID, 'DistDH'] = np.hypot(tran['SL_x'] - ptDH[0].X, tran['SL_y'] - ptDH[0].Y)
                    dh2trans.loc[tID, ['x', 'y']] = [ptDH[0].X, ptDH[0].Y]
                if int(tran.Arm_x) != int(fill):
                    ptArm = transect.snapToLine(arcpy.Point(tran['Arm_x'], tran['Arm_y']))
                    bw_df.loc[tID, 'DistArm'] = np.hypot(tran['SL_x'] - ptArm[0].X, tran['SL_y'] - ptArm[0].Y)
                    arm2trans.loc[tID, ['x', 'y']] = [ptArm[0].X, ptArm[0].Y]
                # Select Dist value for uBW. Use DistDL if available. If not and DH < maxDH, use DistDH. If neither available, use DistArm.
                if int(tran.DL_x) != int(fill):
                    bw_df.loc[tID, 'uBW'] = bw_df['DistDL'].loc[tID]
                    bw_df.loc[tID, 'uBH'] = tran['DL_zmhw']
                    bw_df.loc[tID, 'ub_feat'] = 'DL'
                elif int(tran.DH_x) != int(fill) and tran.DH_zmhw <= maxDH:
                    bw_df.loc[tID, 'uBW'] = bw_df['DistDH'].loc[tID]
                    bw_df.loc[tID, 'uBH'] = tran['DH_zmhw']
                    bw_df.loc[tID, 'ub_feat'] = 'DH'
                elif int(tran.Arm_x) != int(fill):
                    bw_df.loc[tID, 'uBW'] = bw_df['DistArm'].loc[tID]
                    bw_df.loc[tID, 'uBH'] = tran['Arm_zmhw']
                    bw_df.loc[tID, 'ub_feat'] = 'Arm'
                else:
                    continue
            else:
                continue
        except TypeError:
            print(tran.DL_x)
            print(fill)
            break
    # Add new uBW and uBH fields to trans_df
    trans_df = fun.join_columns_id_check(trans_df, bw_df, tID_fld)
    if nan_input: # restore nan values
        trans_df.replace(fill, np.nan, inplace=True)
    return(trans_df, dl2trans, dh2trans, arm2trans)

"""
Widths
"""
def calc_IslandWidths(in_trans, barrierBoundary, out_clipped='clip2island', tID_fld='sort_ID'):
    home = arcpy.env.workspace
    out_clipped = os.path.join(arcpy.env.scratchGDB, out_clipped)
    if not arcpy.Exists(out_clipped):
        print('Clipping the transect to the barrier island boundaries...')
        arcpy.Clip_analysis(os.path.join(home, in_trans), os.path.join(home, barrierBoundary), out_clipped) # ~30 seconds
    # WidthPart - spot-checking verifies the results, but it should additionally include a check to ensure that the first transect part encountered intersects the shoreline
    print('Getting the width along each transect of the oceanside land (WidthPart)...')
    out_clipsingle = out_clipped + 'Single_temp'
    if not arcpy.Exists(out_clipsingle):
        arcpy.MultipartToSinglepart_management(out_clipped, out_clipsingle) # could eliminate Multi to Single using
    clipsingles = FCtoDF(out_clipsingle, dffields = ['SHAPE@LENGTH', tID_fld], length=True)
    widthpart = clipsingles.groupby(tID_fld)['SHAPE@LENGTH'].first()
    widthpart.name = 'WidthPart'
    # WidthFull
    print('Getting the width along each transect of the entire barrier (WidthFull)...')
    verts = FCtoDF(out_clipped, id_fld=tID_fld, explode_to_points=True)
    d = verts.groupby(tID_fld)['SHAPE@X', 'SHAPE@Y'].agg(lambda x: x.max() - x.min())
    widthfull = np.hypot(d['SHAPE@X'], d['SHAPE@Y'])
    widthfull.name = 'WidthFull'
    # WidthLand
    print('Getting the width along each transect of above water portion of the barrier (WidthLand)...')
    clipped = FCtoDF(out_clipped, dffields = ['SHAPE@LENGTH', tID_fld], length=True, verbose=False)
    widthland = clipped.groupby(tID_fld)['SHAPE@LENGTH'].first()
    widthland.name = 'WidthLand'
    # Combine into DF
    widths_df = pd.DataFrame({'WidthFull':widthfull, 'WidthLand':widthland, 'WidthPart':widthpart}, index=widthfull.index)
    return(widths_df)

"""
Format conversion
"""
def TransectsToPointsDF(in_trans, barrierBoundary, fc_out='', tID_fld='sort_ID', step=5):
    start = time.clock()
    out_tidyclipped=os.path.join(arcpy.env.scratchGDB, 'tidytrans_clipped2island')
    if not arcpy.Exists(out_tidyclipped):
        arcpy.Clip_analysis(in_trans, barrierBoundary, out_tidyclipped)
    print('Getting points every 5m along each transect and saving in dataframe...')
    # Initialize empty dataframe
    df = pd.DataFrame(columns=[tID_fld, 'seg_x', 'seg_y'])
    # Get shape object and tID value for each transects
    with arcpy.da.SearchCursor(out_tidyclipped, ("SHAPE@", tID_fld)) as cursor:
        for row in cursor:
            ID = row[1]
            line = row[0]
            # Get points in 5m increments along transect and save to df
            for i in range(0, int(line.length), step):
                pt = line.positionAlongLine(i)[0]
                df = df.append({tID_fld:ID, 'seg_x':pt.X, 'seg_y':pt.Y}, ignore_index=True)
    if len(fc_out) > 1:
        print('Converting new dataframe to feature class...')
        fc_out = DFtoFC(df, fc_out, id_fld=tID_fld, spatial_ref = arcpy.Describe(in_trans).spatialReference)
        duration = fun.print_duration(start)
        return(df, fc_out)
    duration = fun.print_duration(start)
    return(df, fc_out)

def FCtoDF(fc, xy=False, dffields=[], fill=-99999, id_fld=False, extra_fields=[], verbose=True, fid=False, explode_to_points=False, length=False):
    # Convert FeatureClass to pandas.DataFrame with np.nan values
    # 1. Convert FC to Numpy array
    if explode_to_points:
        message = 'Converting feature class vertices to array with X and Y...'
        fcfields = [id_fld, 'SHAPE@X', 'SHAPE@Y', 'OID@']
    else:
        fcfields = [f.name for f in arcpy.ListFields(fc)]
        if xy:
            message = 'Converting feature class to array with X and Y...'
            fcfields += ['SHAPE@X','SHAPE@Y']
        else:
            message = 'Converting feature class to array...'
        if fid:
            fcfields += ['OID@']
        if length:
            fcfields += ['SHAPE@LENGTH']
    if verbose:
        print(message)
    arr = arcpy.da.FeatureClassToNumPyArray(os.path.join(arcpy.env.workspace, fc), fcfields, null_value=fill, explode_to_points=explode_to_points)
    # 2. Convert array to dict
    if verbose:
        print('Converting array to dataframe...')
    if not len(dffields):
        dffields = list(arr.dtype.names)
    else:
        if xy:
            dffields += ['SHAPE@X','SHAPE@Y']
        if fid:
            dffields += ['OID@']
        if length:
            dffields += ['SHAPE@LENGTH']
    dict1 = {}
    for f in dffields:
        if np.ndim(arr[f]) < 2:
            dict1[f] = arr[f]
    # 3. Convert dict to DF
    if not id_fld:
        df = pd.DataFrame(dict1)
    else:
        df = pd.DataFrame(dict1, index=arr[id_fld])
        df.index.name = id_fld
    # replace fill values with NaN values
    df.replace(fill, np.nan, inplace=True) # opposite: df.fillna(fill, inplace=True)
    if len(extra_fields) > 0:
        extra_fields += [x.upper() for x in extra_fields]
        df.drop(extra_fields, axis=1, inplace=True, errors='ignore')
    return(df)

def JoinDFtoFC(df, in_fc, join_id, target_id=False, out_fc='', overwrite=True, fill=-99999, verbose=True):
    if not target_id:
        target_id=join_id
    # If out_fc specified, initialize output FC with a copy of input
    if not len(out_fc):
        out_fc = in_fc
    else:
        arcpy.FeatureClassToFeatureClass_conversion(in_fc, arcpy.env.workspace, out_fc)
    # Use arcpy.da.ExtendTable() to join DF
    if df.index.name in df.columns:
        df.index.name = 'index'
    arr = df.select_dtypes(exclude=['object']).fillna(fill).to_records()
    # remove extra fields
    if overwrite:
        DeleteExtraFields(out_fc, [target_id])
    arcpy.da.ExtendTable(out_fc, target_id, arr, join_id, append_only=not overwrite)
    return(out_fc)

def DFtoFC(df, out_fc, spatial_ref, id_fld='', xy=["seg_x", "seg_y"], keep_fields=[], fill=-99999):
    # Create FC from DF; default only copies X,Y,ID fields
    # using too many fields with a large dataset will fail
    # Make sure name of index is not also a column name
    if df.index.name in df.columns:
        df.index.name = 'index'
    # Convert DF to array
    if keep_fields == 'all':
        keep_fields = df.columns
    else:
        keep_fields += xy + [id_fld]
    # First, remove 'object' type columns, all columns not in keep_fields, convert to floats, and fill Nulls.
    # And remove any rows with X or Y == None
    xfld = xy[0]
    df = df[~df[xfld].isnull()]
    df = df[df[xfld]!=fill]
    try:
        arr = (df.select_dtypes(exclude=['object'])
                 .drop(df.columns.drop(keep_fields, errors='ignore'), errors='ignore', axis=1)
                 .astype('f8').fillna(fill).to_records())
    except ValueError:
        df.index.name = 'index'
        arr = (df.select_dtypes(exclude=['object'])
             .drop(df.columns.drop(keep_fields, errors='ignore'), errors='ignore', axis=1)
             .astype('f8').fillna(fill).to_records())
        print('Encountered ValueError while converting dataframe to array so set index name to "index" before running.' )
    # Convert array to FC
    # out_fc = os.path.join(arcpy.env.scratchGDB, os.path.basename(out_fc)) # set out_fc path
    arcpy.Delete_management(out_fc) # delete if already exists
    arcpy.da.NumPyArrayToFeatureClass(arr, out_fc, xy, spatial_ref)
    return(out_fc)

def DFtoFC_large(pts_df, out_fc, spatial_ref, df_id='SplitSort', xy=["seg_x", "seg_y"], fill=-99999, verbose=True):
    # Create FC from DF using only XY and ID; then join the DF to the new FC
    start = time.clock()
    # 1. Create pts FC with only XY and ID
    if verbose:
        print('Converting points DF to FC...')
    out_fc = DFtoFC(df=pts_df, out_fc=out_fc, spatial_ref=spatial_ref, id_fld=df_id, xy=xy, keep_fields=[], fill=fill)
    # 2. join the DF to the new FC
    # convert DF to array, replacing Null with fill and excluding object column types
    arr = pts_df.apply(pd.to_numeric, errors='ignore').select_dtypes(exclude=['object']).fillna(fill).to_records()
    # join array to the XY FC; matching fields in the input will overwrite those in out_fc
    arcpy.da.ExtendTable(out_fc, df_id, arr, df_id, append_only=False) # Takes a long time
    if verbose:
        print("OUTPUT: {}".format(out_fc))
    fun.print_duration(start)
    return(out_fc)

def JoinDFtoRaster(df, rst_ID, out_rst='', fill=-99999, id_fld='sort_ID', val_fld=''):
    # Join fields from df to rst_ID to create new out_rst
    if len(out_rst) < 1:
        out_rst = 'trans2rst_'+val_fld
    # Convert DF to Table
    trans_tbl = os.path.basename(out_rst)+'_tbl'
    tbl_path = DFtoTable(df, trans_tbl)
    # Join field to raster and save as out_rst
    arcpy.CopyRaster_management(rst_ID, out_rst)
    arcpy.management.JoinField(out_rst, "Value", tbl_path, id_fld, val_fld)
    print('OUTPUT: {}. Field "Value" is ID and "uBW" is beachwidth.'.format(out_rst))
    return(out_rst)
