
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



def SortTransectPrep(newfields = ['sort', 'sort_corn'], spatialref=utmSR):
    multi_sort = input("Do we need to sort the transects in batches to preserve the order? (y/n) ")
    sort_lines = 'sort_lines'
    if multi_sort == 'y':
        if not arcpy.Exists(sort_lines):
            sort_lines = arcpy.CreateFeatureclass_management(arcpy.env.scratchGDB, sort_lines, "POLYLINE", spatial_reference=utmSR)
            arcpy.AddField_management(sort_lines, newfields[0], 'SHORT', field_precision=2)
            arcpy.AddField_management(sort_lines, newfields[1], 'TEXT', field_length=2)
            print("MANUALLY: Add features to sort_lines. Indicate the order of use in 'sort' and the sort corner in 'sort_corn'.")
    else:
        sort_lines = []
        # Corner from which to start sorting, LL = lower left, etc.
        sort_corner = input("Sort corner (LL, LR, UL, UR): ")
    return(sort_lines)
