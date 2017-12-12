
in_fc = '\\\\Mac\\stor\\Projects\\TransectExtraction\\Fisherman2014\\Fisherman2014.gdb\\extTrans'
sort_lines = os.path.join(arcpy.env.scratchGDB, 'sort_lines')
out_trans =  os.path.join(arcpy.env.workspace, 'extTrans_sorttest')
# Loop through sort_lines ordered by field 'sort'
# For each line, copy the transect FC and remove all transects that do not intersect the given sort line.
# Sort the subsetted transects.
# Append each one to the

arcpy.SelectLayerByLocation_management(LTextended, "INTERSECT", barrierBoundary)

arcpy.SpatialJoin_analysis(LTextended, barrierBoundary, LTextended+'_join', "#","KEEP_COMMON", match_option="INTERSECT")

for srow in arcpy.da.SearchCursor(sort_lines2, ['SHAPE@', 'sort', 'sort_corn']):
    temp1 = arcpy.FeatureClassToFeatureClass_conversion(in_fc, arcpy.env.scratchGDB, 'trans_subset')
    with arcpy.da.UpdateCursor(temp1, ['SHAPE@']) as cursor:
        for trow in cursor:
            tran = trow[0]
            if tran.disjoint(sline):
                cursor.deleteRow()

arcpy.CreateFeatureclass_management(arcpy.env.workspace, os.path.basename(out_trans), "POLYLINE", in_fc, spatial_reference=in_fc)
dsc = arcpy.Describe(in_fc)
fieldnames = [field.name for field in dsc.fields if not field.name == dsc.OIDFieldName] + ['SHAPE@']
sort_lines2 = arcpy.Sort_management(sort_lines, sort_lines+'2', [['sort', 'ASCENDING']]) # Sort from lower lef
for srow in arcpy.da.SearchCursor(sort_lines2, ['SHAPE@', 'sort', 'sort_corn']): # this sort may not work...
    sline = srow[0]
    scnt = srow[1]
    scorner = srow[2]
    temp1 = arcpy.FeatureClassToFeatureClass_conversion(in_fc, arcpy.env.scratchGDB, 'trans_subset')
    with arcpy.da.UpdateCursor(temp1, ['SHAPE@']) as cursor:
        for trow in cursor:
            tran = trow[0]
            if tran.disjoint(sline):
                cursor.deleteRow()
    temp2 = arcpy.Sort_management(temp1, 'trans_sub_sort{}'.format(scorner), [['Shape', 'ASCENDING']], scorner) # Sort from lower lef
    with arcpy.da.InsertCursor(out_trans, fieldnames) as icur:
        for row in arcpy.da.SearchCursor(temp2, fieldnames):
            icur.insertRow(row)


#%% Troubleshooting source of 0 values instead of Nulls:
in_fc = '\\\\Mac\\stor\\Projects\\TransectExtraction\\Fisherman2014\\Fisherman2014.gdb\\extTrans'
sort_lines = os.path.join(arcpy.env.scratchGDB, 'sort_lines')
out_trans =  os.path.join(arcpy.env.workspace, 'extTrans_sorttest')
# Loop through sort_lines ordered by field 'sort'
# For each line, copy the transect FC and remove all transects that do not intersect the given sort line.
# Sort the subsetted transects.
# Append each one to the
arcpy.CreateFeatureclass_management(arcpy.env.workspace, os.path.basename(out_trans), "POLYLINE", in_fc, spatial_reference=in_fc)
dsc = arcpy.Describe(in_fc)
fieldnames = [field.name for field in dsc.fields if not field.name == dsc.OIDFieldName] + ['SHAPE@']

# preserves null values...
with arcpy.da.InsertCursor(out_trans, fieldnames) as icur:
    for row in arcpy.da.SearchCursor(in_fc, fieldnames):
        icur.insertRow(row)

# also preserves null values...
temp1 = arcpy.FeatureClassToFeatureClass_conversion(in_fc, arcpy.env.scratchGDB, 'trans_subset')

# There's no reason for this to change the Nulls... and it doesn't.
scur = arcpy.da.SearchCursor(sort_lines2, ['SHAPE@', 'sort', 'sort_corn'])
sline = next(scur)[0]
with arcpy.da.UpdateCursor(temp1, ['SHAPE@']) as cursor:
    for trow in cursor:
        tran = trow[0]
        if tran.disjoint(sline):
            cursor.deleteRow()
# This didn't either:
temp2 = arcpy.Sort_management(temp1, 'trans_sub_sort{}'.format(scorner), [['Shape', 'ASCENDING']], scorner) # Sort from lower lef

def SelectivelyDeleteFeatures(targetFC, selectionFC):
    for row in arcpy.da.SearchCursor(selectionFC, ['SHAPE@']):
        geom = row[0]
        with arcpy.da.UpdateCursor(targetFC, ['SHAPE@']) as cursor:
            for trow in cursor:
                tgeom = trow[0]
                if tgeom.disjoint(geom):
                    cursor.deleteRow()
    return(targetFC)



def SortTransectsFromSortLines(in_trans, out_trans, sort_lines=[], tID_fld='sort_ID', sort_corner='LL', verbose=True):
    # Add the transect ID field to the transects if it doesn't already exist.
    temppath = os.path.join(arcpy.env.scratchGDB, 'trans_')
    try:
        arcpy.AddField_management(in_trans, tID_fld, 'SHORT')
    except:
        pass
    # If sort_lines is blank ([]), go ahead and sort the transects based on sort_corner argument.
    if not len(sort_lines):
        out_trans = arcpy.Sort_management(in_trans, out_trans, [['Shape', 'ASCENDING']], sort_corner) # Sort from lower lef
    else:
        if verbose:
            print("Creating new feature class {} to hold sorted transects...".format(out_trans))
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
                # temp2 = arcpy.Sort_management(temp2, 'trans_sub_sort{}rev'.format(scorner), [['OID', 'DESCENDING']])
                rowcount = int(arcpy.GetCount_management(temp2)[0])
                with arcpy.da.UpdateCursor(temp2, ['OID@']) as cursor:
                    for row in cursor:
                        cursor.updateRow([rowcount-row[0]+1])
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


sort_lines2

for sline, scorner in arcpy.da.SearchCursor(sort_lines2, ['SHAPE@', 'sort_corn']):

temp1 = arcpy.FeatureClassToFeatureClass_conversion(in_trans, arcpy.env.scratchGDB, 'trans_subset')
with arcpy.da.UpdateCursor(temp1, ['SHAPE@']) as cursor:
    for trow in cursor:
        tran = trow[0]
        if tran.disjoint(sline):
            cursor.deleteRow()
temp2 = arcpy.Sort_management(temp1, temppath+'sub_sort{}'.format(scorner), [['Shape', 'ASCENDING']], scorner)
if reverse_order == 'T':

rowcount = int(arcpy.GetCount_management(temp2)[0])
with arcpy.da.UpdateCursor(temp2, ['OID@', 'sort_ID']) as cursor:
    for row in cursor:
        cursor.updateRow([row[0], rowcount-row[0]+1])

with arcpy.da.UpdateCursor(temp2, ['OID@', tID_fld]) as cursor:
    for row in cursor:
        cursor.updateRow([row[0], row[0]])
temp2 = arcpy.Sort_management(temp2, temppath+'subrev_sort{}'.format(scorner), [[tID_fld, 'DESCENDING']])
