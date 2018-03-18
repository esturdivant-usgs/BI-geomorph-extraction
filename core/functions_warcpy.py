# -*- coding: utf-8 -*-
#! python3
'''
Barrier Island Geomorphology Extraction along transects (BI-geomorph-extraction module)
Author: Emily Sturdivant
email: esturdivant@usgs.gov;

These functions require arcpy.
Designed to be imported by either prepper.ipynb or extractor.py.
'''
import time
import os
import collections
import pandas as pd
import numpy as np
from operator import add
import sys
import arcpy
import core.functions as fun

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
        FCname = input("{} file with path (e.g. {} or '0' for none): ".format(varname, inFCname))
        if FCname == '0':
            FCname = False
        elif not arcpy.Exists(FCname):
            FCname = input("'{}' doesn't exist in the workspace. Try again. \n{} file: ".format(FCname, varname, inFCname))
            if FCname == '0':
                FCname = False
        if FCname:
            inFCname = os.path.basename(FCname)
        else:
            print('No data selected for {}.'.format(os.path.basename(inFCname)))
            inFCname = False
            if system_ext:
                raise SystemExit
    return(inFCname)

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
        print("All expected fields present in file '{}'.".format(os.path.basename(in_fc)))
        return False
    else:
        print("Fields '{}' not present in transects file '{}'.".format(
              mfields, os.path.basename(in_fc)))
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
                print('Added {} field to {}'.format(newfname, os.path.basename(fc)))
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
        print("OUTPUT: {}".format(os.path.basename(fc)))
    return fc

def ReProject(fc, newfc, proj_code=26918, verbose=True):
    # If spatial reference does not match desired, project in correct SR.
    if not arcpy.Describe(fc).spatialReference.factoryCode == proj_code: # NAD83 UTM18N
        arcpy.Project_management(fc, newfc, arcpy.SpatialReference(proj_code))
        if verbose:
            print("The projection of {} was changed. The new file is {}.".format(os.path.basename(fc), os.path.basename(newfc)))
    else:
        newfc = fc

    # Print message
    return(newfc)

def DeleteFeaturesByValue(fc,fields=[], deletevalue=-99999):
    # If the fields argument is blank, defaults to use all fields.
    if not len(fields):
        fs = arcpy.ListFields(fc)
        for f in fs:
            fields.append(f.name)
    # Delete each row where any of the fields listed match the delete value.
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

def RemoveTransectsOutsideBounds(trans, barrierBoundary, distance=200):
    # Delete transects not within 200 m of the study area.
    for row in arcpy.da.SearchCursor(barrierBoundary, ['SHAPE@']):
        geom = row[0]
        with arcpy.da.UpdateCursor(trans, ['SHAPE@']) as cursor:
            for trow in cursor:
                tran = trow[0]
                if tran.disjoint(geom.buffer(distance)):
                    cursor.deleteRow()
    return(trans)

def ExtendLine(fc, new_fc, distance, proj_code=26918, verbose=True):
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
    def newcoord_rev(coords, dist):
        # From: gis.stackexchange.com/questions/71645/extending-line-by-specified-distance-in-arcgis-for-desktop
        # Computes new coordinates x0,y0 at a specified distance along the
        # prolongation of the line from x2,y2 to x1,y1
        (x1,y1),(x2,y2) = coords
        dx = x2 - x1 # change in x
        dy = y2 - y1 # change in y
        linelen = np.hypot(dx, dy) # distance between xy1 and xy2
        x0 = x1 - dx/linelen * dist
        y0 = y1 - dy/linelen * dist
        return x0, y0

    # Project transects to UTM
    if len(os.path.split(new_fc)) > 1:
        fcpath, fcbase = os.path.split(new_fc)
    if not arcpy.Describe(fc).spatialReference.factoryCode == proj_code:
        print('Projecting {} to UTM'.format(os.path.basename(fc)))
        arcpy.Project_management(fc, fc+'utm_temp', arcpy.SpatialReference(proj_code))  # project to PCS
        arcpy.FeatureClassToFeatureClass_conversion(fc+'utm_temp', fcpath, fcbase)
    else:
        print('{} is already projected in UTM.'.format(os.path.basename(fc)))
        arcpy.FeatureClassToFeatureClass_conversion(fc, fcpath, fcbase)

    #OID is needed to determine how to break up flat list of data by feature.
    coordinates = [[row[0], row[1]] for row in
                   arcpy.da.SearchCursor(fc, ["OID@", "SHAPE@XY"],
                   explode_to_points=True)]
    oid, vert = zip(*coordinates)
    # Construct list of numbers that mark the start of a new feature class by
    # counting OIDs and accumulating the values.
    vertcounts = list(accumulate(collections.Counter(oid).values()))

    if distance >= 0:
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
        if verbose:
            print("Transects extended.")
        return(new_fc)
    elif distance < 0:
        # Grab the first two vertices of each feature (they will either be listed in vertcounts or one ahead of one in vertcounts)
        firstpoint = [point for x, point in enumerate(vert) if x in vertcounts or x-1 in vertcounts]
        # Obtain list of tuples of new end coordinates by converting flat list of
        # tuples to list of lists of tuples.
        newvert = [newcoord_rev(y, float(distance)) for y in zip(*[iter(firstpoint)]*2)]
        j = 0
        with arcpy.da.UpdateCursor(new_fc, "SHAPE@XY", explode_to_points=True) as cursor:
            for i, row in enumerate(cursor):
                if i in vertcounts:
                    row[0] = newvert[j]
                    j+=1
                    cursor.updateRow(row) #FIXME: If the FC was projected as part of the function, returns RuntimeError: "The spatial index grid size is invalid."
        if verbose:
            print("Transects extended.")
        return(new_fc)

def ExtendLine_backward(fc, new_fc, distance, proj_code=26918, verbose=True):
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
    if len(os.path.split(new_fc)) > 1:
        fcpath, fcbase = os.path.split(new_fc)
    if not arcpy.Describe(fc).spatialReference.factoryCode == proj_code:
        print('Projecting {} to UTM'.format(os.path.basename(fc)))
        arcpy.Project_management(fc, fc+'utm_temp', arcpy.SpatialReference(proj_code))  # project to PCS
        arcpy.FeatureClassToFeatureClass_conversion(fc+'utm_temp', fcpath, fcbase)
    else:
        print('{} is already projected in UTM.'.format(os.path.basename(fc)))
        arcpy.FeatureClassToFeatureClass_conversion(fc, fcpath, fcbase)

    #OID is needed to determine how to break up flat list of data by feature.
    coordinates = [[row[0], row[1]] for row in
                   arcpy.da.SearchCursor(fc, ["OID@", "SHAPE@XY"],
                   explode_to_points=True)]
    oid, vert = zip(*coordinates)
    # List vert positions that mark the start of a new feature class by counting OIDs and accumulating the values.
    vertcounts = list(accumulate(collections.Counter(oid).values()))

    # Grab the first two vertices of each feature (they will either be listed in vertcounts or one ahead of one in vertcounts)
    firstpoint = [point for x,point in enumerate(vert) if x in vertcounts or x-1 in vertcounts]

    # Obtain list of tuples of new end coordinates by converting flat list of
    # tuples to list of lists of tuples.
    newvert = [newcoord_rev(y, float(distance)) for y in zip(*[iter(firstpoint)]*2)]
    j = 0
    with arcpy.da.UpdateCursor(new_fc, "SHAPE@XY", explode_to_points=True) as cursor:
        for i, row in enumerate(cursor):
            if i in vertcounts:
                row[0] = newvert[j]
                j+=1
                cursor.updateRow(row) #FIXME: If the FC was projected as part of the function, returns RuntimeError: "The spatial index grid size is invalid."
    if verbose:
        print("Transects extended.")
    return(new_fc)

def RemoveDuplicates(trans_presort, orig_xtnd, verbose=True):
    # 2. Remove orig transects from manually created transects
    # If any of the original extended transects (with null values) are still present in trans_presort, delete them.
    for row in arcpy.da.SearchCursor(orig_xtnd, ['SHAPE@']):
        oldline = row[0]
        with arcpy.da.UpdateCursor(trans_presort, ['SHAPE@']) as cursor:
            for trow in cursor:
                tran = trow[0]
                if tran.equals(oldline):
                    cursor.deleteRow()
    # 3. Append original extended transects (with values) to the new transects
    arcpy.Append_management(orig_xtnd, trans_presort)
    if verbose:
        print("{} ready for sorting. It should be in your scratch geodatabase.".format(os.path.basename(trans_presort)))
    return(trans_presort)

def PrepTransects_part2_old(trans_presort, LTextended, barrierBoundary=''):
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

def SortTransectPrep(spatialref, newfields = ['sort', 'sort_corn']):
    multi_sort = input("Do we need to sort the transects in batches to preserve the order? (y/n) ")
    sort_lines = 'sort_lines'
    if multi_sort == 'y':
        sort_lines = arcpy.CreateFeatureclass_management(arcpy.env.scratchGDB, sort_lines, "POLYLINE", spatial_reference=spatialref)
        arcpy.AddField_management(sort_lines, newfields[0], 'SHORT', field_precision=2)
        arcpy.AddField_management(sort_lines, newfields[1], 'TEXT', field_length=2)
        print("MANUALLY: Add features to sort_lines. Indicate the order of use in 'sort' and the sort corner in 'sort_corn'.")
    else:
        sort_lines = []
        # Corner from which to start sorting, LL = lower left, etc.
        sort_corner = input("Sort corner (LL, LR, UL, UR): ")
    return(sort_lines)

def SortTransectsFromSortLines(in_trans, out_trans, sort_lines=[], tID_fld='sort_ID', sort_corner='LL', verbose=True):
    """
    Sort the transects along the shoreline using pre-created lines (sort_lines) to sort.
    """
    temppath = os.path.join(arcpy.env.scratchGDB, 'trans_')
    # Add the transect ID field to the transects if it doesn't already exist.
    AddNewFields(in_trans,[tID_fld],fieldtype="SHORT", verbose=True)
    # If sort_lines is blank ([]), go ahead and sort the transects based on sort_corner argument.
    if not len(sort_lines):
        if verbose:
            print("sort_lines not specified, so we are sorting the transects in one group from the {} corner.".format(sort_corner))
        out_trans = arcpy.Sort_management(in_trans, out_trans, [['Shape', 'ASCENDING']], sort_corner) # Sort from lower lef
    else:
        if verbose:
            print("Creating new feature class {} to hold sorted transects...".format(os.path.basename(out_trans)))
        out_trans = arcpy.CreateFeatureclass_management(arcpy.env.workspace, os.path.basename(out_trans), "POLYLINE", in_trans, spatial_reference=in_trans)
        dsc = arcpy.Describe(in_trans)
        fieldnames = [field.name for field in dsc.fields if not field.name == dsc.OIDFieldName] + ['SHAPE@']
        # Sort the sort_lines by field 'sort'
        # Loop through ordered sort_lines
        # Make a new FC with only the transects that intersect the given sort line.
        # Sort the subsetted transects and append each one to out_trans
        if verbose:
            print("Sorting sort lines by field sort...")
        sort_lines2 = arcpy.Sort_management(sort_lines, sort_lines+'2', [['sort', 'ASCENDING']])
        if verbose:
            print("For each line, creating subset of transects and adding them in order to the new FC...")
        for sline, scorner, reverse_order in arcpy.da.SearchCursor(sort_lines2, ['SHAPE@', 'sort_corn', 'reverse']):
            # Get transects that intersect sort line: copy transects, then delete all rows that don't intersect.
            temp1 = arcpy.FeatureClassToFeatureClass_conversion(in_trans, arcpy.env.scratchGDB, 'trans_subset')
            with arcpy.da.UpdateCursor(temp1, ['SHAPE@']) as cursor:
                for trow in cursor:
                    tran = trow[0]
                    if tran.disjoint(sline):
                        cursor.deleteRow()
            # Sort the remaining transects.
            temp2 = arcpy.Sort_management(temp1, temppath+'sub_sort{}'.format(scorner), [['Shape', 'ASCENDING']], scorner)
            # Reverse the order if specified.
            if reverse_order == 'T':
                # Reverse the sort order, i.e. reverse the OID values
                # Copy OID values to tID_fld then sort in descending order, which will reverse the OID values
                with arcpy.da.UpdateCursor(temp2, ['OID@', tID_fld]) as cursor:
                    for row in cursor:
                        cursor.updateRow([row[0], row[0]])
                temp2 = arcpy.Sort_management(temp2, temppath+'subrev_sort{}'.format(scorner), [[tID_fld, 'DESCENDING']])
            # Append the new section of sorted transects to those already completed.
            with arcpy.da.InsertCursor(out_trans, fieldnames) as icur:
                for row in arcpy.da.SearchCursor(temp2, fieldnames):
                    icur.insertRow(row)
    if verbose:
        print("Copying the generated OID values to the transect ID field ({})...".format(tID_fld))
    # Copy the OID values, which should be correctly sorted, to the tID_fld
    with arcpy.da.UpdateCursor(out_trans, ['OID@', tID_fld]) as cursor:
        for row in cursor:
            cursor.updateRow([row[0], row[0]])
    return(out_trans)

def SortTransectsFromSortLines_old(in_fc, out_fc, sort_lines=[], sortfield='sort_ID', sort_corner='LL'):
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
        # Sort the sort lines by the desginated field.
        sort_lines2 = sort_lines+'_sorted'
        arcpy.Sort_management(sort_lines, sort_lines2, [['sort', 'ASCENDING']])
        # Convert the file to a numpy array to access the values.
        sort_lines_arr = arcpy.da.FeatureClassToNumPyArray(sort_lines2, ['sort', 'sort_corn'])
        base_fc, ct = SortTransectsByFeature(in_fc, 0, sort_lines2, sort_lines_arr[0])
        for row in sort_lines_arr[1:]:
            next_fc, ct = SortTransectsByFeature(in_fc, ct, sort_lines2, row)
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

def CreateShoreBetweenInlets(shore_delineator, inletLines, out_line, ShorelinePts, proj_code=26918, SA_bounds='', verbose=True):
    # initialize temp layer names
    split = os.path.join(arcpy.env.scratchGDB, 'shoreline_split')
    # Ready layers for processing
    DeleteExtraFields(inletLines)
    DeleteExtraFields(shore_delineator)
    shore_delineator = ReProject(shore_delineator, shore_delineator+'_utm', proj_code) # Problems projecting
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
        print("Splitting {} at inlets...".format(os.path.basename(shore_delineator)))
    arcpy.Delete_management(split) # delete if already exists
    if len(SA_bounds) > 0:
        arcpy.FeatureToLine_management([shore_delineator, inletLines, SA_bounds], split)
    else:
        arcpy.FeatureToLine_management([shore_delineator, inletLines], split)
    # Delete any lines that are not intersected by a shoreline point.
    if verbose:
        print("Preserving only those line segments that intersect shoreline points...")
    arcpy.SpatialJoin_analysis(split, ShorelinePts, split+'_join', "#","KEEP_COMMON", match_option="COMPLETELY_CONTAINS")
    if verbose:
        print("Dissolving the line to create {}...".format(os.path.basename(out_line)))
    dissolve_fld = "FID_{}".format(os.path.basename(shore_delineator))
    arcpy.Dissolve_management(split+'_join', out_line, [[dissolve_fld]], multi_part="SINGLE_PART")
    return out_line

def RasterToLandPerimeter(in_raster, out_polygon, threshold, agg_dist='30 METERS', min_area='300 SquareMeters', min_hole_sz='300 SquareMeters', manualadditions=None):
    """
    Raster to Polygon: DEM => Reclass => MHW line
    """
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

def CombineShorelinePolygons(bndMTL, bndMHW, inletLines, ShorelinePts, bndpoly, SA_bounds='', verbose=True):
    """
    Use MTL and MHW contour polygons to create shoreline polygon.
    'Shoreline' = MHW on oceanside and MTL on bayside
    """
    start = time.clock()
    # Inlet lines must intersect the MHW polygon
    symdiff = os.path.join(arcpy.env.scratchGDB, 'shore_1symdiff')
    split_lyrname = 'shore_2split'
    split = os.path.join(arcpy.env.scratchGDB, split_lyrname)
    union_2 = os.path.join(arcpy.env.scratchGDB, 'shore_3union')

    # Create layer (symdiff) of land between MTL and MHW and split by inlets
    arcpy.Delete_management(symdiff) # delete if already exists
    arcpy.SymDiff_analysis(bndMTL, bndMHW, symdiff)
    if len(SA_bounds) > 0:
        arcpy.FeatureToPolygon_management([symdiff, inletLines, SA_bounds], split) # Split MTL features at inlets and study area bounds
    else:
        arcpy.FeatureToPolygon_management([symdiff, inletLines], split) # Split MTL features at inlets

    print("Isolating the above-MTL portion of the polygon to the bayside...")
    # Select bayside MHW-MTL area, polygons that don't intersect shoreline points
    pcnt = 0
    totalp = arcpy.GetCount_management(split)[0]
    # Get shoreline points geometry objects
    slpts = [srow[0] for srow in arcpy.da.SearchCursor(inletLines, ("SHAPE@"))]
    with arcpy.da.UpdateCursor(split, ("SHAPE@")) as cursor:
        for prow in cursor:
            pgeom = prow[0]
            # If polygon instersects any shoreline point, delete it
            if not all(pgeom.disjoint(spt) for spt in slpts):
                cursor.deleteRow()
            if verbose:
                pcnt += 1
                if pcnt % 100 < 1:
                    print('...duration at polygon {} out of {}: {}'.format(pcnt,
                            fun.print_duration(start, totalp, True)))

    # Merge bayside MHW-MTL with above-MHW polygon
    arcpy.Union_analysis([split, bndMHW], union_2)
    arcpy.Dissolve_management(union_2, bndpoly, multi_part='SINGLE_PART') # Dissolve all features in union_2 to single part polygons
    print('''\nUser input required! Select extra features in {} for deletion.\n
        Recommended technique: select the polygon/s to keep and then Switch Selection.\n'''.format(os.path.basename(bndpoly)))
    return(bndpoly)

def DEMtoFullShorelinePoly(elevGrid, MTL, MHW, inletLines, ShorelinePts, SA_bounds=''):
    bndMTL = 'bndpoly_mtl'
    bndMHW = 'bndpoly_mhw'
    bndpoly = 'bndpoly'
    print("Creating the MTL contour polgon from the DEM...")
    RasterToLandPerimeter(elevGrid, bndMTL, MTL)  # Polygon of MTL contour
    print("Creating the MHW contour polgon from the DEM...")
    RasterToLandPerimeter(elevGrid, bndMHW, MHW)  # Polygon of MHW contour
    print("Combining the two polygons...")
    bndpoly = CombineShorelinePolygons(bndMTL, bndMHW, inletLines, ShorelinePts, bndpoly, SA_bounds)
    #DeleteTempFiles()
    return(bndpoly)

def NewBNDpoly(old_boundary, modifying_feature, new_bndpoly='boundary_poly', vertexdist='25 METERS', snapdist='25 METERS', verbose=True):
    # boundary = input line or polygon of boundary to be modified by newline
    typeFC = arcpy.Describe(old_boundary).shapeType
    if typeFC == "Line" or typeFC =='Polyline':
        arcpy.FeatureToPolygon_management(old_boundary, new_bndpoly, '1 METER')
    else:
        if len(os.path.split(new_bndpoly)[0]):
            path = os.path.split(new_bndpoly)[0]
        else:
            path = arcpy.env.workspace
        arcpy.FeatureClassToFeatureClass_conversion(old_boundary, path, os.path.basename(new_bndpoly))
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
    if verbose:
        print("Created: {} ... Should be in your home geodatabase.".format(os.path.basename(new_bndpoly)))
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
    print('Deleting any fields in {} with the name of fields to be joined ({}).'.format(os.path.basename(targetfc), dest2src_fields.keys()))
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
            raise AttributeError("Field similar to {} was not found in {}.".format(src, os.path.basename(sourcefile)))
    # Add [src] fields from sourcefile to targetFC
    src_fnames = dest2src_fields.values()
    print('Joining fields from {} to {}: {}'.format(os.path.basename(sourcefil), os.path.basename(targetfc), src_fnames))
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
def find_similar_fields(prefix, oldPts, fields=[], verbose=True):
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
            if verbose:
                print('Looking for field similar to {}{}'.format(prefix, src))
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
                    print("Field similar to {} was not found in {}.".format(src, os.path.basename(oldPts)))
                    # pass
        fdict[key]['src'] = src
    return(fdict)

def ArmorLineToTrans_PD(in_trans, armorLines, sl2trans_df, tID_fld, proj_code, elevGrid_5m):
    #FIXME: How do I know which point will be encountered first? - don't want those in back to take the place of
    arm2trans = os.path.join(arcpy.env.scratchGDB, "arm2trans")
    flds = ['Arm_x', 'Arm_y', 'Arm_z']
    if not arcpy.Exists(armorLines) or not int(arcpy.GetCount_management(armorLines).getOutput(0)):
        print('\nArmoring file either missing or empty so we will proceed without armoring data. If shorefront tampering is present at this site, cancel the operations to digitize.')
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
    # Where multiple armor intersect points created along a transect, use the closest point to the shoreline.
    if df.index.duplicated().any():
        idx = df.index[df.index.duplicated()]
        print("Looks like these transects {} are intersected by armoring lines multiple times. We will select the more seaward of the points.".format(idx.unique().tolist()))
        for i in idx.unique():
            sl = sl2trans_df.loc[i, :] # get shoreline point at transect #FIXME: what happens if there's no shoreline point
            rows = df.loc[i,:] # get rows with duplicated transect ID
            rows = rows.assign(bw = lambda x: np.hypot(sl.SL_x - x.Arm_x, sl.SL_y - x.Arm_y)) # calculate dist from SL to each point in row (bw) #FIXME: 'Series' object has no attribute 'assign'
            df.drop(i, axis=0, inplace=True)
            df = pd.concat([df, rows.loc[rows['bw'] == min(rows['bw']), flds]]) # return the row with the smallest bw
    return(df)

def geom_shore2trans(transect, tID, shoreline, in_pts, slp_fld, proximity=25):
    """
    #For input transect geometry, get slope at nearest shoreline point and XY at intersect
    """
    # 1. Set SL_x and SL_y at point where transect intersects shoreline
    slxpt = arcpy.Point(np.nan, np.nan)
    for srow in arcpy.da.SearchCursor(shoreline, ("SHAPE@")):
        sline = srow[0]
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

def add_shorelinePts2Trans(in_trans, in_pts, shoreline, tID_fld='sort_ID', proximity=25, verbose=True):
    """
    """
    start = time.clock()
    if verbose:
        print("\nMatching shoreline points to transects...")

    # Find fieldname of slope field
    fmapdict = find_similar_fields('sl', in_pts, ['slope'])
    slp_fld = fmapdict['slope']['src']
    if verbose:
        print("Using field '{}' as slope.".format(slp_fld))
    in_pts = ReProject(in_pts, in_pts+'_utm', proj_code=arcpy.Describe(in_trans).spatialReference.factoryCode)

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
                print('...duration at transect {}: {}'.format(tID, fun.print_duration(start, True)))

    fun.print_duration(start)
    return(df)

def geom_dune2trans(trow, out_df, in_pts, z_fld, prefix, proximity=25):
    """
    Find the nearest dune point to the input transect.

    # for 'trow' (a row in the transect search cursor),
    # find the nearest dune point within 25 m of the transect and
    # add to the working dataframe (out_df)
    """
    # initialize column names, shortest distance threshold, and found=false
    colnames_xyz = [prefix+'_x', prefix+'_y', prefix+'_z']
    colnames_snapt = [prefix+'_snapX', prefix+'_snapY']
    shortest_dist = float(proximity)
    found = False
    # retrieve transect geom, ID value
    transect = trow[0]
    tID = trow[1]
    # iterate through dune points using SearchCursor
    # update the shortest distance value if the distance to the point is shorter than the threshold or than previous found.
    for prow in arcpy.da.SearchCursor(in_pts, ["SHAPE@X", "SHAPE@Y", z_fld, "OID@"]):
        in_pt = arcpy.Point(X=prow[0], Y=prow[1], Z=prow[2], ID=prow[3])
        if transect.distanceTo(in_pt) < shortest_dist:
            shortest_dist = transect.distanceTo(in_pt)
            pt = in_pt
            found = True
    # Once all the dune points have been checked, and
    # if one was nearer to the transect than the original threshold,
    # then assign the XYZ values of that point to the working dataframe.
    if found:
        snappt = transect.snapToLine(arcpy.Point(pt.X, pt.Y))
        out_df.loc[tID, colnames_snapt] = [snappt[0].X, snappt[0].Y]
        out_df.loc[tID, colnames_xyz] = [pt.X, pt.Y, pt.Z]
    return(out_df)

def find_ClosestPt2Trans_snap(in_trans, dh_pts, dl_pts, trans_df, tID_fld='sort_ID', proximity=25, verbose=True, fill=-99999):
    """
    Find the nearest dune crest/toe point to the transects.


    """
    # 12 minutes for FireIsland
    start = time.clock()
    if verbose:
        print("\nMatching dune points with transects:")

    # Get fieldname for elevation (Z) field
    fmapdict = find_similar_fields('DH', dh_pts, fields=['_z'], verbose=False)
    dhz_fld = fmapdict['_z']['src']
    if verbose:
        print("Using field '{}' as DH Z field...".format(dhz_fld))
    dh_pts = ReProject(dh_pts, dh_pts+'_utm', proj_code=arcpy.Describe(in_trans).spatialReference.factoryCode)

    # Get fieldname for elevation (Z) field
    fmapdict = find_similar_fields('DL', dl_pts, fields=['_z'], verbose=False)
    dlz_fld = fmapdict['_z']['src']
    if verbose:
        print("Using field '{}' as DL Z field...".format(dlz_fld))
    dl_pts = ReProject(dl_pts, dl_pts+'_utm', proj_code=arcpy.Describe(in_trans).spatialReference.factoryCode)

    # Initialize dataframe
    colnames =['DH_x', 'DH_y', 'DH_z', 'DH_snapX', 'DH_snapY',
                'DL_x', 'DL_y', 'DL_z', 'DL_snapX','DL_snapY']
    out_df = pd.DataFrame(columns=colnames, dtype='f8')
    out_df.index.name = tID_fld

    # Find nearest point to each transect
    if verbose:
        print('Looping through transects and dune points to find nearest point within {} m...'.format(proximity))
    for trow in arcpy.da.SearchCursor(in_trans, ("SHAPE@", tID_fld)):

        # Dune crests (dhigh)
        out_df = geom_dune2trans(trow, out_df, dh_pts, dhz_fld, prefix='DH', proximity=proximity)
        # Dune toes (dlow)
        out_df = geom_dune2trans(trow, out_df, dl_pts, dlz_fld, prefix='DL', proximity=proximity)

        if verbose:
            tID = trow[1]
            if tID % 100 < 1:
                print('...duration at transect {}: {}'.format(tID, fun.print_duration(start, True)))

    duration = fun.print_duration(start)
    return(out_df)

"""
Dist2Inlet
"""
def measure_Dist2Inlet(shoreline, in_trans, inletLines, tID_fld='sort_ID'):
    """
    # measure distance along oceanside shore from transect to inlet.
    # Uses three SearchCursors (arcpy's data access module).
    # Stores values in new data frame.
    """
    # Initialize
    start = time.clock()
    utmSR = arcpy.Describe(in_trans).spatialReference
    df = pd.DataFrame(columns=[tID_fld, 'Dist2Inlet']) # initialize dataframe
    # Get inlets geometry objects
    inlets = [row[0] for row in arcpy.da.SearchCursor(inletLines, ("SHAPE@"))]
    # Loop through shoreline features
    for row in arcpy.da.SearchCursor(shoreline, ("SHAPE@")):
        line = row[0]
        # Loop through transect features
        for [transect, tID] in arcpy.da.SearchCursor(in_trans, ("SHAPE@",  tID_fld)):
            if not line.disjoint(transect):
                # 1. cut shoreline at the transect
                [rseg, lseg] = line.cut(transect)
                # 2. if the shoreline segment touches any inlet, get the segment length.
                #    If it doesn't touch an inlet, length is set to NaN to remove it from consideration.
                #    In case of multipart features, use the shortest part that intersects an inlet.
                lenR = np.nan
                for pi in range(rseg.partCount):
                    part = arcpy.Polyline(rseg.getPart(pi), utmSR)
                    if not all(part.disjoint(i) for i in inlets):
                        lenR = np.nanmin([lenR, part.length])
                lenL = np.nan
                for pi in range(lseg.partCount):
                    part = arcpy.Polyline(lseg.getPart(pi), utmSR)
                    if not all(part.disjoint(i) for i in inlets):
                        lenL = np.nanmin([lenL, part.length])
                # 3. If shoreline and transect intersect on an inlet line, return 0 because transect is at an inlet.
                #    Only check for overlap at segments that touch an inlet (not NaN).
                xpt = line.intersect(transect, 1) # point where shoreline and transect intersect
                lenR = 0 if not np.isnan(lenR) and not all(xpt.disjoint(i) for i in inlets) else lenR
                lenL = 0 if not np.isnan(lenL) and not all(xpt.disjoint(i) for i in inlets) else lenL
                # 4. Return the length of the shorter segment and save it in the DF
                mindist = np.nanmin([lenR, lenL])
                df = df.append({tID_fld:tID, 'Dist2Inlet':mindist}, ignore_index=True)
                # Alert if there is a large change (>300 m) in values between consecutive transects
                try:
                    dist_prev = pd.to_numeric(df.loc[df[tID_fld]==tID-1, 'Dist2Inlet'])
                    if any(abs(dist_prev - mindist) > 300):
                        print("CAUTION: Large change in Dist2Inlet values between transects {} ({} m) and {} ({} m).".format(tID-1, dist_prev, tID, mindist))
                except:
                    print("Error-catching is not working in Dist2Inlet.")
                    pass
    df.index = df[tID_fld]
    df.drop(tID_fld, axis=1, inplace=True)
    fun.print_duration(start) # 25.8 seconds for Monomoy; converting shorelines to geom objects took longer time to complete.
    return(df)

"""
Beach width
"""
def calc_BeachWidth_fill(in_trans, trans_df, maxDH, tID_fld='sort_ID', MHW='', fill=-99999, skip_missing_z=True):
    # To find dlow proxy, use code written by Ben in Matlab and converted to pandas by Emily
    # Uses snapToLine() polyline geometry method from arcpy

    # Replace nan's with fill for cursor operations;
    if trans_df.isnull().values.any():
        nan_input = True
        trans_df.fillna(fill, inplace=True)
    else:
        nan_input = False

    # Add (or recalculate) elevation fields adjusted to MHW
    trans_df = fun.adjust2mhw(trans_df, MHW, ['DH_z', 'DL_z', 'Arm_z'], fill)

    # Initialize beach width dataframe
    bw_df = pd.DataFrame(fill, index=trans_df.index, columns= ['DistDL', 'DistDH', 'DistArm', 'uBW', 'uBH', 'ub_feat'], dtype='f8')
    # field ub_feat gets converted to object type when the value is set

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
                if int(tran.DH_x) != int(fill):
                    ptDH = transect.snapToLine(arcpy.Point(tran['DH_x'], tran['DH_y']))
                    bw_df.loc[tID, 'DistDH'] = np.hypot(tran['SL_x'] - ptDH[0].X, tran['SL_y'] - ptDH[0].Y)
                if int(tran.Arm_x) != int(fill):
                    ptArm = transect.snapToLine(arcpy.Point(tran['Arm_x'], tran['Arm_y']))
                    bw_df.loc[tID, 'DistArm'] = np.hypot(tran['SL_x'] - ptArm[0].X, tran['SL_y'] - ptArm[0].Y)

                # Select Dist value for uBW. Use DistDL if available. If not and DH < maxDH, use DistDH. If neither available, use DistArm.
                if skip_missing_z: # if Z value is fill, don't use the point even if XY is populated
                    if int(tran.DL_z) != int(fill) and int(tran.DL_x) != int(fill):
                        bw_df.loc[tID, 'uBW'] = bw_df['DistDL'].loc[tID]
                        bw_df.loc[tID, 'uBH'] = tran['DL_zmhw']
                        bw_df.loc[tID, 'ub_feat'] = 'DL'
                    elif int(tran.DH_x) != int(fill) and int(tran.DH_z) != int(fill) and tran.DH_zmhw <= maxDH:
                        bw_df.loc[tID, 'uBW'] = bw_df['DistDH'].loc[tID]
                        bw_df.loc[tID, 'uBH'] = tran['DH_zmhw']
                        bw_df.loc[tID, 'ub_feat'] = 'DH'
                    elif int(tran.Arm_x) != int(fill) and int(tran.Arm_z) != int(fill):
                        bw_df.loc[tID, 'uBW'] = bw_df['DistArm'].loc[tID]
                        bw_df.loc[tID, 'uBH'] = tran['Arm_zmhw']
                        bw_df.loc[tID, 'ub_feat'] = 'Arm'
                    else:
                        continue
                # Use any point with XY matching the criteria
                else:
                    if int(tran.DL_x) != int(fill):
                        bw_df.loc[tID, 'uBW'] = bw_df['DistDL'].loc[tID]
                        bw_df.loc[tID, 'uBH'] = tran['DL_zmhw']
                        bw_df.loc[tID, 'ub_feat'] = 'DL'
                    elif int(tran.DH_x) != int(fill) and tran.DH_zmhw <= maxDH and int(tran.DH_z) != int(fill):
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
    return(trans_df)

"""
Widths
"""
def calc_IslandWidths(in_trans, barrierBoundary, out_clipped='clip2island', tID_fld='sort_ID'):
    home = arcpy.env.workspace
    out_clipped = os.path.join(arcpy.env.scratchGDB, out_clipped)
    if not arcpy.Exists(out_clipped):
        print("Clipping the transects to the barrier island boundaries ('{}')...".format(os.path.basename(out_clipped)))
        arcpy.Clip_analysis(os.path.join(home, in_trans), os.path.join(home, barrierBoundary), out_clipped) # ~30 seconds
    else:
        print("Found {} in scratch database. This could have been generated by an earlier version so beware.".format(os.path.basename(out_clipped)))
    # WidthPart - spot-checking verifies the results, but it should additionally include a check to ensure that the first transect part encountered intersects the shoreline
    print('Getting the width along each transect of the oceanside land (WidthPart)...')
    out_clipsingle = out_clipped + '_singlepart'
    if not arcpy.Exists(out_clipsingle):
        arcpy.MultipartToSinglepart_management(out_clipped, out_clipsingle)
    clipsingles = FCtoDF(out_clipsingle, dffields = ['SHAPE@LENGTH', tID_fld], length=True)
    widthpart = clipsingles.groupby(tID_fld)['SHAPE@LENGTH'].first()
    widthpart.name = 'WidthPart'
    # WidthFull
    print('Getting the width along each transect of the entire barrier (WidthFull)...')
    verts = FCtoDF(out_clipped, id_fld=tID_fld, explode_to_points=True)
    verts.drop(tID_fld, axis=1, inplace=True)
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

    out_clipped = os.path.join(arcpy.env.scratchGDB, 'tidytrans_clipped')
    print("Clipping transects to within the shoreline bounds ('{}')...".format(os.path.basename(out_clipped)))
    arcpy.Clip_analysis(in_trans, barrierBoundary, os.path.join(arcpy.env.scratchGDB, out_clipped))

    print('Getting points every 5m along each transect and saving in new dataframe...')
    # Initialize empty dataframe
    df = pd.DataFrame(columns=[tID_fld, 'seg_x', 'seg_y'])
    # Get shape object and tID value for each transect
    for line, ID in arcpy.da.SearchCursor(out_clipped, ("SHAPE@", tID_fld)):
        # Get points in 5m increments along transect and save to df
        for i in range(0, int(line.length), step):
            pt = line.positionAlongLine(i)[0]
            df = df.append({tID_fld:ID, 'seg_x':pt.X, 'seg_y':pt.Y}, ignore_index=True)

    if len(fc_out) > 1:
        print("Converting dataframe to feature class ('{}')...".format(os.path.basename(fc_out)))
        fc_out = DFtoFC(df, fc_out, id_fld=tID_fld, spatial_ref = arcpy.Describe(in_trans).spatialReference)

    duration = fun.print_duration(start)
    return(df, fc_out)

def FCtoDF(fc, xy=False, dffields=[], fill=-99999, id_fld=False, extra_fields=[], verbose=True, fid=False, explode_to_points=False, length=False):
    # Convert FeatureClass to pandas.DataFrame with np.nan values
    # 1. Convert FC to Numpy array
    if explode_to_points:
        message = 'Converting feature class vertices to array with X and Y...'
        if not id_fld:
            print('Error: if explode_to_points is set to True, id_fld must be specified.')
        fcfields = [id_fld, 'SHAPE@X', 'SHAPE@Y', 'OID@']
    else:
        fcfields = [f.name for f in arcpy.ListFields(fc)]
        if xy:
            message = 'Converting feature class to array with X and Y...'
            fcfields += ['SHAPE@X','SHAPE@Y']
        else:
            message = '...converting feature class to array...'
        if fid:
            fcfields += ['OID@']
        if length:
            fcfields += ['SHAPE@LENGTH']
    if verbose:
        print(message)
    arr = arcpy.da.FeatureClassToNumPyArray(os.path.join(arcpy.env.workspace, fc), fcfields, null_value=fill, explode_to_points=explode_to_points)
    # 2. Convert array to dict
    if verbose:
        print('...converting array to dataframe...')
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
    if verbose:
        print("Created {} from input dataframe and {} file.".format(os.path.basename(out_fc), os.path.basename(in_fc)))
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
        print("OUTPUT: {}".format(os.path.basename(out_fc)))
    fun.print_duration(start)
    return(out_fc)

def DFtoTable(df, tbl, fill=-99999):
    # Convert data frame to Arc Table by converting to np.array with fill values and then to Table
    try:
        arr = df.select_dtypes(exclude=['object']).fillna(fill).to_records()
    except ValueError:
        df.index.name = 'index'
        arr = df.select_dtypes(exclude=['object']).fillna(fill).to_records()
    if not os.path.split(tbl)[0]: # if no path is provided, default to scratch gdb
        tbl = os.path.join(arcpy.env.scratchGDB, tbl)
    arcpy.Delete_management(tbl)
    arcpy.da.NumPyArrayToTable(arr, tbl)
    return(tbl)

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
    print('OUTPUT: {}. Field "Value" is ID and "uBW" is beachwidth.'.format(os.path.basename(out_rst)))
    return(out_rst)
