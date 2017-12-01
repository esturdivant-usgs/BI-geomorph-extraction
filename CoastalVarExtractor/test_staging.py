
in_fc = '\\\\Mac\\stor\\Projects\\TransectExtraction\\Fisherman2014\\Fisherman2014.gdb\\extTrans'
sort_lines = os.path.join(arcpy.env.scratchGDB, 'sort_lines')
out_trans =  os.path.join(arcpy.env.scratchGDB, 'extTrans_sorttest')
# Loop through sort_lines ordered by field 'sort'
# For each line, copy the transect FC and remove all transects that do not intersect the given sort line.
# Sort the subsetted transects.
# Append each one to the
arcpy.CreateFeatureclass_management(arcpy.env.workspace, os.path.basename(out_trans), "POLYLINE", in_fc, spatial_reference=in_fc)
dsc = arcpy.Describe(in_fc)
fieldnames = [field.name for field in dsc.fields if not field.name == dsc.OIDFieldName] + ['SHAPE@']
sort_lines2 = arcpy.Sort_management(sort_lines, 'sort_lines2', [['sort', 'ASCENDING']]) # Sort from lower lef
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
# Copy the OID values to the tID_fld
with arcpy.da.UpdateCursor(out_trans, ['OID@', tID_fld]) as cursor:
    for row in cursor:
        cursor.updateRow([row[0], row[0]])



new_ct = 0 # Initialize new_ct
# Loop through sort_lines ordered by field 'sort'
# For each line, copy the transect FC and remove all transects that do not intersect the given sort line.
# Create empty feature class to add the new Transects
arcpy.CreateFeatureClass_management(arcpy.env.workspace, out_trans, "POLYLINE", in_fc, spatial_reference=in_fc)
for srow in arcpy.da.SearchCursor(sort_lines, ['SHAPE@', 'sort', 'sort_corn'], sort_fields='sort A'):
    sline = srow[0]
    scnt = srow[1]
    scorner = srow[2]
    temp_fc = 'trans_sort{}_temp'.format(scnt)
    arcpy.FeatureClassToFeatureClass_conversion(in_fc, arcpy.env.scratchGDB, temp_fc)
    with arcpy.da.UpdateCursor(temp_fc, ['SHAPE@']) as cursor:
        for trow in cursor:
            if trow.disjoint(sline):
                cursor.deleteRow()
    out_fc = 'trans_sort{}_temp'.format(new_ct)
    arcpy.Sort_management(temp_fc, out_fc, [['Shape', 'ASCENDING']], scorner) # Sort from lower left
    ct = 0
    with arcpy.da.UpdateCursor(out_fc, ['OID@', sortfield]) as cursor:
        for row in cursor:
            ct+=1
            cursor.updateRow([row[0], row[0]+new_ct])





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
